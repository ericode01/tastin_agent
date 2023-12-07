from pydantic import BaseModel


class AskAgentRequest(BaseModel):
    user_id: str
    session_id: str
    user_prompt: str


class AskAgentResponse(BaseModel):
    user_id: str
    session_id: str
    user_prompt: str
    agent_response_text: str
    agent_references: dict | None
