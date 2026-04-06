"""
Simple Streamlit UI for Chatbot ONLY
Clean version before adding ReAct Agent
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv
import time

from src.core.openai_provider import OpenAIProvider
from src.chatbot.chatbot import SimpleChatbot

load_dotenv()

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Simple Chatbot",
    page_icon="🤖",
    layout="centered"
)

# ============================================================
# INIT SESSION
# ============================================================
if "llm" not in st.session_state:
    st.session_state.llm = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))

if "chatbot" not in st.session_state:
    st.session_state.chatbot = SimpleChatbot(st.session_state.llm)

if "messages" not in st.session_state:
    st.session_state.messages = []

# ============================================================
# UI HEADER
# ============================================================
st.title("🤖 Simple Chatbot")
st.caption("Basic LLM chatbot (no tools, no reasoning)")

# ============================================================
# CHAT DISPLAY
# ============================================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ============================================================
# INPUT
# ============================================================
user_input = st.chat_input("Type your message...")

if user_input:
    # Save user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            start = time.time()
            response = st.session_state.chatbot.chat(user_input)
            duration = time.time() - start

        st.markdown(response)
        st.caption(f"⏱️ {duration:.2f}s")

    # Save bot response
    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.header("⚙️ Controls")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 📌 About")
    st.write("""
    - Model: OpenAI
    - Mode: Simple Chatbot
    - No tools / No reasoning
    """)

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption("🚀 Step 1: Build Chatbot → Next: Add ReAct Agent")