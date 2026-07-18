import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

from app.agent import refund_agent

load_dotenv()

app = FastAPI(title="Retail Refund Service")
session_service = InMemorySessionService()

runner = Runner(
    agent=refund_agent,
    app_name="retail_refund_service",
    session_service=session_service,
)


@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Retail Refund Agent"}


@app.post("/chat")
async def chat(user_id: str, session_id: str, message: str):
    await session_service.create_session(
        app_name="retail_refund_service",
        user_id=user_id,
        session_id=session_id,
    )
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
