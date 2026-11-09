"""HTTP + WebSocket API: content, sessions, and code execution.

M1 has no accounts; bind to localhost only. Auth arrives with M2.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from dojo import grader
from dojo.models import TryItStep
from dojo.registry import Content, LoadedExercise, load_content
from dojo.sandbox import SandboxError, Session, SessionManager

MAX_CODE = 100_000
REAP_INTERVAL_S = 30


# --- request / response bodies ---------------------------------------------


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


class RunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool


class TestResultOut(BaseModel):
    name: str
    label: str
    outcome: str
    message: str


class CheckResponse(BaseModel):
    passed: bool
    timed_out: bool
    results: list[TestResultOut]


class TryItResponse(BaseModel):
    passed: bool
    message: str


# --- app ---------------------------------------------------------------------


def create_app(content: Content | None = None, manager: SessionManager | None = None) -> FastAPI:
    if content is None:
        content = load_content(Path(os.environ.get("DOJO_CONTENT", "content")).resolve())
    sessions = manager or SessionManager(content)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(SessionManager.remove_orphans)
        reaper = asyncio.create_task(_reap_forever(sessions))
        try:
            yield
        finally:
            reaper.cancel()
            await run_in_threadpool(sessions.close_all)

    app = FastAPI(title="DataDojo", version="0.1.0", lifespan=lifespan)

    def session_or_404(session_id: str) -> Session:
        try:
            return sessions.get(session_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from None

    def exercise_or_404(exercise_id: str) -> LoadedExercise:
        exercise = content.exercise(exercise_id)
        if exercise is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "exercise not found")
        return exercise

    # -- content --

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "modules": len(content.modules)}

    @app.get("/modules")
    def list_modules() -> list[dict]:
        return [
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
                        "exercises": [ex.spec.id for ex in lesson.exercises.values()],
                    }
                    for lesson in m.lessons
                ],
            }
            for m in content.modules.values()
        ]

    @app.get("/exercises/{exercise_id}")
    def get_exercise(exercise_id: str) -> dict:
        # Never send solution.py, hidden tests, or hint text (hints are fetched one by one).
        ex = exercise_or_404(exercise_id)
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

    @app.get("/exercises/{exercise_id}/hints/{level}")
    def get_hint(exercise_id: str, level: int) -> dict:
        hints = exercise_or_404(exercise_id).spec.hints
        if not 1 <= level <= len(hints):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"hints go from 1 to {len(hints)}")
        return {"level": level, "of": len(hints), "hint": hints[level - 1]}

    # -- sessions --

    @app.post("/sessions", status_code=status.HTTP_201_CREATED)
    def create_session(body: CreateSession) -> dict:
        try:
            session = sessions.create(body.module_id)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "module not found") from None
        except SandboxError as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from None
        return {"session_id": session.id, "module_id": session.module_id}

    @app.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_session(session_id: str) -> None:
        session_or_404(session_id)
        sessions.close(session_id)

    @app.post("/sessions/{session_id}/run")
    def run(session_id: str, body: RunRequest) -> RunResponse:
        session = session_or_404(session_id)
        result = grader.run_program(body.code, body.inputs, executor=session.executor)
        return RunResponse(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            timed_out=result.timed_out,
        )

    @app.post("/sessions/{session_id}/check")
    def check(session_id: str, body: CheckRequest) -> CheckResponse:
        session = session_or_404(session_id)
        exercise = exercise_or_404(body.exercise_id)
        if exercise.module_id != session.module_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "exercise is from another module")
        result = grader.grade(exercise, body.code, executor=session.executor)
        return CheckResponse(
            passed=result.passed,
            timed_out=result.timed_out,
            results=[
                TestResultOut(name=r.name, label=r.label, outcome=r.outcome, message=r.message)
                for r in result.results
            ],
        )

    @app.post("/sessions/{session_id}/try-it")
    def try_it(session_id: str, body: TryItRequest) -> TryItResponse:
        session = session_or_404(session_id)
        module = content.modules[session.module_id]
        lesson = next((les for les in module.lessons if les.slug == body.lesson), None)
        if lesson is None or not 0 <= body.step < len(lesson.spec.steps):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "lesson step not found")
        step = lesson.spec.steps[body.step]
        if not isinstance(step, TryItStep):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "that step is not a try-it")
        result = grader.run_snippet(body.code, step.check, executor=session.executor)
        return TryItResponse(passed=result.passed, message=result.message)

    @app.websocket("/sessions/{session_id}/stream")
    async def stream(websocket: WebSocket, session_id: str) -> None:
        """Run code and stream its output as it is printed.

        Client sends {"code": ..., "inputs": [...]}; server sends
        {"type": "output", "data": ...} messages, then one {"type": "exit", ...}.
        """
        await websocket.accept()
        try:
            session = sessions.get(session_id)
        except KeyError:
            await websocket.close(code=4404, reason="session not found")
            return
        try:
            body = RunRequest.model_validate(await websocket.receive_json())
        except (ValidationError, ValueError) as e:
            await websocket.close(code=4400, reason=str(e)[:120])
            return

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str] = asyncio.Queue()

        def on_output(text: str) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, text)

        job = loop.run_in_executor(
            None,
            lambda: grader.run_program(
                body.code, body.inputs, executor=session.executor, on_output=on_output
            ),
        )
        try:
            while not (job.done() and queue.empty()):
                try:
                    text = await asyncio.wait_for(queue.get(), timeout=0.1)
                except TimeoutError:
                    continue
                await websocket.send_json({"type": "output", "data": text})
            result = await job
            await websocket.send_json(
                {"type": "exit", "exit_code": result.returncode, "timed_out": result.timed_out}
            )
            await websocket.close()
        except WebSocketDisconnect:
            pass  # the run finishes on its own (it is time-limited)

    return app


async def _reap_forever(sessions: SessionManager) -> None:
    while True:
        await asyncio.sleep(REAP_INTERVAL_S)
        await run_in_threadpool(sessions.reap_idle)
