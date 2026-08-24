"""FastAPI dependencies. Tests override get_agent to avoid a real Groq client."""

from app.agent.agent import SupportAgent
from app.config.settings import GROQ_MODEL


def get_agent() -> SupportAgent:
    return SupportAgent(model=GROQ_MODEL)
