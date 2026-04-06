from typing import Dict


def ask_chatbot(prompt: str) -> str:
    """
    Baseline chatbot: one-shot response without tool calling.
    """
    lower_prompt = prompt.lower()
    if "capital of france" in lower_prompt:
        return "The capital of France is Paris."
    if "find stock of iphone" in lower_prompt and "tax" in lower_prompt:
        return (
            "I cannot verify stock or calculate exact tax total because I do not call tools "
            "in baseline mode."
        )
    return "I am a baseline chatbot for simple Q&A."


def run_chatbot_case(prompt: str) -> Dict[str, str]:
    return {"prompt": prompt, "answer": ask_chatbot(prompt)}
