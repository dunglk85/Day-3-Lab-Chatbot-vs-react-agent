import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Product Recommendation Demo", page_icon="🤖", layout="wide")
st.title("Product Recommendation Agent Demo")
st.write(
    "This demo uses the non-graph product recommendation agent from `src/agent_not_graph.py`. "
    "Enter a shopping request, choose an LLM provider, and press `Recommend` to see the results."
)

provider_option = st.selectbox("Choose LLM provider", ["OpenAI", "Local"])
user_query = st.text_area(
    "User query",
    value="Tôi muốn mua điện thoại giá từ 5 triệu đến 10 triệu, cần camera tốt và pin lâu",
    height=140,
)

if provider_option == "Local":
    local_model_path = st.text_input("LOCAL_MODEL_PATH", value=os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf"))
    st.caption("Local model path for llama-cpp-python. Must exist on disk.")

run_button = st.button("Recommend")

if run_button:
    if not user_query.strip():
        st.warning("Please enter a user query first.")
    else:
        try:
            from src.agent_not_graph import ProductRecommendationAgent
            from src.core.llm_provider import LLMProvider
            from src.core.openai_provider import OpenAIProvider
            from src.core.local_provider import LocalProvider
        except Exception as e:
            st.error(f"Import error: {e}")
            st.stop()

        llm = None
        if provider_option == "OpenAI":
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                st.error("OPENAI_API_KEY is not set. Please define it in your environment or .env file.")
                st.stop()
            llm = OpenAIProvider(model_name="gpt-4o", api_key=openai_api_key)
        else:
            if not os.path.exists(local_model_path):
                st.error(f"Local model not found at: {local_model_path}")
                st.stop()
            llm = LocalProvider(model_path=local_model_path)

        agent = ProductRecommendationAgent(llm=llm)

        with st.spinner("Running recommendation workflow..."):
            response = agent.run(user_query)

        st.success("Recommendation completed")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Final Answer")
            st.text_area("Result", value=response.get("final_answer", ""), height=320)

        with col2:
            st.subheader("Summary")
            st.metric("Steps", response.get("steps", 0))
            st.metric("Recommendations", len(response.get("recommendations", [])))
            st.markdown("**Provider**: {}".format(provider_option))

        if response.get("recommendations"):
            st.subheader("Recommendations")
            st.write(response["recommendations"])

        st.subheader("Workflow History")
        st.json(response.get("history", []))
