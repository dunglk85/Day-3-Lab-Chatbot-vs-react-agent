import os
import streamlit as st
from dotenv import load_dotenv

# Force .env values to override existing process/system environment variables.
load_dotenv(override=True)


def render_llm_error(error: Exception, provider: str) -> None:
    """Show user-friendly provider errors instead of raw tracebacks."""
    message = str(error)
    normalized = message.lower()

    if "reported as leaked" in normalized or "permissiondenied" in normalized:
        st.error(
            f"{provider} API key is blocked/leaked. Please generate a new key and update `.env`."
        )
    elif "resourceexhausted" in normalized or "quota exceeded" in normalized:
        st.error(
            f"{provider} quota is exceeded. Wait and retry, upgrade billing, or switch provider."
        )
    elif "notfound" in normalized or ("model" in normalized and "not found" in normalized):
        st.error(
            f"{provider} model is not available for this API key/version. Try another model name."
        )
    else:
        st.error(f"{provider} request failed: {message}")


st.set_page_config(page_title="Product Recommendation Demo V2", page_icon="🤖", layout="wide")
st.title("Product Recommendation Agent Demo V2")
st.write(
    "This demo uses the improved agent from `src/agent_v2.py`. "
    "Enter a shopping request, choose an LLM provider, and press `Recommend` to see the result."
)

provider_option = st.selectbox("Choose LLM provider", ["OpenAI", "Gemini", "Local"])
user_query = st.text_area(
    "User query",
    value="Tôi muốn mua điện thoại giá từ 5 triệu đến 10 triệu, cần camera tốt và pin lâu",
    height=140,
)

if provider_option == "Local":
    local_model_path = st.text_input(
        "LOCAL_MODEL_PATH",
        value=os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf"),
    )
    st.caption("Local model path for llama-cpp-python. Must exist on disk.")
elif provider_option == "Gemini":
    gemini_model = st.text_input(
        "Gemini model",
        value=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )
    st.caption("If you get 404 model not found, try another available Gemini model for your API key.")

run_button = st.button("Recommend with Agent V2")

if run_button:
    if not user_query.strip():
        st.warning("Please enter a user query first.")
    else:
        try:
            from src.agent_v2 import ProductRecommendationAgentV2
            from src.core.openai_provider import OpenAIProvider
            from src.core.gemini_provider import GeminiProvider
            from src.core.local_provider import LocalProvider
        except Exception as e:
            st.error(f"Import error: {e}")
            st.stop()

        llm = None
        if provider_option == "OpenAI":
            openai_api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
            if not openai_api_key:
                st.error("OPENAI_API_KEY is not set. Please define it in your environment or .env file.")
                st.stop()
            llm = OpenAIProvider(model_name="gpt-4o", api_key=openai_api_key)
        elif provider_option == "Gemini":
            gemini_api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
            if not gemini_api_key:
                st.error("GEMINI_API_KEY is not set. Please define it in your environment or .env file.")
                st.stop()
            llm = GeminiProvider(model_name=gemini_model, api_key=gemini_api_key)
        else:
            if not os.path.exists(local_model_path):
                st.error(f"Local model not found at: {local_model_path}")
                st.stop()
            llm = LocalProvider(model_path=local_model_path)

        agent = ProductRecommendationAgentV2(llm=llm)

        try:
            with st.spinner("Running recommendation workflow..."):
                response = agent.run(user_query)
        except Exception as e:
            render_llm_error(e, provider_option)
            st.stop()

        st.success("Recommendation completed with Agent V2")

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
