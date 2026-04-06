import os
import sys
from typing import Dict, Any, Optional, Generator

from dotenv import load_dotenv

# Ensure local imports work when running from project root.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider


class MockProvider(LLMProvider):
    """Offline provider for deterministic ReAct demo and logging."""

    def __init__(self) -> None:
        super().__init__(model_name="mock-react")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if "Observation:" not in prompt:
            content = 'Thought: I should use calculator.\nAction: calculator({"a": 2, "b": 2})'
        else:
            content = "Final Answer: 2 + 2 = 4."

        return {
            "content": content,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "latency_ms": 1,
            "provider": "mock",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt)["content"]


def calculator(a: float, b: float) -> float:
    return a + b


def main() -> None:
    load_dotenv()

    provider = MockProvider()
    tools = [
        {
            "name": "calculator",
            "description": "Add two numbers. Args: {\"a\": number, \"b\": number}.",
            "function": calculator,
        }
    ]

    agent = ReActAgent(llm=provider, tools=tools, max_steps=5)
    question = "What is 2 + 2?"
    answer = agent.run(question)
    print("User:", question)
    print("Assistant:", answer)


if __name__ == "__main__":
    main()
