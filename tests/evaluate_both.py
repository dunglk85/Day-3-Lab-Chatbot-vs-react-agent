import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import json
from src.core.openai_provider import OpenAIProvider
from src.agent.agent import ReActAgent
from src.chatbot.chatbot import SimpleChatbot
from src.tools.tools import TOOLS
from src.telemetry.logger import logger

load_dotenv()

# Test cases: 5 use cases matching chatbot.py
test_cases = [
    {
        "id": 1,
        "query": "What is the capital of France?",
        "type": "simple_qa",
        "expected_chatbot": "success",
        "expected_agent": "success"
    },
    {
        "id": 2,
        "query": "What is the price of iPhone 15?",
        "type": "single_tool",
        "expected_chatbot": "partial",
        "expected_agent": "success"
    },
    {
        "id": 3,
        "query": "Check if iPhone 15 is in stock and calculate 10% tax on $999",
        "type": "multi_step",
        "expected_chatbot": "fail",
        "expected_agent": "success"
    },
    {
        "id": 4,
        "query": "What is the phone with best battery on Mars?",
        "type": "error_handling",
        "expected_chatbot": "hallucinate",
        "expected_agent": "success"
    },
    {
        "id": 5,
        "query": "Compare Samsung Galaxy S24 and iPhone 15, then calculate total shipping cost if I buy both",
        "type": "complex",
        "expected_chatbot": "fail",
        "expected_agent": "success"
    },
]

def is_valid_response(text: str, required_keywords: list = None) -> bool:
    """Check if response is valid (not empty, not error)"""
    if not text or len(text.strip()) == 0:
        return False
    if "error" in text.lower() or "i'm unable" in text.lower():
        return False
    if required_keywords:
        return any(kw.lower() in text.lower() for kw in required_keywords)
    return True

def run_evaluation():
    """Run comprehensive evaluation comparing Chatbot vs Agent"""
    
    llm = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
    chatbot = SimpleChatbot(llm)
    agent = ReActAgent(llm, tools=TOOLS, max_steps=5)
    
    print("\n" + "="*100)
    print("CHATBOT vs REACT AGENT EVALUATION")
    print("="*100)
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"Tools Available: {len(TOOLS)}")
    print("="*100)
    
    results = []
    
    for test in test_cases:
        print(f"\n[Case {test['id']}] {test['type'].upper()}")
        print(f"Query: {test['query']}")
        print("-" * 100)
        
        # Run Chatbot
        print("🤖 Running Chatbot (baseline, no tools)...")
        chatbot_result = chatbot.chat(test["query"])
        chatbot_success = is_valid_response(chatbot_result)
        
        # Run Agent
        print("🦾 Running ReAct Agent (with tools)...")
        try:
            agent_result = agent.run(test["query"])
            agent_success = is_valid_response(agent_result)
        except Exception as e:
            agent_result = f"Agent Error: {str(e)}"
            agent_success = False
        
        # Determine winner
        if chatbot_success and agent_success:
            winner = "Draw"
        elif agent_success and not chatbot_success:
            winner = "Agent ⭐"
        elif chatbot_success and not agent_success:
            winner = "Chatbot"
        else:
            winner = "Both Failed"
        
        # Store result
        result_dict = {
            "case_id": test["id"],
            "type": test["type"],
            "query": test["query"],
            "chatbot_result": chatbot_result[:80],
            "agent_result": agent_result[:80],
            "chatbot_success": chatbot_success,
            "agent_success": agent_success,
            "winner": winner
        }
        results.append(result_dict)
        
        # Log to telemetry
        logger.log_event("CASE_EVALUATION", result_dict)
        
        # Print result
        print(f"✓ Chatbot: {'✅' if chatbot_success else '❌'}")
        print(f"  Response: {chatbot_result[:80]}...")
        print(f"✓ Agent:   {'✅' if agent_success else '❌'}")
        print(f"  Response: {agent_result[:80]}...")
        print(f"🏆 Winner: {winner}")
    
    # Summary table
    print("\n" + "="*100)
    print("SUMMARY TABLE")
    print("="*100)
    print(f"{'Case':<6} {'Type':<15} {'Chatbot':<10} {'Agent':<10} {'Winner':<15}")
    print("-"*100)
    
    chatbot_wins = 0
    agent_wins = 0
    draws = 0
    
    for result in results:
        chatbot_status = "✅ Pass" if result["chatbot_success"] else "❌ Fail"
        agent_status = "✅ Pass" if result["agent_success"] else "❌ Fail"
        winner = result["winner"]
        
        if "Agent" in winner:
            agent_wins += 1
        elif "Chatbot" in winner:
            chatbot_wins += 1
        else:
            draws += 1
        
        print(f"{result['case_id']:<6} {result['type']:<15} {chatbot_status:<10} {agent_status:<10} {winner:<15}")
    
    print("-"*100)
    print(f"FINAL SCORE: Agent {agent_wins} - Chatbot {chatbot_wins} - Draws {draws}")
    print("="*100)
    
    # Export results for GROUP_REPORT
    with open("logs/evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Evaluation complete! Results saved to logs/evaluation_results.json")
    
    return results

if __name__ == "__main__":
    run_evaluation()
