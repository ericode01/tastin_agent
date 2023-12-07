from fastapi import FastAPI
from ConversationalAgentManager import ConversationalAgentManager
from models.ApiModels import AskAgentRequest, AskAgentResponse

app = FastAPI()
conversational_agent_manager = ConversationalAgentManager()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/weatai/ask/")
async def ask_agent(ask_agent_request: AskAgentRequest) -> AskAgentResponse:
    user_id = ask_agent_request.user_id
    session_id = ask_agent_request.session_id
    user_prompt = ask_agent_request.user_prompt

    result = conversational_agent_manager.ask_agent(session_id=session_id, user_prompt=user_prompt)

    response = AskAgentResponse(
        user_id=user_id,
        session_id=session_id,
        user_prompt=user_prompt,
        agent_response_text=result["response_text"],
        agent_references=result["references_json"]
    )

    return response

# def print_hi(name):
#     # Use a breakpoint in the code line below to debug your script.
#     print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.
#
#
# # Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#     print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
