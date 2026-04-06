import os
import re
from typing import List, Dict, Any, Optional
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
        You are an intelligent assistant. You have access to the following tools:
        {tool_descriptions}

        Use the following format:
        Thought: your line of reasoning.
        Action: tool_name(arguments)
        Observation: result of the tool call.
        ... (repeat Thought/Action/Observation if needed)
        Final Answer: your final response.
        """

    def run(self, user_input: str) -> str:
        """
        TODO: Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        system_prompt = self.get_system_prompt()
        current_prompt = user_input.strip()
        steps = 0
        final_answer = None

        while steps < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=system_prompt)
            content = result.get("content", "").strip()
            logger.log_event("LLM_RESPONSE", {
                "step": steps + 1,
                "content": content,
                "provider": result.get("provider"),
                "latency_ms": result.get("latency_ms"),
                "usage": result.get("usage")
            })

            final_answer = self._parse_final_answer(content)
            if final_answer:
                logger.log_event("AGENT_FINAL_ANSWER", {"final_answer": final_answer, "steps": steps + 1})
                break

            action = self._parse_action(content)
            if action is None:
                logger.log_event("AGENT_NO_ACTION", {"step": steps + 1, "content": content})
                final_answer = content
                break

            tool_output = self._execute_tool(action["tool_name"], action["args"])
            logger.log_event("TOOL_EXECUTION", {
                "tool_name": action["tool_name"],
                "args": action["args"],
                "output": tool_output
            })

            current_prompt = (
                f"{current_prompt}\n"
                f"Thought: {action.get('thought', '').strip()}\n"
                f"Action: {action['tool_name']}({action['args']})\n"
                f"Observation: {tool_output}"
            )

            steps += 1

        if final_answer is None:
            final_answer = "Agent stopped after reaching max steps without a final answer."
            logger.log_event("AGENT_MAX_STEPS", {"max_steps": self.max_steps})

        logger.log_event("AGENT_END", {"steps": steps, "final_answer": final_answer})
        return final_answer

    def _parse_action(self, text: str) -> Optional[Dict[str, str]]:
        """
        Parse the first Action from the model output.
        Expected format: Action: tool_name(arguments)
        """
        action_pattern = r"Action\s*:\s*([A-Za-z0-9_]+)\s*\((.*?)\)"
        match = re.search(action_pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None

        thought_match = re.search(r"Thought\s*:\s*(.*?)(?:\n|$)", text, re.IGNORECASE)
        thought = thought_match.group(1).strip() if thought_match else ""
        tool_name = match.group(1).strip()
        args = match.group(2).strip()

        return {
            "tool_name": tool_name,
            "args": args,
            "thought": thought
        }

    def _parse_final_answer(self, text: str) -> Optional[str]:
        """
        Parse the Final Answer from the model output.
        Expected format: Final Answer: your final response.
        """
        final_pattern = r"Final Answer\s*:\s*(.+)"
        match = re.search(final_pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        return match.group(1).strip()

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool["name"] == tool_name:
                tool_fn = tool.get("function") or tool.get("execute") or tool.get("implementation")
                if callable(tool_fn):
                    try:
                        return tool_fn(args)
                    except Exception as exc:
                        return f"Error executing {tool_name}: {exc}"
                return tool.get("output", f"Tool {tool_name} has no callable implementation.")
        return f"Tool {tool_name} not found."
