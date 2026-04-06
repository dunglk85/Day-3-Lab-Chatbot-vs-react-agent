import os
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

__all__ = ["ReActAgent"]

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
        Generate system prompt that instructs the agent to follow ReAct with proper tool usage.
        """
        tool_descriptions = "\n".join([
            f"- {t['name']}: {t['description']}" for t in self.tools
        ])

        return f"""You are an intelligent assistant with access to the following tools:
{tool_descriptions}

Use the following format for your responses:
Thought: your reasoning about what to do next
Action: tool_name(argument)
Observation: result from the tool
... (repeat as needed)
Final Answer: your final response to the user

Guidelines for tool usage:
- Use simple argument format: tool_name("argument")
- For product queries: check_stock("iPhone 15")
- For price queries: get_product_price("iPhone 15") 
- For tax calculation: calculate_tax("999")
- For shipping: get_shipping_cost("Vietnam")
- For battery info: get_battery_life("iPhone 15")
- For comparisons: compare_products("iPhone 15 vs Samsung Galaxy S24")

Always use the exact tool names and provide arguments as quoted strings."""

    def run(self, user_input: str) -> Dict[str, Any]:
        """
        ReAct loop logic that returns detailed step information.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        
        Returns:
            Dict containing:
                - final_answer: str - the final response
                - steps: List[Dict] - each step with thought, action, observation
                - total_steps: int - number of steps taken
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        system_prompt = self.get_system_prompt()
        current_prompt = user_input.strip()
        step_count = 0
        final_answer = None
        step_details = []

        while step_count < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=system_prompt)
            content = result.get("content", "").strip()
            logger.log_event("LLM_RESPONSE", {
                "step": step_count + 1,
                "content": content,
                "provider": result.get("provider"),
                "latency_ms": result.get("latency_ms"),
                "usage": result.get("usage")
            })

            final_answer = self._parse_final_answer(content)
            if final_answer:
                logger.log_event("AGENT_FINAL_ANSWER", {"final_answer": final_answer, "steps": step_count + 1})
                break

            action = self._parse_action(content)
            if action is None:
                logger.log_event("AGENT_NO_ACTION", {"step": step_count + 1, "content": content})
                final_answer = content
                break

            tool_output = self._execute_tool(action["tool_name"], action["args"])
            logger.log_event("TOOL_EXECUTION", {
                "tool_name": action["tool_name"],
                "args": action["args"],
                "raw_args": action.get("raw_args", ""),
                "output": tool_output
            })

            # Store step details
            step_details.append({
                "step_number": step_count + 1,
                "thought": action.get("thought", "").strip(),
                "action": f"{action['tool_name']}({action.get('raw_args', str(action['args']))})",
                "tool_name": action["tool_name"],
                "args": action["args"],
                "observation": tool_output
            })

            current_prompt = (
                f"{current_prompt}\n"
                f"Thought: {action.get('thought', '').strip()}\n"
                f"Action: {action['tool_name']}({action.get('raw_args', str(action['args']))})\n"
                f"Observation: {tool_output}"
            )

            step_count += 1

        if final_answer is None:
            final_answer = "Agent stopped after reaching max steps without a final answer."
            logger.log_event("AGENT_MAX_STEPS", {"max_steps": self.max_steps})

        logger.log_event("AGENT_END", {"steps": step_count, "final_answer": final_answer})
        
        return {
            "final_answer": final_answer,
            "steps": step_details,
            "total_steps": step_count
        }

    def _parse_action(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse the first Action from the model output.
        Supports multiple formats:
        - Action: tool_name(arguments)
        - Action: tool_name("arg1", "arg2")
        - Action: tool_name(arg1="value1", arg2="value2")
        """
        # Pattern for function call format: tool_name(args)
        action_pattern = r"Action\s*:\s*([A-Za-z0-9_]+)\s*\((.*?)\)"
        match = re.search(action_pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None

        tool_name = match.group(1).strip()
        args_str = match.group(2).strip()

        # Extract thought
        thought_match = re.search(r"Thought\s*:\s*(.*?)(?:\n|$)", text, re.IGNORECASE)
        thought = thought_match.group(1).strip() if thought_match else ""

        # Parse arguments
        parsed_args = self._parse_arguments(args_str)

        return {
            "tool_name": tool_name,
            "args": parsed_args,
            "thought": thought,
            "raw_args": args_str
        }

    def _parse_arguments(self, args_str: str) -> Dict[str, Any]:
        """
        Parse arguments string into a dictionary.
        Supports:
        - Single argument: "iPhone 15"
        - Multiple positional: "iPhone 15", "Samsung"
        - Named arguments: product="iPhone 15", amount="999"
        """
        if not args_str:
            return {}

        try:
            # Check if it's named arguments (contains =)
            if '=' in args_str:
                # Named arguments: product="iPhone 15", amount="999"
                args_dict = {}
                # Split by comma but be careful with quoted strings
                parts = self._split_preserving_quotes(args_str, ',')

                for part in parts:
                    part = part.strip()
                    if '=' in part:
                        key, value = part.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        args_dict[key] = value
                return args_dict
            else:
                # Positional arguments: "iPhone 15", "999"
                parts = self._split_preserving_quotes(args_str, ',')
                if len(parts) == 1:
                    # Single argument
                    arg = parts[0].strip()
                    if (arg.startswith('"') and arg.endswith('"')) or \
                       (arg.startswith("'") and arg.endswith("'")):
                        arg = arg[1:-1]
                    return {"query": arg}  # Default key for single arg
                else:
                    # Multiple positional args
                    args_list = []
                    for part in parts:
                        part = part.strip()
                        if (part.startswith('"') and part.endswith('"')) or \
                           (part.startswith("'") and part.endswith("'")):
                            part = part[1:-1]
                        args_list.append(part)
                    return {"args": args_list}

        except Exception as e:
            logger.log_event("ARG_PARSE_ERROR", {"args_str": args_str, "error": str(e)})
            # Fallback: return raw string
            return {"raw": args_str}

    def _split_preserving_quotes(self, text: str, delimiter: str) -> List[str]:
        """
        Split string by delimiter while preserving quoted strings.
        """
        parts = []
        current = ""
        in_quotes = False
        quote_char = None

        i = 0
        while i < len(text):
            char = text[i]

            if not in_quotes and (char == '"' or char == "'"):
                in_quotes = True
                quote_char = char
                current += char
            elif in_quotes and char == quote_char:
                in_quotes = False
                quote_char = None
                current += char
            elif not in_quotes and char == delimiter:
                parts.append(current)
                current = ""
            else:
                current += char
            i += 1

        if current:
            parts.append(current)

        return parts

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

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Execute a tool by name with parsed arguments.
        """
        # Find the tool
        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return f"Tool '{tool_name}' not found. Available tools: {', '.join([t['name'] for t in self.tools])}"

        # Get the function
        tool_fn = tool.get("function") or tool.get("execute") or tool.get("implementation")
        if not callable(tool_fn):
            return f"Tool '{tool_name}' has no callable implementation."

        try:
            # Validate and prepare arguments
            prepared_args = self._prepare_tool_arguments(tool_name, args)

            # Execute the tool
            logger.log_event("TOOL_EXECUTION_START", {
                "tool_name": tool_name,
                "prepared_args": prepared_args
            })

            result = tool_fn(prepared_args)

            logger.log_event("TOOL_EXECUTION_SUCCESS", {
                "tool_name": tool_name,
                "result_length": len(str(result))
            })

            return str(result)

        except Exception as exc:
            error_msg = f"Error executing {tool_name}: {str(exc)}"
            logger.log_event("TOOL_EXECUTION_ERROR", {
                "tool_name": tool_name,
                "args": args,
                "error": str(exc)
            })
            return error_msg

    def _prepare_tool_arguments(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Prepare arguments for tool execution based on tool type.
        """
        if not args:
            return ""

        # For tools that expect a single string argument
        if tool_name in ["check_stock", "get_product_price", "get_battery_life"]:
            if "query" in args:
                return args["query"]
            elif "raw" in args:
                return args["raw"]
            elif isinstance(args, dict) and len(args) == 1:
                return str(list(args.values())[0])
            else:
                return str(args)

        # For calculate_tax - expects a number
        elif tool_name == "calculate_tax":
            if "query" in args:
                return args["query"]
            elif "amount" in args:
                return args["amount"]
            elif "raw" in args:
                return args["raw"]
            else:
                return str(args)

        # For get_shipping_cost - expects destination
        elif tool_name == "get_shipping_cost":
            if "query" in args:
                return args["query"]
            elif "destination" in args:
                return args["destination"]
            elif "raw" in args:
                return args["raw"]
            else:
                return str(args)

        # For compare_products - expects "product1 vs product2"
        elif tool_name == "compare_products":
            if "query" in args:
                return args["query"]
            elif "raw" in args:
                return args["raw"]
            elif "args" in args and isinstance(args["args"], list):
                return " vs ".join(args["args"])
            else:
                return str(args)

        # Default fallback
        else:
            if "query" in args:
                return args["query"]
            elif "raw" in args:
                return args["raw"]
            else:
                # Convert dict to string representation
                return str(args)
