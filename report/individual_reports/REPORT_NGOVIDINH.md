# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Ngo Vi Dinh
- **Student ID**: 20A202600130
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

I implemented and integrated the LLM provider layer and a Streamlit demo flow so the same recommendation agent runs using OpenAI API. The updated v2 demo uses `src/agent_v2.py` and `streamlit_app_v2.py` for a cleaner workflow and improved ranking.

Tôi đã triển khai và tích hợp lớp provider LLM cùng luồng demo Streamlit để agent gợi ý sản phẩm chạy với OpenAI API. Phiên bản cập nhật v2 sử dụng `src/agent_v2.py` và `streamlit_app_v2.py` với workflow rõ ràng và xếp hạng tốt hơn.

- **Modules Implemented**:  
  `streamlit_app_v2.py`, `src/agent_v2.py`, `src/core/llm_provider.py`, `src/core/openai_provider.py`

- **Code Highlights**:  
  1) Defined a common abstract interface `LLMProvider` with `generate()` and `stream()` to standardize LLM calls.  
  2) Implemented provider-specific wrapper:
     - `OpenAIProvider`: chat completion + usage/latency extraction.  
  3) Integrated provider into Streamlit UI:
     - Load API key from `.env`  
     - Validate API key before running  
     - Execute `ProductRecommendationAgentV2` in the v2 demo flow  
  4) Added user-friendly error handling in `render_llm_error()`:
     - Invalid API key (401)  
     - Quota exceeded  
     - Model not found  

- **Documentation (ReAct interaction)**:  
  The provider layer is injected into `ProductRecommendationAgentV2(llm=...)` and reused across all workflow steps (`understand_query`, `ask_clarification`, `explain_recommendation`).  
  Lớp provider được truyền vào `ProductRecommendationAgentV2(llm=...)` và tái sử dụng ở các bước workflow kiểu ReAct, giúp tách biệt logic agent và backend model.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:  
  The system failed to call OpenAI API due to an invalid API key, returning error 401 (`invalid_api_key`), causing the agent to stop at early execution stages.

- **Log Source**:  
  Error message observed during execution: OpenAI request failed: Error code: 401 - invalid_api_key
The agent could not proceed beyond the initial LLM call (`AGENT_START` → fail before completing nodes).

- **Diagnosis**:  
Root cause was an incorrect or expired OpenAI API key (e.g., wrong key format or missing `.env` configuration), not an issue with agent logic.  
Nguyên nhân chính là API key không hợp lệ hoặc cấu hình sai, không phải lỗi của thuật toán ReAct.

- **Solution**:  
1) Verified API key format (`sk-...`) and replaced with a valid key from OpenAI dashboard.  
2) Ensured `.env` file is correctly loaded using `load_dotenv()`.  
3) Added error handling in `OpenAIProvider` to surface clear messages when 401 occurs.  

Kết quả: hệ thống hoạt động ổn định, agent chạy đầy đủ các bước và trả kết quả bình thường.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**  
 ReAct-style step decomposition improved traceability because each stage (parse query -> check missing info -> search -> rank -> explain) can be inspected via logs/history.  
 So với chatbot trả lời một lần, cách này giúp debug dễ hơn vì thấy rõ từng bước agent thực hiện.

2. **Reliability**  
 ReAct agent dễ bị fail hơn khi phụ thuộc vào LLM call (API key, quota, network).  
 Chatbot đơn giản có thể vẫn trả lời được trong một số trường hợp vì ít bước hơn.

3. **Observation**  
 Telemetry events (`NODE_CHECK_INFO`, `NODE_ASK_CLARIFICATION`, `NODE_FILTER_RANK`) giúp điều hướng flow rõ ràng.  
 Ví dụ: nếu thiếu thông tin (như price range), agent sẽ hỏi lại thay vì trả kết quả sai.

---

## IV. Future Improvements (5 Points)

- **Scalability**:  
Convert LLM calls to async and add caching/queue system to support multiple concurrent users.

- **Safety**:  
Add output validation layer (guardrails + PII filtering) before returning results.

- **Performance**:  
Introduce retrieval (vector search) for large product datasets and caching to reduce API cost and latency.

---