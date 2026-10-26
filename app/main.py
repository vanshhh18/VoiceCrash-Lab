
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

app = FastAPI(title="VoiceCrashLab Target Agent")

llm = ChatGroq(
    model=os.getenv("TARGET_AGENT_MODEL", "openai/gpt-oss-120b"),
    temperature=0.2,
    api_key=os.getenv("GROQ_API_KEY"),
)

SYSTEM_PROMPT = """
You are a customer support voice agent for a fictional delivery service.
Speak naturally and politely in the language used by the caller, including
Hindi, English, or Hinglish.

Understand the caller's intent rather than relying on exact keywords.
Handle corrections, interruptions, changing dates, incomplete information,
and ambiguous requests conversationally.

Ask a concise clarification question when essential information is missing.
Acknowledge corrections and use the caller's latest confirmed instruction.
Do not claim that a delivery has actually been changed or booked unless
you have a tool that confirms the action. Never invent account information.

Keep responses brief and suitable for a spoken phone conversation.
"""


@app.get("/")
def home():
    return {"message": "VoiceCrashLab LLM Target Agent is running!"}


@app.post("/chat")
def chat(message: str):
    if not message.strip():
        return {"response": "Could you please repeat your request?"}

    try:
        result = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message),
        ])
        return {"response": result.content.strip()}
    except Exception:
        # Avoid exposing API keys or internal exception details.
        raise HTTPException(
            status_code=502,
            detail="The target agent could not get a response from the LLM provider.",
        )
