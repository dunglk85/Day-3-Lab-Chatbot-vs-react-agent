import sys
import os
# Go up 3 levels: chatbot.py -> chatbot/ -> src/ -> repo_root/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from src.core.openai_provider import OpenAIProvider
from src.telemetry.logger import logger

load_dotenv()

class SimpleChatbot:
    """Baseline chatbot without tools - directly asks LLM"""
    
    SYSTEM_PROMPT = """You are a helpful Phone Consultant AI.
Answer user questions directly based on your knowledge.
Be concise and helpful.
Do NOT use tools or mention tool calls."""

    def __init__(self, llm):
        self.llm = llm
    
    def chat(self, user_input: str) -> str:
        """Generate response using only LLM, no tools"""
        result = self.llm.generate(
            user_input,
            system_prompt=self.SYSTEM_PROMPT
        )
        return result.get("content", "No response")

# Test cases: 5 use cases
test_cases = [
    {
        "id": 1,
        "query": "What is the capital of France?",
        "type": "simple_qa",
        "expected": "chatbot_should_work"
    },
    {
        "id": 2,
        "query": "What is the price of iPhone 15?",
        "type": "single_tool",
        "expected": "chatbot_may_hallucinate"
    },
    {
        "id": 3,
        "query": "Check if iPhone 15 is in stock and calculate 10% tax on $999",
        "type": "multi_step",
        "expected": "chatbot_will_fail"
    },
    {
        "id": 4,
        "query": "What is the phone with best battery on Mars?",
        "type": "error_handling",
        "expected": "chatbot_will_hallucinate"
    },
    {
        "id": 5,
        "query": "Compare Samsung Galaxy S24 and iPhone 15, then calculate total shipping cost if I buy both",
        "type": "complex",
        "expected": "chatbot_will_hallucinate"
    },
]

def run_chatbot_evaluation():
    """Run chatbot on all 5 test cases"""
    llm = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
    chatbot = SimpleChatbot(llm)
    
    print("\n" + "="*80)
    print("CHATBOT BASELINE EVALUATION")
    print("="*80)
    
    results = []
    for test in test_cases:
        print(f"\n[Case {test['id']}] {test['type'].upper()}")
        print(f"Query: {test['query']}")
        
        chatbot_result = chatbot.chat(test["query"])
        
        # Log result
        logger.log_event("CHATBOT_EVALUATION", {
            "case_id": test["id"],
            "query": test["query"],
            "type": test["type"],
            "result": chatbot_result[:300],
            "expected": test["expected"]
        })
        
        print(f"Response: {chatbot_result[:300]}...")
        
        results.append({
            "id": test["id"],
            "query": test["query"],
            "result": chatbot_result
        })
    
    print("\n" + "="*80)
    return results

if __name__ == "__main__":
    run_chatbot_evaluation()