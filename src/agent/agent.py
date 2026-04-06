import os
import re
import json
from typing import List, Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        TODO: Implement the system prompt that instructs the agent to follow ReAct.
        Should include:
        1.  Available tools and their descriptions.
        2.  Format instructions: Thought, Action, Observation.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""
You are an intelligent assistant that MUST follow ReAct.

Available tools:
{tool_descriptions}

Rules:
1) Think step by step.
2) If a tool is needed, respond with EXACTLY:
Thought: <reasoning>
Action: <tool_name>(<json_arguments>)
3) If enough information is available, respond with:
Final Answer: <answer>
4) Do not invent tools that are not listed.
5) JSON arguments must be valid JSON.
"""

    def run(self, user_input: str) -> str:
        """
        TODO: Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = user_input
        steps = 0

        while steps < self.max_steps:
            try:
                result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
                content = (result.get("content") or "").strip()
                self.history.append({"step": steps + 1, "response": content})

                logger.log_event(
                    "LLM_METRIC",
                    {
                        "step": steps + 1,
                        "provider": result.get("provider"),
                        "usage": result.get("usage", {}),
                        "latency_ms": result.get("latency_ms")
                    }
                )
                logger.log_event("AGENT_STEP", {"step": steps + 1, "response": content})
            except Exception as exc:
                logger.log_event("AGENT_ERROR", {"step": steps + 1, "error": str(exc), "code": "LLM_CALL_ERROR"})
                return f"Agent failed while calling LLM: {exc}"

            final_match = re.search(r"Final Answer:\s*(.+)", content, flags=re.IGNORECASE | re.DOTALL)
            if final_match:
                answer = final_match.group(1).strip()
                logger.log_event("AGENT_FINAL", {"step": steps + 1, "answer": answer})
                logger.log_event("AGENT_END", {"steps": steps + 1, "status": "success"})
                return answer

            action_match = re.search(r"Action:\s*([a-zA-Z_]\w*)\s*\(([\s\S]*)\)\s*$", content, flags=re.IGNORECASE)
            if not action_match:
                logger.log_event(
                    "AGENT_ERROR",
                    {"step": steps + 1, "error": "Could not parse Action or Final Answer", "code": "PARSER_ERROR"}
                )
                current_prompt += (
                    "\n\nObservation: Parser error - please follow EXACT format:\n"
                    "Thought: ...\nAction: tool_name({...})\nOR\nFinal Answer: ..."
                )
                steps += 1
                continue

            tool_name = action_match.group(1).strip()
            args = action_match.group(2).strip()
            observation = self._execute_tool(tool_name, args)
            logger.log_event(
                "TOOL_EXECUTION",
                {"step": steps + 1, "tool": tool_name, "args": args, "observation": observation}
            )

            current_prompt += (
                f"\n\nAssistant:\n{content}\n"
                f"Observation: {observation}\n"
                "Continue reasoning. If done, return Final Answer."
            )
            
            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps"})
        return "I could not complete the task within max_steps."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                fn = tool.get("function") or tool.get("func")
                if not callable(fn):
                    return f"Tool {tool_name} is not callable."

                try:
                    parsed_args: Any
                    if not args:
                        parsed_args = {}
                    else:
                        parsed_args = json.loads(args)
                except Exception:
                    parsed_args = args

                try:
                    if isinstance(parsed_args, dict):
                        result = fn(**parsed_args)
                    elif isinstance(parsed_args, list):
                        result = fn(*parsed_args)
                    else:
                        result = fn(parsed_args)
                except TypeError:
                    # Graceful fallback for tools expecting a single raw-argument string.
                    result = fn(args)
                except Exception as exc:
                    return f"Tool execution error: {exc}"

                return str(result)
        return f"Tool {tool_name} not found."


class ReActDemoProvider(LLMProvider):
    """
    Deterministic provider that follows ReAct format for demo/testing.
    """

    def __init__(self) -> None:
        super().__init__(model_name="react-demo")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        p = prompt.lower()

        if "capital of france" in p:
            content = "Final Answer: The capital of France is Paris."
        elif "find stock of iphone" in p and "observation:" not in p:
            content = 'Thought: I need inventory data first.\nAction: check_stock({"item_name":"iphone"})'
        elif "'total':" in prompt and "'tax':" in prompt:
            content = (
                "Final Answer: iPhone stock is 12 units. "
                "Subtotal is 14400.0, tax is 1440.0, so total with tax is 15840.0."
            )
        elif "'unit_price':" in prompt and "'stock':" in prompt:
            content = 'Thought: Now compute total with tax.\nAction: apply_tax({"amount": 14400.0, "tax_rate": 0.1})'
        else:
            content = "Final Answer: I do not have enough information."

        return {
            "content": content,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "latency_ms": 1,
            "provider": "react-demo",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt)["content"]
