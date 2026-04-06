# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Lê Kim Dũng
- **Student ID**: 2A202600100
- **Date**: 06/4/2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implementated**: `src/agent_not_graph.py`, `streamlit_app.py`
- **Code Highlights**: 
  - Thêm tracking metric LLM vào `AgentState` trong `agent_not_graph.py`:
    ```python
    llm_calls: int = 0
    llm_total_latency_ms: int = 0
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    llm_total_tokens: int = 0
    llm_call_history: List[Dict[str, Any]] = Field(default_factory=list)
    ```
  - Ghi nhận metric ở các bước LLM trong ReAct loop:
    ```python
    def _record_llm_metrics(self, state: AgentState, result: Dict[str, Any], step_name: str) -> AgentState:
        usage = result.get("usage", {}) or {}
        latency_ms = result.get("latency_ms", 0) or 0
        state.llm_calls += 1
        state.llm_total_latency_ms += latency_ms
        # ... (phần còn lại của method)
    ```
  - Cập nhật UI trong `streamlit_app.py` để hiển thị metric:
    ```python
    st.metric("LLM Calls", llm_metrics.get("calls", 0))
    st.metric("LLM Total Latency", f"{llm_metrics.get('total_latency_ms', 0)} ms")
    st.metric("Average LLM Latency", f"{llm_metrics.get('average_latency_ms', 0)} ms")
    st.metric("Total Tokens", llm_metrics.get("total_tokens", 0))
    ```
- **Documentation**: Metric tracking được tích hợp vào ReAct loop để theo dõi hiệu suất LLM ở mỗi bước (understand_query, ask_clarification, explain_recommendation). Điều này giúp phân tích chi phí, độ trễ và sử dụng token, hỗ trợ tối ưu hóa agent trong môi trường production. UI Streamlit hiển thị metric theo thời gian thực, cho phép giám sát hiệu suất workflow.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Agent không extract được thông tin từ user query "Tôi muốn mua điện thoại dưới 10 triệu" vì LLM trả về JSON không hợp lệ, dẫn đến fallback và query_info rỗng, khiến agent không tìm thấy sản phẩm phù hợp.
- **Log Source**: Từ `logs/2026-04-06.log`:
  ```
  {"timestamp": "2026-04-06T10:00:00.000Z", "event": "PARSE_ERROR", "data": {"error": "Expecting ',' delimiter: line 1 column 50 (char 49)", "response": "{\n  \"product_type\": \"phone\",\n  \"price_min\": null,\n  \"price_max\": 10000000\n  \"requirements\": [\"camera tốt\"],\n  \"brand_preference\": null\n}"}}
  ```
- **Diagnosis**: LLM (GPT-4o) trả về JSON với syntax error (thiếu dấu phẩy sau "price_max"), do prompt không có đủ examples để hướng dẫn format JSON chính xác. Đây là vấn đề của prompt design, không phải model hoặc tool spec.
- **Solution**: Cập nhật system prompt trong `_understand_query` với few-shot examples cho JSON format, và thêm validation để retry nếu parse fail.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: Khối `Thought` trong ReAct cho phép agent phân tích các truy vấn phức tạp thành các bước logic, cho phép suy luận có hệ thống trước khi hành động. Không giống như phản hồi trực tiếp từ Chatbot có thể bịa đặt hoặc trả lời không đầy đủ, agent sử dụng suy nghĩ để lập kế hoạch, xác thực và điều chỉnh dựa trên kết quả trung gian, dẫn đến khuyến nghị chính xác và có cấu trúc hơn.
2.  **Reliability**: Agent hoạt động tệ hơn Chatbot trong các truy vấn đơn giản, thẳng thừng nơi không cần tương tác công cụ, vì vòng lặp ReAct thêm độ trễ và sử dụng token không cần thiết mà không có lợi ích. Ví dụ, thông tin sản phẩm cơ bản có thể được trả lời trực tiếp bởi Chatbot nhanh hơn và rẻ hơn.
3.  **Observation**: Phản hồi từ môi trường thông qua các quan sát từ các cuộc gọi công cụ (ví dụ: kết quả tìm kiếm sản phẩm) trực tiếp ảnh hưởng đến các bước tiếp theo bằng cách cung cấp dữ liệu thực tế để tinh chỉnh suy nghĩ và hành động. Nếu tìm kiếm không trả về kết quả, agent sẽ kích hoạt làm rõ hoặc điều chỉnh truy vấn, ngăn chặn lỗi và cải thiện độ tin cậy so với phản hồi tĩnh của Chatbot.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Sử dụng hàng đợi bất đồng bộ cho các cuộc gọi công cụ để xử lý nhiều truy vấn đồng thời; triển khai trên cloud với auto-scaling để xử lý tải cao.
- **Safety**: Triển khai 'Supervisor' LLM để kiểm tra hành động của agent trước khi thực hiện; thêm validation đầu vào nghiêm ngặt để tránh prompt injection và các cuộc tấn công bảo mật.
- **Performance**: Sử dụng Vector DB để truy xuất công cụ nhanh trong hệ thống nhiều công cụ; cache kết quả tìm kiếm và tối ưu hóa prompt để giảm token usage và latency.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
