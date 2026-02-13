"""FastAPI web backend for the BC Learning Bot."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from learning_bot import config
from learning_bot.responses import ChatResponse, ResponseType

app = FastAPI(title="BC Learning Bot", version="0.1.0")

# In-memory session store: session_id -> Agent
_sessions: dict[str, object] = {}

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


# ---------- Request / response models ----------

class SessionRequest(BaseModel):
    name: str


class SessionResponse(BaseModel):
    session_id: str
    student_name: str
    greeting: dict | None = None
    progress: dict | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


# ---------- Helpers ----------

def _create_agent(student_name: str) -> tuple[str, object]:
    """Create a new Agent and return (web_session_id, agent)."""
    from learning_bot.curriculum.loader import CurriculumLoader
    from learning_bot.curriculum.navigator import CurriculumNavigator
    from learning_bot.progress import ProgressTracker
    from learning_bot.session import SessionManager
    from learning_bot.storage.database import Database

    config.DB_DIR.mkdir(parents=True, exist_ok=True)
    db = Database(config.DB_PATH)
    db.init_db()

    session_mgr = SessionManager(db)
    session_info = session_mgr.start_session(student_name)
    student = db.get_student(session_info.student_id)

    nav = None
    try:
        loader = CurriculumLoader()
        curriculum = loader.load_curriculum(config.CURRICULUM_DIR, config.DEFAULT_CURRICULUM)
        nav = CurriculumNavigator(curriculum)
    except Exception:
        pass

    progress = ProgressTracker(db) if nav else None

    from learning_bot.agent import Agent

    agent = Agent(
        db=db,
        student_id=student.id,
        student_name=student.name,
        session_id=session_info.session_id,
        curriculum_nav=nav,
        progress_tracker=progress,
    )

    web_session_id = uuid.uuid4().hex
    return web_session_id, agent


def _get_agent(session_id: str):
    """Retrieve an agent by web session id, or raise 404."""
    agent = _sessions.get(session_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return agent


def _get_progress_data(agent) -> dict | None:
    """Build progress data dict from an agent."""
    if not agent.nav or not agent.progress:
        return None

    all_progress = agent.progress.get_all_progress(agent.student_id)
    stats = agent.nav.get_progress_summary(all_progress)

    table_data = []
    for module in agent.nav.curriculum.modules:
        for lesson in module.lessons:
            status = "not_started"
            for p in all_progress:
                if p.module_id == module.id and p.lesson_id == lesson.id:
                    status = p.status
                    break
            table_data.append({
                "module_id": module.id,
                "module_title": module.title,
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "status": status,
            })

    current = agent.nav.get_current_lesson(all_progress)
    current_mod = current[0].id if current else None
    current_les = current[1].id if current else None

    return {
        "status_table": table_data,
        "stats": stats,
        "current_module": current_mod,
        "current_lesson": current_les,
    }


def _get_curriculum_tree(agent) -> list[dict] | None:
    """Build a curriculum tree for the sidebar."""
    if not agent.nav:
        return None

    all_progress = []
    if agent.progress:
        all_progress = agent.progress.get_all_progress(agent.student_id)

    modules = []
    for module in agent.nav.curriculum.modules:
        lessons = []
        for lesson in module.lessons:
            status = "not_started"
            for p in all_progress:
                if p.module_id == module.id and p.lesson_id == lesson.id:
                    status = p.status
                    break
            lessons.append({
                "id": lesson.id,
                "title": lesson.title,
                "status": status,
            })
        modules.append({
            "id": module.id,
            "title": module.title,
            "order": module.order,
            "lessons": lessons,
        })
    return modules


# ---------- API endpoints ----------

@app.post("/api/session")
def create_session(req: SessionRequest) -> JSONResponse:
    """Create or resume a learning session."""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    web_session_id, agent = _create_agent(name)
    _sessions[web_session_id] = agent

    # Initialize (auto-start + greeting)
    greeting_resp = agent.initialize()
    greeting_dict = greeting_resp.to_dict() if greeting_resp else None

    progress_data = _get_progress_data(agent)

    return JSONResponse({
        "session_id": web_session_id,
        "student_name": agent.student_name,
        "greeting": greeting_dict,
        "progress": progress_data,
    })


@app.post("/api/chat")
def chat(req: ChatRequest) -> JSONResponse:
    """Send a message and get a response."""
    agent = _get_agent(req.session_id)

    response: ChatResponse = agent.chat(req.message)
    result = response.to_dict()

    # Always include fresh progress data
    result["progress"] = _get_progress_data(agent)

    return JSONResponse(result)


@app.get("/api/status/{session_id}")
def get_status(session_id: str) -> JSONResponse:
    """Get current progress data for the sidebar."""
    agent = _get_agent(session_id)
    progress_data = _get_progress_data(agent)
    return JSONResponse(progress_data or {})


@app.get("/api/tokens/{session_id}")
def get_tokens(session_id: str) -> JSONResponse:
    """Get token usage summary and estimated cost for a session."""
    agent = _get_agent(session_id)
    summary = agent.db.get_session_token_summary(agent.session_id)
    return JSONResponse(summary)


@app.get("/api/curriculum/{session_id}")
def get_curriculum(session_id: str) -> JSONResponse:
    """Get the curriculum tree."""
    agent = _get_agent(session_id)
    tree = _get_curriculum_tree(agent)
    return JSONResponse(tree or [])


@app.get("/")
def index():
    """Serve the frontend."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="Frontend not found")
    return FileResponse(index_path, media_type="text/html")


# Mount static files (CSS, JS, images if any) — after route definitions
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
