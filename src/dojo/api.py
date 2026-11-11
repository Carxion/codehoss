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
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Literal

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
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from dojo import grader, lab, skills, tutor
from dojo.ai import ANTHROPIC_MODELS, AIError, AISettings, Gateway
from dojo.executors import StdinFeed
from dojo.explain import explain_message, explain_traceback
from dojo.lsp import LanguageServer
from dojo.models import (
    LEVELS,
    ExampleStep,
    ExerciseStep,
    ExplainStep,
    QuizStep,
    ShowcaseStep,
    Step,
    TryItStep,
)
from dojo.notebook import Kernel
from dojo.portfolio import export_zip
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


class LabFile(BaseModel):
    path: str = Field(min_length=1, max_length=200)
    content: str = Field(max_length=lab.MAX_FILE_BYTES)


class LabReset(BaseModel):
    engine: bool = False  # also remove the learner's containers, networks and volumes


class TryItRequest(BaseModel):
    lesson: str
    step: int
    code: str = Field(max_length=MAX_CODE)


class AISettingsBody(BaseModel):
    provider: Literal["ollama", "anthropic"] | None
    model: str | None = Field(default=None, max_length=100)
    api_key: str | None = Field(default=None, max_length=300)
    clear_key: bool = False


class TutorMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=20_000)


class TutorRequest(BaseModel):
    module_id: str
    lesson: str
    step: int
    code: str = Field(default="", max_length=MAX_CODE)
    # Labs: the tutor reads the learner's files from this session.
    session_id: str | None = None
    # The last Check, as shown to the learner (results, or a try-it message).
    feedback: dict | None = None
    messages: list[TutorMessage] = Field(min_length=1, max_length=60)


class LevelBody(BaseModel):
    level: Literal["guided", "assisted", "solo"]


class QuizAnswer(BaseModel):
    answer: int


# --- app -----------------------------------------------------------------------


def create_app(
    content: Content | None = None,
    *,
    manager: SessionManager | None = None,
    gateway: Gateway | None = None,
    store: Store | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    if content is None:
        content = load_content(Path(os.environ.get("DOJO_CONTENT", "content")).resolve())
    sessions = manager or SessionManager(content)
    db = store or Store(os.environ.get("DOJO_DB", "var/dojo.db"))
    ai = gateway or Gateway()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(SessionManager.remove_orphans)
        reaper = asyncio.create_task(_reap_forever(sessions))
        try:
            yield
        finally:
            reaper.cancel()
            await run_in_threadpool(sessions.close_all)

    app = FastAPI(title="DataDojo", version="0.3.0", lifespan=lifespan)
    # The JS bundle and library indexes are large and compress well.
    app.add_middleware(GZipMiddleware, minimum_size=1024)
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

    def language_of(session: Session) -> str:
        return content.modules[session.module_id].spec.language

    def review_answer(user: User, module_id: str, ref: str, passed: bool) -> None:
        """Schedule the step's review card after an answer (see dojo.skills)."""
        lesson = lesson_or_404(content.modules[module_id], ref.rpartition("/")[0])
        kind = skills.review_kind(lesson, lesson.spec.steps[int(ref.rpartition("/")[2])])
        if kind is None:
            return
        card = skills.schedule(
            db.review_card(user, module_id, ref), module_id, ref, kind, passed, time.time()
        )
        if card is not None:
            db.save_review_card(user, card)

    def review_helped(user: User, module_id: str, ref: str) -> None:
        card = skills.mark_helped(db.review_card(user, module_id, ref), time.time())
        if card is not None:
            db.save_review_card(user, card)

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

    def ai_settings_for(user: User) -> AISettings:
        row = db.ai_settings(user)
        return AISettings(provider=row.provider, model=row.model, api_key=row.api_key)

    @api.get("/ai/status")
    def ai_status(user: UserDep) -> dict:
        """Everything the AI settings panel shows. Never includes the key itself."""
        settings = ai_settings_for(user)
        ollama = ai.ollama_status()
        key = settings.api_key
        return {
            "provider": settings.provider,
            "current": ai.describe(settings) if settings.provider else None,
            "ollama": {
                **ollama,
                "url": ai.ollama_url,
                "selected_model": settings.model if settings.provider == "ollama" else None,
            },
            "anthropic": {
                "configured": bool(key),
                "key_hint": f"…{key[-4:]}" if key else None,
                "models": ANTHROPIC_MODELS,
                "selected_model": settings.model if settings.provider == "anthropic" else None,
            },
            "embeddings": "ollama"
            if settings.provider == "ollama" and ollama["embedding"]
            else "builtin",
        }

    @api.put("/ai/settings")
    def save_ai_settings(body: AISettingsBody, user: UserDep) -> dict:
        api_key = body.api_key.strip() if body.api_key else None
        if body.provider == "anthropic" and not (api_key or db.ai_settings(user).api_key):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Add an API key to use a hosted model."
            )
        if body.provider == "anthropic" and body.model and body.model not in ANTHROPIC_MODELS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown Claude model.")
        db.save_ai_settings(
            user,
            provider=body.provider,
            model=body.model,
            api_key=api_key,
            clear_key=body.clear_key,
        )
        return ai_status(user)

    @api.post("/ai/test")
    def test_ai(user: UserDep) -> dict:
        try:
            ai.limiter.check(user.id)
            return ai.test(ai_settings_for(user))
        except AIError as e:
            return {"ok": False, "error": str(e)}

    @api.post("/tutor")
    def ask_tutor(body: TutorRequest, user: UserDep) -> StreamingResponse:
        """Stream a tutor reply as JSON lines: meta (which model), text chunks, done/error."""
        module = module_or_404(body.module_id)
        lesson = lesson_or_404(module, body.lesson)
        step_or_404(lesson, body.step)
        if lesson.spec.project and db.project_level(user, module.spec.id, lesson.slug) == "solo":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "The tutor is off in Solo. Switch to Assisted or Guided for help.",
            )
        lab_files = None
        step = lesson.spec.steps[body.step]
        if body.session_id and isinstance(step, ExerciseStep) and lesson.exercises[step.ref].is_lab:
            session = own_session(body.session_id, user)
            lab_files = lab.read_files(session.container, lab.lab_dir(lesson.exercises[step.ref]))
        ctx = tutor.context_for(
            module, lesson, body.step, code=body.code, lab_files=lab_files, feedback=body.feedback
        )
        messages = tutor.trim_messages([m.model_dump() for m in body.messages])
        if not messages:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ask the tutor something first.")
        settings = ai_settings_for(user)

        def events() -> Iterator[str]:
            def line(**event) -> str:
                return json.dumps(event) + "\n"

            guard = tutor.LeakGuard(ctx.solution, allowed=f"{ctx.starter}\n{ctx.code}")
            try:
                ai.limiter.check(user.id)
                chunks = ai.chat_stream(
                    settings, tutor.system_prompt(ctx), messages, tutor.MAX_REPLY_TOKENS
                )
                model = next(chunks)
                yield line(type="meta", provider=settings.provider, model=model)
                for chunk in chunks:
                    for text in guard.feed(chunk):
                        yield line(type="text", text=text)
                for text in guard.finish():
                    yield line(type="text", text=text)
                db.record(user, module.spec.id, f"{lesson.slug}/{body.step}", tutor_questions=1)
                review_helped(user, module.spec.id, f"{lesson.slug}/{body.step}")
                yield line(type="done", redactions=guard.redactions)
            except AIError as e:
                yield line(type="error", message=str(e))

        return StreamingResponse(events(), media_type="application/x-ndjson")

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
                    "view": m.spec.default_view,
                    "language": m.spec.language,
                    "ai": m.spec.sandbox.ai,
                    "prerequisites": m.spec.prerequisites,
                    "lessons": [
                        {
                            "slug": lesson.slug,
                            "title": lesson.spec.title,
                            "summary": lesson.spec.summary,
                            "project": {"uses": lesson.spec.project.uses}
                            if lesson.spec.project
                            else None,
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
        project = lesson.spec.project
        steps = [_public_step(lesson, i, step) for i, step in enumerate(lesson.spec.steps)]
        if project:
            # Projects send every level's starter and the learner's last passing code, so
            # assisted/solo learners can carry their own code forward between checkpoints.
            for public, step in zip(steps, lesson.spec.steps, strict=True):
                if isinstance(step, ExerciseStep):
                    exercise = lesson.exercises[step.ref]
                    public["exercise"]["starters"] = {
                        level: (path.read_text(encoding="utf-8") if path else None)
                        for level in LEVELS
                        for path in [exercise.starter_for(level)]
                    }
                    saved = db.submission(user, exercise.spec.id)
                    public["exercise"]["submission"] = saved[0] if saved else None
        return {
            "module_id": module_id,
            "slug": slug,
            "title": lesson.spec.title,
            "summary": lesson.spec.summary,
            "view": (project and project.view) or module.spec.default_view,
            "language": module.spec.language,
            "ai": bool(project and project.ai) or module.spec.sandbox.ai,
            "project": {
                "brief": project.brief,
                "uses": project.uses,
                "level": db.project_level(user, module_id, slug),
            }
            if project
            else None,
            "previous": slugs[position - 1] if position > 0 else None,
            "next": slugs[position + 1] if position + 1 < len(slugs) else None,
            "steps": steps,
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

    @api.get("/modules/{module_id}/glossary")
    def get_glossary(module_id: str, user: UserDep) -> dict[str, str]:
        return module_or_404(module_id).glossary

    @api.get("/exercises/{exercise_id}")
    def get_exercise(exercise_id: str, user: UserDep) -> dict:
        return _public_exercise(exercise_or_404(exercise_id))

    @api.put("/modules/{module_id}/lessons/{slug}/level")
    def set_level(module_id: str, slug: str, body: LevelBody, user: UserDep) -> dict:
        lesson = lesson_or_404(module_or_404(module_id), slug)
        if not lesson.spec.project:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "only projects have levels")
        db.set_project_level(user, module_id, slug, body.level)
        return {"level": body.level}

    @api.get("/modules/{module_id}/lessons/{slug}/steps/{index}/hints/{level}")
    def get_hint(module_id: str, slug: str, index: int, level: int, user: UserDep) -> dict:
        """Levels 1..n are hints; level n+1 is "show me" (the solution)."""
        module = module_or_404(module_id)
        lesson = lesson_or_404(module, slug)
        step = step_or_404(lesson, index)
        if isinstance(step, TryItStep):
            hints, solution = step.hints, step.solution
            solution_files = None
        elif isinstance(step, ExerciseStep):
            exercise = lesson.exercises[step.ref]
            hints = exercise.spec.hints
            if exercise.is_lab:
                solution = (exercise.dir / "solution.sh").read_text(encoding="utf-8")
                solution_files = {
                    p.relative_to(exercise.dir / "solution").as_posix(): p.read_text(
                        encoding="utf-8"
                    )
                    for p in sorted((exercise.dir / "solution").rglob("*"))
                    if p.is_file()
                }
            else:
                solution = exercise.solution_path.read_text(encoding="utf-8")
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "this step has no hints")
        if not 1 <= level <= len(hints) + 1:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"levels go from 1 to {len(hints) + 1}")
        if lesson.spec.project:
            project_level = db.project_level(user, module_id, slug)
            if project_level == "solo":
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Hints are off in Solo. Switch to Assisted or Guided for help.",
                )
            if project_level == "assisted" and level > len(hints):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, "Show me is only in Guided. Switch level to see it."
                )
        ref = f"{slug}/{index}"
        if level <= len(hints):
            db.record(user, module_id, ref, hints_used=level)
            review_helped(user, module_id, ref)
            return {"level": level, "of": len(hints), "hint": hints[level - 1]}
        db.record(user, module_id, ref, hints_used=len(hints), showed_solution=True)
        review_answer(user, module_id, ref, passed=False)
        shown = {"level": level, "of": len(hints), "solution": solution}
        if isinstance(step, ExerciseStep) and lesson.exercises[step.ref].is_lab:
            shown["solution_files"] = solution_files
        return shown

    @api.post("/modules/{module_id}/lessons/{slug}/steps/{index}/answer")
    def answer_quiz(module_id: str, slug: str, index: int, body: QuizAnswer, user: UserDep) -> dict:
        step = step_or_404(lesson_or_404(module_or_404(module_id), slug), index)
        if not isinstance(step, QuizStep):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "this step is not a quiz")
        correct = body.answer == step.answer
        db.record(user, module_id, f"{slug}/{index}", attempt=True, done=correct)
        review_answer(user, module_id, f"{slug}/{index}", correct)
        # The right answer is only revealed by getting it right.
        return {"correct": correct, "explanation": step.explanation if correct else ""}

    @api.post(
        "/modules/{module_id}/lessons/{slug}/steps/{index}/viewed",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def mark_viewed(module_id: str, slug: str, index: int, user: UserDep) -> None:
        step = step_or_404(lesson_or_404(module_or_404(module_id), slug), index)
        if not isinstance(step, ExplainStep | ExampleStep | ShowcaseStep):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "this step is completed by doing it")
        db.record(user, module_id, f"{slug}/{index}", done=True)

    # -- skills, review, streaks --

    @api.get("/skills")
    def skill_map(user: UserDep, tz: int = 0) -> dict:
        """The skill map, streaks and how many reviews are due. tz: minutes east of UTC."""
        now = time.time()
        cards = db.review_cards(user)
        return {
            "streak": skills.streaks(db.activity_since(user, 0), now, max(-840, min(tz, 840))),
            "reviews_due": len(skills.due_cards(content, cards, now)),
            "modules": skills.skill_map(content, db.all_progress(user), cards, now),
        }

    @api.get("/review")
    def reviews_due(user: UserDep) -> list[dict]:
        """Review cards due now, oldest first."""
        return skills.due_cards(content, db.review_cards(user), time.time())

    # -- portfolio --

    def finished_project(user: User, module: LoadedModule, lesson: LoadedLesson) -> dict | None:
        """A project counts as finished when every checkpoint has passed."""
        project = lesson.spec.project
        if not project:
            return None
        checkpoints = [s for s in lesson.spec.steps if isinstance(s, ExerciseStep)]
        saved = [db.submission(user, lesson.exercises[s.ref].spec.id) for s in checkpoints]
        if not checkpoints or not all(saved):
            return None
        view = project.view or module.spec.default_view
        return {
            "module_id": module.spec.id,
            "slug": lesson.slug,
            "title": lesson.spec.title,
            "summary": lesson.spec.summary,
            "brief": project.brief,
            "uses": project.uses,
            "level": db.project_level(user, module.spec.id, lesson.slug),
            "view": view,
            "checkpoints": [lesson.exercises[s.ref].spec.title for s in checkpoints],
            "code": saved[-1][0],
            "completed_at": max(when for _, when in saved),
        }

    @api.get("/portfolio")
    def portfolio(user: UserDep) -> list[dict]:
        items = [
            item
            for module in content.modules.values()
            for lesson in module.lessons
            if (item := finished_project(user, module, lesson))
        ]
        return sorted(items, key=lambda item: item["completed_at"], reverse=True)

    @api.get("/portfolio/{module_id}/{slug}/export")
    def export_project(module_id: str, slug: str, user: UserDep) -> Response:
        module = module_or_404(module_id)
        item = finished_project(user, module, lesson_or_404(module, slug))
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "finish every checkpoint first")
        return Response(
            export_zip(item, user.username),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{slug}.zip"'},
        )

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
        result = grader.run_program(
            body.code, body.inputs, executor=session.executor, language=language_of(session)
        )
        explanation = explain_traceback(result.stderr, body.code)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "timed_out": result.timed_out,
            "explanation": asdict(explanation) if explanation else None,
        }

    @api.post("/sessions/{session_id}/trace")
    def trace(session_id: str, body: RunRequest, user: UserDep) -> dict:
        """Step-by-step trace of a pseudocode program, for the step-through view."""
        session = own_session(session_id, user)
        if language_of(session) != "pseudo":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "only pseudocode can be traced")
        return grader.trace_program(body.code, body.inputs, executor=session.executor)

    @api.post("/sessions/{session_id}/check")
    def check(session_id: str, body: CheckRequest, user: UserDep) -> dict:
        session = own_session(session_id, user)
        exercise = exercise_or_404(body.exercise_id)
        if exercise.module_id != session.module_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "exercise is from another module")
        if exercise.is_lab:
            target = lab.lab_dir(exercise)
            result = grader.grade_lab(exercise, target, executor=session.executor)
            submitted = (
                json.dumps(lab.read_files(session.container, target)) if result.passed else ""
            )
        else:
            result = grader.grade(exercise, body.code, executor=session.executor)
            submitted = body.code
        if (ref := _exercise_step_ref(content, exercise)) is not None:
            db.record(user, exercise.module_id, ref, attempt=True, done=result.passed)
            review_answer(user, exercise.module_id, ref, result.passed)
        if result.passed:
            db.save_submission(user, exercise.spec.id, submitted)
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
        result = grader.run_snippet(
            body.code, step.check, executor=session.executor, language=language_of(session)
        )
        db.record(
            user, session.module_id, f"{body.lesson}/{body.step}", attempt=True, done=result.passed
        )
        review_answer(user, session.module_id, f"{body.lesson}/{body.step}", result.passed)
        return {"passed": result.passed, "message": explain_message(result.message, body.code)}

    # -- labs --

    def lab_exercise(session: Session, exercise_id: str) -> LoadedExercise:
        exercise = exercise_or_404(exercise_id)
        if not session.lab or exercise.module_id != session.module_id or not exercise.is_lab:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "not a lab exercise in this session")
        return exercise

    def lab_state(session: Session, exercise: LoadedExercise) -> dict:
        target = lab.lab_dir(exercise)
        return {"dir": target, "files": lab.read_files(session.container, target)}

    @api.post("/sessions/{session_id}/lab/{exercise_id}/open")
    def lab_open(session_id: str, exercise_id: str, user: UserDep) -> dict:
        """Seed the exercise folder (first time only) and return its files."""
        session = own_session(session_id, user)
        exercise = lab_exercise(session, exercise_id)
        lab.seed(session.container, exercise)
        return lab_state(session, exercise)

    @api.get("/sessions/{session_id}/lab/{exercise_id}/files")
    def lab_files(session_id: str, exercise_id: str, user: UserDep) -> dict:
        session = own_session(session_id, user)
        return lab_state(session, lab_exercise(session, exercise_id))

    @api.put("/sessions/{session_id}/lab/{exercise_id}/files")
    def lab_write(session_id: str, exercise_id: str, body: LabFile, user: UserDep) -> dict:
        session = own_session(session_id, user)
        exercise = lab_exercise(session, exercise_id)
        try:
            lab.write_file(session.container, exercise, body.path, body.content)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
        return {"saved": lab.safe_path(body.path)}

    @api.delete("/sessions/{session_id}/lab/{exercise_id}/files")
    def lab_delete(session_id: str, exercise_id: str, path: str, user: UserDep) -> dict:
        session = own_session(session_id, user)
        exercise = lab_exercise(session, exercise_id)
        try:
            lab.delete_file(session.container, exercise, path)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
        return lab_state(session, exercise)

    @api.post("/sessions/{session_id}/lab/{exercise_id}/reset")
    def lab_reset(session_id: str, exercise_id: str, body: LabReset, user: UserDep) -> dict:
        """Put the starter files back (and optionally clear the engine)."""
        session = own_session(session_id, user)
        exercise = lab_exercise(session, exercise_id)
        if body.engine:
            lab.reset_engine(session.container)
        lab.seed(session.container, exercise, force=True)
        return lab_state(session, exercise)

    @api.websocket("/sessions/{session_id}/terminal")
    async def terminal(websocket: WebSocket, session_id: str, dir: str = "/work") -> None:
        """A bash shell in a lab session. Client: {"i": keys} or {"r": [cols, rows]} as
        JSON text. Server: raw terminal output as binary frames."""
        session, _ = await _ws_session(websocket, session_id)
        if session is None:
            return
        if not session.lab:
            await websocket.close(code=4400, reason="terminals are for lab modules")
            return
        start = dir if dir.startswith("/work") and ".." not in dir else "/work"
        loop = asyncio.get_running_loop()
        outgoing: asyncio.Queue[bytes | None] = asyncio.Queue()

        def on_output(chunk: bytes) -> None:
            loop.call_soon_threadsafe(outgoing.put_nowait, chunk)

        shell = await run_in_threadpool(lab.Terminal, session.container, start, on_output)

        async def forward() -> None:
            while (chunk := await outgoing.get()) is not None:
                await websocket.send_bytes(chunk)

        async def watch_exit() -> None:
            while shell.alive:
                await asyncio.sleep(0.5)
            await asyncio.sleep(0.2)  # let the last output through
            with contextlib.suppress(RuntimeError):
                await websocket.close(code=1000, reason="shell exited")

        sender = asyncio.create_task(forward())
        watcher = asyncio.create_task(watch_exit())
        try:
            while True:
                message = json.loads(await websocket.receive_text())
                if isinstance(message, dict):
                    session.last_used = time.monotonic()
                    await run_in_threadpool(shell.send, message)
        except (WebSocketDisconnect, ValueError, RuntimeError):
            pass
        finally:
            sender.cancel()
            watcher.cancel()
            await run_in_threadpool(shell.close)

    async def _ws_session(
        websocket: WebSocket, session_id: str
    ) -> tuple[Session, User] | tuple[None, None]:
        await websocket.accept()
        user = db.user_for_token(websocket.cookies.get(COOKIE, ""))
        try:
            session = sessions.get(session_id) if user else None
        except KeyError:
            session = None
        if user is None or session is None or session.owner != user.id:
            await websocket.close(code=4404, reason="session not found")
            return None, None
        return session, user

    @api.websocket("/sessions/{session_id}/stream")
    async def stream(websocket: WebSocket, session_id: str) -> None:
        """Interactive run.

        Client: {"type": "run", "code": ...}, then any number of
        {"type": "stdin", "data": "..."} and optionally {"type": "stop"}.
        Server: {"type": "output", "data": ...} messages, then one {"type": "exit", ...}.
        """
        session, user = await _ws_session(websocket, session_id)
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
                language=language_of(session),
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

    @api.websocket("/sessions/{session_id}/kernel")
    async def kernel(websocket: WebSocket, session_id: str) -> None:
        """Notebook kernel. Started on the first execute; stopped when the socket closes.

        Client: {"type": "execute", "cell": <cell id>, "code": ...}, {"type": "interrupt"},
        {"type": "restart"}. Server: kernel messages (see dojo._kernel), each tagged with
        "cell"; errors also carry "explanation" and "line". Plus {"type": "status", ...}
        and {"type": "dead", "reason": ...}.
        """
        session, user = await _ws_session(websocket, session_id)
        if session is None:
            return
        loop = asyncio.get_running_loop()
        outgoing: asyncio.Queue[dict] = asyncio.Queue()

        def emit(message: dict) -> None:
            loop.call_soon_threadsafe(outgoing.put_nowait, message)

        running: Kernel | None = None

        async def forward() -> None:
            while True:
                await websocket.send_json(await outgoing.get())

        sender = asyncio.create_task(forward())
        try:
            while True:
                message = await websocket.receive_json()
                kind = message.get("type")
                if kind == "execute":
                    if running is None or not running.alive:
                        emit({"type": "status", "state": "starting"})
                        running = await run_in_threadpool(
                            Kernel,
                            session.executor.container,
                            emit,
                            # Settings are read per call, so switching model applies at once.
                            lambda kind, payload: ai.handle(
                                user.id, ai_settings_for(user), kind, payload
                            ),
                        )
                    code = str(message.get("code", ""))[:MAX_CODE]
                    await run_in_threadpool(running.execute, code, str(message.get("cell", "")))
                elif kind == "interrupt" and running is not None:
                    await run_in_threadpool(running.interrupt)
                elif kind == "restart":
                    if running is not None:
                        await run_in_threadpool(running.close)
                        running = None
                    emit({"type": "status", "state": "restarted"})
        except (WebSocketDisconnect, ValueError, RuntimeError):
            pass
        finally:
            sender.cancel()
            if running is not None:
                await run_in_threadpool(running.close)

    @api.websocket("/sessions/{session_id}/lsp")
    async def lsp(websocket: WebSocket, session_id: str) -> None:
        """Language Server Protocol bridge: one JSON-RPC message per WebSocket text frame."""
        session, user = await _ws_session(websocket, session_id)
        if session is None:
            return
        loop = asyncio.get_running_loop()
        replies: asyncio.Queue[dict] = asyncio.Queue()
        sandbox = content.modules[session.module_id].spec.sandbox
        server = await run_in_threadpool(
            LanguageServer,
            sandbox.image,
            lambda msg: loop.call_soon_threadsafe(replies.put_nowait, msg),
            sandbox.memory,
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
        "starter": "" if ex.is_lab else ex.starter_path.read_text(encoding="utf-8"),
        "visible_tests": ex.visible_tests.read_text(encoding="utf-8"),
        "lab": {"dir": lab.lab_dir(ex)} if ex.is_lab else None,
    }


def _public_step(lesson: LoadedLesson, index: int, step: Step) -> dict:
    base: dict = {"index": index, "type": step.type}
    match step:
        case ExplainStep():
            return {**base, "md": step.md}
        case ExampleStep():
            return {
                **base,
                "md": step.md,
                "code": step.code,
                "runnable": step.runnable,
                "language": step.language,
            }
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
        case ShowcaseStep():
            return {**base, "algorithm": step.algorithm, "md": step.md, "input": step.input}
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
