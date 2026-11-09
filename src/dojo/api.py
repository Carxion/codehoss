"""HTTP + WebSocket API, plus the built frontend.

All routes live under /api and need a logged-in user (cookie), except auth and
health. Solutions, hidden tests, try-it checks and quiz answers never leave the
server; hints are handed out one level at a time and recorded as progress.
"""

# No `from __future__ import annotations` here: FastAPI must resolve the locally
# defined `UserDep` annotation at runtime.
import asyncio
import contextlib
import json
import os
import threading
from collections.abc import AsyncIterator
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from dojo import grader
from dojo.executors import StdinFeed
from dojo.explain import explain_message, explain_traceback
from dojo.lsp import LanguageServer
from dojo.models import ExampleStep, ExerciseStep, ExplainStep, QuizStep, Step, TryItStep
from dojo.registry import Content, LoadedExercise, LoadedLesson, LoadedModule, load_content
from dojo.sandbox import LIBRARY_DIR, SandboxError, Session, SessionManager
from dojo.store import AuthError, Store, User

MAX_CODE = 100_000
REAP_INTERVAL_S = 30
COOKIE = "dojo_token"
# Interactive runs wait for typing, so wall-clock time is generous; CPU time is what
# stops runaway loops.
INTERACTIVE_TIMEOUT_S = 300
INTERACTIVE_CPU_S = 10


# --- request bodies ------------------------------------------------------------


class Credentials(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


class CreateSession(BaseModel):
    module_id: str


class RunRequest(BaseModel):
    code: str = Field(max_length=MAX_CODE)
    inputs: list[str] = Field(default=[], max_length=200)


class CheckRequest(BaseModel):
    exercise_id: str
    code: str = Field(max_length=MAX_CODE)


class TryItRequest(BaseModel):
    lesson: str
    step: int
    code: str = Field(max_length=MAX_CODE)


class QuizAnswer(BaseModel):
    answer: int


# --- app -----------------------------------------------------------------------


def create_app(
    content: Content | None = None,
    *,
    manager: SessionManager | None = None,
    store: Store | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    if content is None:
        content = load_content(Path(os.environ.get("DOJO_CONTENT", "content")).resolve())
    sessions = manager or SessionManager(content)
    db = store or Store(os.environ.get("DOJO_DB", "var/dojo.db"))

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(SessionManager.remove_orphans)
        reaper = asyncio.create_task(_reap_forever(sessions))
        try:
            yield
        finally:
            reaper.cancel()
            await run_in_threadpool(sessions.close_all)

    app = FastAPI(title="DataDojo", version="0.2.0", lifespan=lifespan)
    api = APIRouter(prefix="/api")

    # -- helpers --

    def current_user(request: Request) -> User:
        user = db.user_for_token(request.cookies.get(COOKIE, ""))
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "please log in")
        return user

    UserDep = Annotated[User, Depends(current_user)]

    def module_or_404(module_id: str) -> LoadedModule:
        module = content.modules.get(module_id)
        if module is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "module not found")
        return module

    def lesson_or_404(module: LoadedModule, slug: str) -> LoadedLesson:
        lesson = next((les for les in module.lessons if les.slug == slug), None)
        if lesson is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "lesson not found")
        return lesson

    def step_or_404(lesson: LoadedLesson, index: int) -> Step:
        if not 0 <= index < len(lesson.spec.steps):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "step not found")
        return lesson.spec.steps[index]

    def exercise_or_404(exercise_id: str) -> LoadedExercise:
        exercise = content.exercise(exercise_id)
        if exercise is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "exercise not found")
        return exercise

    def own_session(session_id: str, user: User) -> Session:
        try:
            session = sessions.get(session_id)
        except KeyError:
            session = None
        if session is None or session.owner != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
        return session

    # -- auth --

    def _login_response(response: Response, user: User) -> dict:
        response.set_cookie(
            COOKIE, db.create_token(user), httponly=True, samesite="lax", max_age=30 * 86400
        )
        return {"username": user.username}

    @api.post("/auth/register", status_code=status.HTTP_201_CREATED)
    def register(body: Credentials, response: Response) -> dict:
        try:
            user = db.register(body.username, body.password)
        except AuthError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
        return _login_response(response, user)

    @api.post("/auth/login")
    def login(body: Credentials, response: Response) -> dict:
        try:
            user = db.authenticate(body.username, body.password)
        except AuthError as e:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from None
        return _login_response(response, user)

    @api.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(request: Request, response: Response) -> None:
        db.revoke_token(request.cookies.get(COOKIE, ""))
        response.delete_cookie(COOKIE)

    @api.get("/me")
    def me(user: UserDep) -> dict:
        return {"username": user.username}

    @api.get("/health")
    def health() -> dict:
        return {"status": "ok", "modules": len(content.modules)}

    # -- content --

    @api.get("/modules")
    def list_modules(user: UserDep) -> list[dict]:
        result = []
        for m in content.modules.values():
            progress = db.progress(user, m.spec.id)
            result.append(
                {
                    "id": m.spec.id,
                    "title": m.spec.title,
                    "description": m.spec.description,
                    "level": m.spec.level,
                    "prerequisites": m.spec.prerequisites,
                    "lessons": [
                        {
                            "slug": lesson.slug,
                            "title": lesson.spec.title,
                            "summary": lesson.spec.summary,
                            "steps": len(lesson.spec.steps),
                            "done": sum(
                                1
                                for i in range(len(lesson.spec.steps))
                                if (p := progress.get(f"{lesson.slug}/{i}")) and p.done
                            ),
                        }
                        for lesson in m.lessons
                    ],
                }
            )
        return result

    @api.get("/modules/{module_id}/lessons/{slug}")
    def get_lesson(module_id: str, slug: str, user: UserDep) -> dict:
        module = module_or_404(module_id)
        lesson = lesson_or_404(module, slug)
        slugs = [les.slug for les in module.lessons]
        position = slugs.index(slug)
        progress = db.progress(user, module_id)
        return {
            "module_id": module_id,
            "slug": slug,
            "title": lesson.spec.title,
            "summary": lesson.spec.summary,
            "previous": slugs[position - 1] if position > 0 else None,
            "next": slugs[position + 1] if position + 1 < len(slugs) else None,
            "steps": [_public_step(lesson, i, step) for i, step in enumerate(lesson.spec.steps)],
            "progress": {
                ref.split("/", 1)[1]: asdict(p)
                for ref, p in progress.items()
                if ref.startswith(f"{slug}/")
            },
        }

    @api.get("/modules/{module_id}/library")
    def get_library(module_id: str, user: UserDep) -> Response:
        module_or_404(module_id)
        path = LIBRARY_DIR / f"{module_id}.json"
        if not path.exists():
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "library index not built; run `dojo build-images`"
            )
        return Response(path.read_bytes(), media_type="application/json")

    @api.get("/exercises/{exercise_id}")
    def get_exercise(exercise_id: str, user: UserDep) -> dict:
        return _public_exercise(exercise_or_404(exercise_id))

    @api.get("/modules/{module_id}/lessons/{slug}/steps/{index}/hints/{level}")
    def get_hint(module_id: str, slug: str, index: int, level: int, user: UserDep) -> dict:
        """Levels 1..n are hints; level n+1 is "show me" (the solution)."""
        module = module_or_404(module_id)
        lesson = lesson_or_404(module, slug)
        step = step_or_404(lesson, index)
        if isinstance(step, TryItStep):
            hints, solution = step.hints, step.solution
        elif isinstance(step, ExerciseStep):
            exercise = lesson.exercises[step.ref]
            hints = exercise.spec.hints
            solution = exercise.solution_path.read_text(encoding="utf-8")
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "this step has no hints")
        if not 1 <= level <= len(hints) + 1:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"levels go from 1 to {len(hints) + 1}")
        ref = f"{slug}/{index}"
        if level <= len(hints):
            db.record(user, module_id, ref, hints_used=level)
            return {"level": level, "of": len(hints), "hint": hints[level - 1]}
        db.record(user, module_id, ref, hints_used=len(hints), showed_solution=True)
        return {"level": level, "of": len(hints), "solution": solution}

    @api.post("/modules/{module_id}/lessons/{slug}/steps/{index}/answer")
    def answer_quiz(module_id: str, slug: str, index: int, body: QuizAnswer, user: UserDep) -> dict:
        step = step_or_404(lesson_or_404(module_or_404(module_id), slug), index)
        if not isinstance(step, QuizStep):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "this step is not a quiz")
        correct = body.answer == step.answer
        db.record(user, module_id, f"{slug}/{index}", attempt=True, done=correct)
        # The right answer is only revealed by getting it right.
        return {"correct": correct, "explanation": step.explanation if correct else ""}

    @api.post(
        "/modules/{module_id}/lessons/{slug}/steps/{index}/viewed",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def mark_viewed(module_id: str, slug: str, index: int, user: UserDep) -> None:
        step = step_or_404(lesson_or_404(module_or_404(module_id), slug), index)
        if not isinstance(step, ExplainStep | ExampleStep):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "this step is completed by doing it")
        db.record(user, module_id, f"{slug}/{index}", done=True)

    # -- sessions --

    @api.post("/sessions", status_code=status.HTTP_201_CREATED)
    def create_session(body: CreateSession, user: UserDep) -> dict:
        module_or_404(body.module_id)
        session = sessions.find(user.id, body.module_id)
        if session is None:
            try:
                session = sessions.create(body.module_id, owner=user.id)
            except SandboxError as e:
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from None
        return {"session_id": session.id, "module_id": session.module_id}

    @api.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_session(session_id: str, user: UserDep) -> None:
        own_session(session_id, user)
        sessions.close(session_id)

    @api.post("/sessions/{session_id}/run")
    def run(session_id: str, body: RunRequest, user: UserDep) -> dict:
        session = own_session(session_id, user)
        result = grader.run_program(body.code, body.inputs, executor=session.executor)
        explanation = explain_traceback(result.stderr, body.code)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "timed_out": result.timed_out,
            "explanation": asdict(explanation) if explanation else None,
        }

    @api.post("/sessions/{session_id}/check")
    def check(session_id: str, body: CheckRequest, user: UserDep) -> dict:
        session = own_session(session_id, user)
        exercise = exercise_or_404(body.exercise_id)
        if exercise.module_id != session.module_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "exercise is from another module")
        result = grader.grade(exercise, body.code, executor=session.executor)
        if (ref := _exercise_step_ref(content, exercise)) is not None:
            db.record(user, exercise.module_id, ref, attempt=True, done=result.passed)
        return {
            "passed": result.passed,
            "timed_out": result.timed_out,
            "results": [
                {
                    "name": r.name,
                    "label": r.label,
                    "outcome": r.outcome,
                    "message": r.message,
                    "explanation": explain_message(r.message, body.code),
                }
                for r in result.results
            ],
        }

    @api.post("/sessions/{session_id}/try-it")
    def try_it(session_id: str, body: TryItRequest, user: UserDep) -> dict:
        session = own_session(session_id, user)
        lesson = lesson_or_404(content.modules[session.module_id], body.lesson)
        step = step_or_404(lesson, body.step)
        if not isinstance(step, TryItStep):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "that step is not a try-it")
        result = grader.run_snippet(body.code, step.check, executor=session.executor)
        db.record(
            user, session.module_id, f"{body.lesson}/{body.step}", attempt=True, done=result.passed
        )
        return {"passed": result.passed, "message": explain_message(result.message, body.code)}

    async def _ws_session(websocket: WebSocket, session_id: str) -> Session | None:
        await websocket.accept()
        user = db.user_for_token(websocket.cookies.get(COOKIE, ""))
        try:
            session = sessions.get(session_id) if user else None
        except KeyError:
            session = None
        if user is None or session is None or session.owner != user.id:
            await websocket.close(code=4404, reason="session not found")
            return None
        return session

    @api.websocket("/sessions/{session_id}/stream")
    async def stream(websocket: WebSocket, session_id: str) -> None:
        """Interactive run.

        Client: {"type": "run", "code": ...}, then any number of
        {"type": "stdin", "data": "..."} and optionally {"type": "stop"}.
        Server: {"type": "output", "data": ...} messages, then one {"type": "exit", ...}.
        """
        session = await _ws_session(websocket, session_id)
        if session is None:
            return
        try:
            first = await websocket.receive_json()
            body = RunRequest.model_validate(first)
        except (ValidationError, ValueError, WebSocketDisconnect) as e:
            with contextlib.suppress(RuntimeError):
                await websocket.close(code=4400, reason=str(e)[:120])
            return

        loop = asyncio.get_running_loop()
        outputs: asyncio.Queue[str] = asyncio.Queue()
        feed = StdinFeed()
        for line in body.inputs:
            feed.write(f"{line}\n")
        cancel = threading.Event()

        job = loop.run_in_executor(
            None,
            lambda: grader.run_program(
                body.code,
                feed,
                executor=session.executor,
                timeout=INTERACTIVE_TIMEOUT_S,
                cpu_seconds=INTERACTIVE_CPU_S,
                cancel=cancel,
                on_output=lambda text: loop.call_soon_threadsafe(outputs.put_nowait, text),
            ),
        )

        async def read_client() -> None:
            try:
                while True:
                    message = await websocket.receive_json()
                    if message.get("type") == "stdin":
                        feed.write(str(message.get("data", ""))[:10_000])
                    elif message.get("type") == "stop":
                        cancel.set()
            except (WebSocketDisconnect, ValueError, RuntimeError):
                cancel.set()

        reader = asyncio.create_task(read_client())
        output: list[str] = []
        try:
            while not (job.done() and outputs.empty()):
                try:
                    text = await asyncio.wait_for(outputs.get(), timeout=0.1)
                except TimeoutError:
                    continue
                output.append(text)
                await websocket.send_json({"type": "output", "data": text})
            result = await job
            explanation = explain_traceback("".join(output), body.code)
            await websocket.send_json(
                {
                    "type": "exit",
                    "exit_code": result.returncode,
                    "timed_out": result.timed_out,
                    "cancelled": result.cancelled,
                    "explanation": asdict(explanation) if explanation else None,
                }
            )
            await websocket.close()
        except (WebSocketDisconnect, RuntimeError):
            cancel.set()
        finally:
            reader.cancel()

    @api.websocket("/sessions/{session_id}/lsp")
    async def lsp(websocket: WebSocket, session_id: str) -> None:
        """Language Server Protocol bridge: one JSON-RPC message per WebSocket text frame."""
        session = await _ws_session(websocket, session_id)
        if session is None:
            return
        loop = asyncio.get_running_loop()
        replies: asyncio.Queue[dict] = asyncio.Queue()
        image = content.modules[session.module_id].spec.sandbox.image
        server = await run_in_threadpool(
            LanguageServer, image, lambda msg: loop.call_soon_threadsafe(replies.put_nowait, msg)
        )

        async def forward_replies() -> None:
            while True:
                await websocket.send_text(json.dumps(await replies.get()))

        sender = asyncio.create_task(forward_replies())
        try:
            while True:
                message = json.loads(await websocket.receive_text())
                await run_in_threadpool(server.send, message)
        except (WebSocketDisconnect, ValueError, RuntimeError):
            pass
        finally:
            sender.cancel()
            await run_in_threadpool(server.close)

    app.include_router(api)
    if static_dir and static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="web")
    return app


def _public_exercise(ex: LoadedExercise) -> dict:
    # Never send solution.py, hidden tests, or hint text (hints are fetched one by one).
    return {
        "id": ex.spec.id,
        "module_id": ex.module_id,
        "title": ex.spec.title,
        "prompt": ex.spec.prompt,
        "difficulty": ex.spec.difficulty,
        "hint_count": len(ex.spec.hints),
        "starter": ex.starter_path.read_text(encoding="utf-8"),
        "visible_tests": ex.visible_tests.read_text(encoding="utf-8"),
    }


def _public_step(lesson: LoadedLesson, index: int, step: Step) -> dict:
    base: dict = {"index": index, "type": step.type}
    match step:
        case ExplainStep():
            return {**base, "md": step.md}
        case ExampleStep():
            return {**base, "md": step.md, "code": step.code, "runnable": step.runnable}
        case TryItStep():
            return {
                **base,
                "prompt": step.prompt,
                "starter": step.starter,
                "hint_count": len(step.hints),
            }
        case ExerciseStep():
            return {**base, "exercise": _public_exercise(lesson.exercises[step.ref])}
        case QuizStep():
            return {**base, "question": step.question, "options": step.options}
    raise AssertionError(f"unhandled step type {step.type}")


def _exercise_step_ref(content: Content, exercise: LoadedExercise) -> str | None:
    module = content.modules[exercise.module_id]
    for lesson in module.lessons:
        if lesson.slug != exercise.lesson_slug:
            continue
        for i, step in enumerate(lesson.spec.steps):
            if isinstance(step, ExerciseStep) and step.ref == exercise.slug:
                return f"{lesson.slug}/{i}"
    return None


async def _reap_forever(sessions: SessionManager) -> None:
    while True:
        await asyncio.sleep(REAP_INTERVAL_S)
        await run_in_threadpool(sessions.reap_idle)
