"""
Simple Streamlit UI for Chatbot vs ReAct Agent Comparison
Allows users to see responses side-by-side
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv
import time

from src.core.openai_provider import OpenAIProvider
from src.agent.agent import ReActAgent
from src.chatbot.chatbot import SimpleChatbot
from src.tools.tools import TOOLS
from src.telemetry.logger import logger

load_dotenv()

# Page config
st.set_page_config(
    page_title="Chatbot vs ReAct Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .chatbot-header { color: #FF6B6B; font-weight: bold; }
    .agent-header { color: #4ECDC4; font-weight: bold; }
    .success { color: #95E1D3; }
    .error { color: #FF6B6B; }
    .divider { margin: 20px 0; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "llm" not in st.session_state:
    st.session_state.llm = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))

if "chatbot" not in st.session_state:
    st.session_state.chatbot = SimpleChatbot(st.session_state.llm)

if "agent" not in st.session_state:
    st.session_state.agent = ReActAgent(st.session_state.llm, tools=TOOLS, max_steps=5)

if "history" not in st.session_state:
    st.session_state.history = []

# ============================================================
# MAIN APP
# ============================================================

st.title("🤖 Chatbot vs 🦾 ReAct Agent Comparison")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    max_steps = st.slider("Agent Max Steps", 1, 10, 5)
    st.session_state.agent.max_steps = max_steps
    
    st.markdown("---")
    st.header("📚 Available Tools")
    for tool in TOOLS:
        with st.expander(f"🔧 {tool['name']}"):
            st.write(f"**Description:** {tool['description']}")
    
    st.markdown("---")
    st.header("📝 Test Cases")
    test_cases = {
        "1️⃣ What is the capital of France?": "What is the capital of France?",
        "2️⃣ iPhone 15 price": "What is the price of iPhone 15?",
        "3️⃣ Stock & Tax": "Check if iPhone 15 is in stock and calculate 10% tax on $999",
        "4️⃣ Mars phone": "What is the phone with best battery on Mars?",
        "5️⃣ Complex query": "Compare Samsung Galaxy S24 and iPhone 15, then calculate total shipping cost if I buy both",
    }
    
    selected_test = st.selectbox("Quick test:", list(test_cases.keys()))
    if st.button("Load test case"):
        st.session_state.input_query = test_cases[selected_test]

# Main content area
col1, col2 = st.columns(2, gap="large")

# ============================================================
# USER INPUT
# ============================================================
st.header("❓ Your Query")

user_input = st.text_area(
    "Enter your question:",
    value=st.session_state.get("input_query", ""),
    height=100,
    placeholder="Type something like: 'Check iPhone 15 stock and calculate tax for $999'",
    key="input_query"
)

# Run button
col_button1, col_button2, col_button3 = st.columns([2, 1, 1])

with col_button1:
    run_comparison = st.button("🚀 Compare Chatbot vs Agent", use_container_width=True)

with col_button2:
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.history = []
        st.rerun()

with col_button3:
    if st.button("📊 History", use_container_width=True):
        st.session_state.show_history = not st.session_state.get("show_history", False)

# ============================================================
# COMPARISON RESULTS
# ============================================================

if run_comparison and user_input.strip():
    st.markdown("---")
    st.header("📊 Results")
    
    # Create a progress placeholder
    progress_placeholder = st.empty()
    
    with col1:
        st.markdown("### 🤖 SimpleChatbot (No Tools)")
        st.markdown("*(Direct LLM response)*")
        
        with st.spinner("⏳ Chatbot is thinking..."):
            start_time = time.time()
            chatbot_result = st.session_state.chatbot.chat(user_input)
            chatbot_time = time.time() - start_time
        
        # Display result
        st.markdown(f"<div class='success'>✅ Response ({chatbot_time:.2f}s)</div>", unsafe_allow_html=True)
        st.info(chatbot_result)
        
        # Metrics
        st.metric("Response Time", f"{chatbot_time:.2f}s")
    
    with col2:
        st.markdown("### 🦾 ReAct Agent (With Tools)")
        st.markdown("*(Multi-step reasoning with tools)*")
        
        with st.spinner("⏳ Agent is reasoning..."):
            start_time = time.time()
            try:
                agent_result = st.session_state.agent.run(user_input)
                agent_time = time.time() - start_time
                agent_success = True
            except Exception as e:
                agent_result = f"❌ Error: {str(e)}"
                agent_time = time.time() - start_time
                agent_success = False
        
        # Display result
        status_text = "✅ Response" if agent_success else "❌ Error"
        st.markdown(f"<div class='success'>{status_text} ({agent_time:.2f}s)</div>", unsafe_allow_html=True)
        st.info(agent_result)
        
        # Metrics
        max_steps_used = min(st.session_state.agent.max_steps, 5)  # Display actual steps used
        st.metric("Response Time", f"{agent_time:.2f}s")
        st.metric("Max Steps", max_steps_used)
    
    # ============================================================
    # WINNER ANNOUNCEMENT
    # ============================================================
    st.markdown("---")
    
    col_winner1, col_winner2, col_winner3 = st.columns(3)
    
    with col_winner2:
        if agent_success and not chatbot_result.startswith("I'm unable"):
            st.success("🏆 Agent wins with practical tool usage!")
        elif not agent_success and chatbot_result:
            st.info("Chatbot provided a response, Agent encountered issues.")
        else:
            st.warning("Both systems had issues or both succeeded.")
    
    # Store in history
    st.session_state.history.append({
        "query": user_input,
        "chatbot_result": chatbot_result[:100],
        "agent_result": agent_result[:100],
        "chatbot_time": chatbot_time,
        "agent_time": agent_time,
        "timestamp": time.time()
    })
    
    # Log to telemetry
    logger.log_event("UI_COMPARISON", {
        "query": user_input,
        "chatbot_response_length": len(chatbot_result),
        "agent_response_length": len(agent_result),
        "chatbot_time": chatbot_time,
        "agent_time": agent_time
    })

# ============================================================
# HISTORY
# ============================================================

if st.session_state.get("show_history", False) and st.session_state.history:
    st.markdown("---")
    st.header("📋 Conversation History")
    
    for i, entry in enumerate(st.session_state.history[-5:], 1):  # Show last 5
        with st.expander(f"Query {i}: {entry['query'][:50]}..."):
            col_h1, col_h2 = st.columns(2)
            
            with col_h1:
                st.write("**Chatbot:**")
                st.caption(f"⏱️ {entry['chatbot_time']:.2f}s")
                st.write(entry['chatbot_result'])
            
            with col_h2:
                st.write("**Agent:**")
                st.caption(f"⏱️ {entry['agent_time']:.2f}s")
                st.write(entry['agent_result'])

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 12px;'>
    <p>🚀 Lab 3: From Simple Chatbot to Agentic ReAct Loop</p>
    <p>Built with Streamlit | LLM: OpenAI | Tools: Phone Consultant</p>
</div>
""", unsafe_allow_html=True)
