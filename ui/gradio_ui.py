"""
Simple Gradio UI for Chatbot vs ReAct Agent Comparison
Lightweight alternative to Streamlit
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr
from dotenv import load_dotenv
import time

from src.core.openai_provider import OpenAIProvider
from src.agent.agent import ReActAgent
from src.chatbot.chatbot import SimpleChatbot
from src.tools.tools import TOOLS
from src.telemetry.logger import logger

load_dotenv()

# Initialize
llm = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
chatbot = SimpleChatbot(llm)
agent = ReActAgent(llm, tools=TOOLS, max_steps=5)

# Custom CSS
custom_css = """
.chatbot-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.agent-box { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
"""

def run_chatbot(query: str) -> str:
    """Run chatbot baseline"""
    if not query.strip():
        return "Please enter a query"
    
    try:
        start = time.time()
        result = chatbot.chat(query)
        elapsed = time.time() - start
        return f"⏱️ {elapsed:.2f}s\n\n{result}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def run_agent(query: str) -> str:
    """Run ReAct agent"""
    if not query.strip():
        return "Please enter a query"
    
    try:
        start = time.time()
        result = agent.run(query)
        elapsed = time.time() - start
        return f"⏱️ {elapsed:.2f}s\n\n{result}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def compare_both(query: str) -> tuple:
    """Run both chatbot and agent side-by-side"""
    if not query.strip():
        return "Please enter a query", "Please enter a query"
    
    chatbot_response = run_chatbot(query)
    agent_response = run_agent(query)
    
    # Log comparison
    logger.log_event("GRADIO_COMPARISON", {
        "query": query,
        "chatbot_length": len(chatbot_response),
        "agent_length": len(agent_response)
    })
    
    return chatbot_response, agent_response

# ============================================================
# GRADIO INTERFACE
# ============================================================

with gr.Blocks(title="Chatbot vs ReAct Agent") as demo:
    
    gr.Markdown("# 🤖 Chatbot vs 🦾 ReAct Agent")
    gr.Markdown("Compare simple chatbot (no tools) vs ReAct agent (with tools)")
    
    # ============================================================
    # INPUT SECTION
    # ============================================================
    gr.Markdown("## 📝 Input")
    with gr.Group():
        query_input = gr.Textbox(
            label="Your Question",
            placeholder="E.g., 'Check iPhone 15 stock and calculate 10% tax on $999'",
            lines=3
        )
        
        with gr.Row():
            submit_btn = gr.Button("🚀 Compare Both", variant="primary", scale=3)
            chatbot_only_btn = gr.Button("🤖 Chatbot Only", scale=1)
            agent_only_btn = gr.Button("🦾 Agent Only", scale=1)
    
    # ============================================================
    # SAMPLE QUERIES
    # ============================================================
    gr.Markdown("## 📚 Sample Queries")
    
    examples = [
        "What is the capital of France?",
        "What is the price of iPhone 15?",
        "Check if iPhone 15 is in stock and calculate 10% tax on $999",
        "What is the phone with best battery on Mars?",
        "Compare Samsung Galaxy S24 and iPhone 15, then calculate total shipping cost if I buy both",
    ]
    
    gr.Examples(
        examples=[[ex] for ex in examples],
        inputs=[query_input],
        label="Click to load example"
    )
    
    # ============================================================
    # OUTPUT SECTION
    # ============================================================
    gr.Markdown("## 📊 Results")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 SimpleChatbot")
            gr.Markdown("*(Direct LLM, no tools)*")
            chatbot_output = gr.Textbox(
                label="Response",
                lines=10,
                interactive=False
            )
        
        with gr.Column(scale=1):
            gr.Markdown("### 🦾 ReAct Agent")
            gr.Markdown("*(Multi-step reasoning with tools)*")
            agent_output = gr.Textbox(
                label="Response",
                lines=10,
                interactive=False
            )
    
    # ============================================================
    # AVAILABLE TOOLS
    # ============================================================
    gr.Markdown("## 🔧 Available Tools")
    
    tool_info = "### Tools the Agent can use:\n\n"
    for i, tool in enumerate(TOOLS, 1):
        tool_info += f"**{i}. {tool['name']}**: {tool['description']}\n\n"
    
    gr.Markdown(tool_info)
    
    # ============================================================
    # EVENT HANDLERS
    # ============================================================
    submit_btn.click(
        fn=compare_both,
        inputs=[query_input],
        outputs=[chatbot_output, agent_output]
    )
    
    chatbot_only_btn.click(
        fn=run_chatbot,
        inputs=[query_input],
        outputs=[chatbot_output]
    )
    
    agent_only_btn.click(
        fn=run_agent,
        inputs=[query_input],
        outputs=[agent_output]
    )
    
    # ============================================================
    # FOOTER
    # ============================================================
    gr.Markdown("---")
    gr.Markdown("""
    <div style='text-align: center; color: #888;'>
        <p>🚀 Lab 3: From Simple Chatbot to Agentic ReAct Loop</p>
        <p>Built with Gradio | LLM: OpenAI | Tools: Phone Consultant</p>
    </div>
    """)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
