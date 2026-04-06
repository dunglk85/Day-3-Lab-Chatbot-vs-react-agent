import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List

from chatbot import ask_chatbot
from tools import build_tools


def _log_event(event: str, data: Dict[str, Any]) -> None:
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", f"{datetime.now().strftime('%Y-%m-%d')}.log")
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        "data": data,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


class ReActAgent:
    def __init__(self, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.tools = tools
        self.max_steps = max_steps

    def _mock_llm(self, prompt: str) -> str:
        p = prompt.lower()
        if "capital of france" in p:
            return "Final Answer: The capital of France is Paris."
        if "find stock of iphone" in p and "observation:" not in p:
            return 'Thought: Need stock first.\nAction: check_stock({"item_name":"iphone"})'
        if "'total':" in prompt and "'tax':" in prompt:
            return (
                "Final Answer: iPhone stock is 12 units. "
                "Subtotal is 14400.0, tax is 1440.0, total is 15840.0."
            )
        if "'unit_price':" in prompt and "'stock':" in prompt:
            return 'Thought: Need total with tax.\nAction: apply_tax({"amount": 14400.0, "tax_rate": 0.1})'
        return "Final Answer: I do not have enough information."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        for tool in self.tools:
            if tool["name"] == tool_name:
                fn = tool["function"]
                parsed = json.loads(args) if args else {}
                if isinstance(parsed, dict):
                    return str(fn(**parsed))
                if isinstance(parsed, list):
                    return str(fn(*parsed))
                return str(fn(parsed))
        return f"Tool {tool_name} not found."

    def run(self, user_input: str) -> str:
        _log_event("AGENT_START", {"input": user_input})
        prompt = user_input
        step = 0
        while step < self.max_steps:
            step += 1
            response = self._mock_llm(prompt)
            _log_event("AGENT_STEP", {"step": step, "response": response})

            final = re.search(r"Final Answer:\s*(.+)", response, flags=re.IGNORECASE | re.DOTALL)
            if final:
                answer = final.group(1).strip()
                _log_event("AGENT_END", {"status": "success", "steps": step, "answer": answer})
                return answer

            action = re.search(r"Action:\s*([a-zA-Z_]\w*)\(([\s\S]*)\)\s*$", response)
            if not action:
                _log_event("AGENT_END", {"status": "parse_error", "steps": step})
                return "Agent failed to parse action."

            tool_name = action.group(1).strip()
            args = action.group(2).strip()
            obs = self._execute_tool(tool_name, args)
            _log_event("TOOL_EXECUTION", {"step": step, "tool": tool_name, "args": args, "observation": obs})
            prompt += f"\nAssistant:\n{response}\nObservation: {obs}\n"

        _log_event("AGENT_END", {"status": "max_steps", "steps": step})
        return "I could not complete the task within max_steps."


def run_demo() -> None:
    tools = build_tools()
    agent = ReActAgent(tools=tools, max_steps=5)

    cases = [
        "Find stock of iPhone, then calculate total with tax.",
        "What is the capital of France?",
    ]

    for prompt in cases:
        chatbot_answer = ask_chatbot(prompt)
        agent_answer = agent.run(prompt)
        print("User:", prompt)
        print("Chatbot:", chatbot_answer)
        print("Agent:", agent_answer)
        print()


if __name__ == "__main__":
    run_demo()
