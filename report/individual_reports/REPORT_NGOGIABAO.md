# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Ngo Giabao
- **Student ID**: 20A202600385
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

I implemented and integrated the LLM provider layer and Streamlit demo flow so the same recommendation agent can run with OpenAI, Gemini, and Local GGUF models.

Tôi đã triển khai và tích hợp lớp provider LLM cùng luồng demo Streamlit để cùng một agent gợi ý sản phẩm có thể chạy với OpenAI, Gemini và model local GGUF.

- **Modules Implemented**:  
  `streamlit_app.py`, `src/core/llm_provider.py`, `src/core/openai_provider.py`, `src/core/gemini_provider.py`, `src/core/local_provider.py`

- **Code Highlights**:  
  1) Defined a common abstract interface `LLMProvider` with `generate()` and `stream()` to standardize provider calls.  
  2) Implemented provider-specific wrappers:
     - `OpenAIProvider`: chat completion + usage/latency extraction.
     - `GeminiProvider`: `generate_content` integration + token usage metadata.
     - `LocalProvider`: `llama-cpp-python` GGUF inference with prompt template and stop tokens.  
  3) Built a Streamlit selector to switch provider dynamically, validate env/model path, and execute `ProductRecommendationAgent`.  
  4) Added user-friendly error rendering in `render_llm_error()` to handle key leak/permission denied, quota exhaustion, and model-not-found failures.

- **Documentation (ReAct interaction)**:  
  The provider layer is injected into `ProductRecommendationAgent(llm=...)` and reused across all ReAct-like workflow steps (`understand_query`, `ask_clarification`, `explain_recommendation`).  
  Lớp provider được truyền vào `ProductRecommendationAgent(llm=...)` và tái sử dụng ở các bước workflow kiểu ReAct (`understand_query`, `ask_clarification`, `explain_recommendation`), giúp tách biệt logic agent và backend model.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:  
  Gemini runs repeatedly failed or got stuck at early node execution due to unavailable/invalid model names (e.g., `gemini-2.-flash`, `gemini-2.0-flash`), causing repeated `AGENT_START` without full completion in multiple attempts.

- **Log Source**:  
  `logs/2026-04-06.log` shows many retries with Gemini model variants, while stable runs completed with `gpt-4o` and `gemini-1.5-flash`.  
  Example events:
  - `AGENT_START` with `"model": "gemini-2.-flash"` (invalid name pattern).
  - Repeated `AGENT_START` + `NODE_UNDERSTAND_QUERY` without corresponding `AGENT_END` in some retries.
  - Successful completion later with `gemini-1.5-flash` / `gpt-4o` including `NODE_RETURN_RESULT` and `AGENT_END`.

- **Diagnosis**:  
  Root cause was model compatibility/availability mismatch for the active API key/version, not the business logic of the agent itself.  
  Nguyên nhân chính là mismatch về model khả dụng theo API key/version (và lỗi gõ sai model), không phải lỗi cốt lõi của luồng recommend.

- **Solution**:  
  1) Added configurable Gemini model input in `streamlit_app.py` (instead of hard-coded only).  
  2) Added explicit error guidance for model-not-found/quota/key issues via `render_llm_error()`.  
  3) Retested with known valid model names (`gemini-1.5-flash`, later `gemini-2.5-flash` where available).  
  Kết quả: giảm thời gian debug do người dùng nhận thông báo rõ nguyên nhân và hướng xử lý ngay trên UI.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**  
   ReAct-style step decomposition improved traceability because each stage (parse query -> check missing info -> search -> rank -> explain) can be inspected in `history` and logs.  
   So với chatbot trả lời trực tiếp một lần, cách này giúp thấy rõ agent đang "nghĩ gì/làm gì", dễ kiểm thử và sửa lỗi hơn.

2. **Reliability**  
   Agent can perform worse than a direct chatbot when upstream tools/models fail (invalid model, quota exhaustion, local model path missing) because the pipeline has more failure points.  
   Trong khi đó chatbot baseline có thể vẫn trả lời được nếu chỉ cần text generation đơn giản.

3. **Observation**  
   Environment feedback from telemetry events (`NODE_CHECK_INFO`, `NODE_ASK_CLARIFICATION`, `NODE_FILTER_RANK`) directly guides next actions and loop behavior.  
   Ví dụ, khi thiếu `price range`, agent chuyển sang nhánh hỏi làm rõ trước khi tiếp tục tìm kiếm sản phẩm.

---

## IV. Future Improvements (5 Points)

- **Scalability**:  
  Move provider calls to async execution and add request queue/caching so multiple users can run recommendation workflows concurrently.

- **Safety**:  
  Add output guardrails (policy checks + PII redaction) and a supervisor validation step before returning recommendations.

- **Performance**:  
  Introduce retrieval index/vector search for larger product catalogs, plus prompt/result caching and fallback routing across providers.

---

