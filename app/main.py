from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

from app.agent import refund_agent

load_dotenv()

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Retail Refund Service")
session_service = InMemorySessionService()

runner = Runner(
    agent=refund_agent,
    app_name="retail_refund_service",
    session_service=session_service,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def ui():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Retail Refund Agent", "version": "1.0.2"}


async def ensure_session(user_id: str, session_id: str) -> None:
    """Create session once; reuse it for follow-up messages in the same chat."""
    existing = await session_service.get_session(
        app_name="retail_refund_service",
        user_id=user_id,
        session_id=session_id,
    )
    if existing:
        return
    try:
        await session_service.create_session(
            app_name="retail_refund_service",
            user_id=user_id,
            session_id=session_id,
        )
    except AlreadyExistsError:
        pass


@app.post("/chat")
async def chat(user_id: str, session_id: str, message: str):
    await ensure_session(user_id, session_id)
    new_msg = types.Content(role="user", parts=[types.Part(text=message)])

    response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_msg,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text

    return {"reply": response_text}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
