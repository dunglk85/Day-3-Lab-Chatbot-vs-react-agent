import os
from src.core.openai_provider import OpenAIProvider
from src.core.local_provider import LocalProvider

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = "gpt-4o"  # hoặc model khác bạn muốn thử
    llm = OpenAIProvider(model_name=model_name, api_key=api_key)

    system_prompt = "Tôi cần mua một chiếc điện thoại mới. Hãy giúp tôi chọn một chiếc phù hợp với nhu cầu của tôi. Tôi thích chụp ảnh và chơi game, nhưng ngân sách của tôi chỉ khoảng 10 triệu đồng.  Bạn có thể đề xuất một số lựa chọn và giải thích tại sao chúng phù hợp với tôi không?"
    user_input = "Tính tổng giá tiền của 2 sản phẩm 120k và 80k, sau đó cho biết thuế 10% là bao nhiêu."

    response = llm.generate(user_input, system_prompt=system_prompt)
    print("Chatbot baseline response:")
    print(response["content"])
    print("Usage:", response["usage"])
    print("Latency:", response["latency_ms"], "ms")

if __name__ == "__main__":
    main()