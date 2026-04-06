from dotenv import load_dotenv
from src.core.local_provider import LocalProvider
from src.agent.agent import ReActAgent

load_dotenv()

def echo_tool(args: str) -> str:
    return f"Echo: {args}"

provider = LocalProvider(model_path="./models/Phi-3-mini-4k-instruct-q4.gguf")
agent = ReActAgent(provider, [
    {"name": "echo", "description": "Echo back the input text", "function": echo_tool}
])

print(agent.run("Please echo the phrase: hello world"))