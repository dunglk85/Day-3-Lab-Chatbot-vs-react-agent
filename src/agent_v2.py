import os
import sys
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Ensure package imports work whether running from project root or inside src/
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


# ============================================================================
# Data Models
# ============================================================================

class QueryInfo(BaseModel):
    """Extracted information from user query."""
    product_type: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    requirements: List[str] = Field(default_factory=list)
    brand_preference: Optional[str] = None
    missing_info: List[str] = Field(default_factory=list)


class Product(BaseModel):
    """Product metadata used for recommendations."""
    id: str
    name: str
    brand: str
    price: float
    specs: Dict[str, Any] = Field(default_factory=dict)
    rating: float = 0.0
    score: float = 0.0


class AgentState(BaseModel):
    """Agent workflow state."""
    user_input: str
    query_info: Optional[QueryInfo] = None
    products: List[Product] = Field(default_factory=list)
    filtered_products: List[Product] = Field(default_factory=list)
    recommendations: List[Product] = Field(default_factory=list)
    explanation: str = ""
    history: List[Dict[str, Any]] = Field(default_factory=list)
    step_count: int = 0
    needs_clarification: bool = False
    final_answer: str = ""
    clarification_loops: int = 0


# ============================================================================
# Product Database (Mock)
# ============================================================================

PRODUCT_DATABASE = {
    "phone": [
        {
            "id": "phone_001",
            "name": "iPhone 15 Pro",
            "brand": "Apple",
            "price": 25_000_000,
            "specs": {"screen": "6.1 inch", "chip": "A18 Pro", "camera": "48MP"},
            "rating": 4.8
        },
        {
            "id": "phone_002",
            "name": "Samsung Galaxy S24 Ultra",
            "brand": "Samsung",
            "price": 24_000_000,
            "specs": {"screen": "6.8 inch", "chip": "Snapdragon 8 Gen 3", "camera": "200MP"},
            "rating": 4.7
        },
        {
            "id": "phone_003",
            "name": "Xiaomi 14 Ultra",
            "brand": "Xiaomi",
            "price": 16_000_000,
            "specs": {"screen": "6.73 inch", "chip": "Snapdragon 8 Gen 3", "camera": "50MP"},
            "rating": 4.6
        },
        {
            "id": "phone_004",
            "name": "Oppo Reno 11 Pro",
            "brand": "Oppo",
            "price": 13_000_000,
            "specs": {"screen": "6.7 inch", "chip": "Snapdragon 8 Gen 2", "camera": "50MP"},
            "rating": 4.5
        },
        {
            "id": "phone_005",
            "name": "Vivo X90 Pro",
            "brand": "Vivo",
            "price": 12_000_000,
            "specs": {"screen": "6.78 inch", "chip": "Snapdragon 8 Gen 2", "camera": "50MP"},
            "rating": 4.4
        },
        {
            "id": "phone_006",
            "name": "Google Pixel 8 Pro",
            "brand": "Google",
            "price": 23_000_000,
            "specs": {"screen": "6.7 inch", "chip": "Tensor G3", "camera": "50MP AI"},
            "rating": 4.7
        },
        {
            "id": "phone_007",
            "name": "Samsung Galaxy A54",
            "brand": "Samsung",
            "price": 8_000_000,
            "specs": {"screen": "6.4 inch", "chip": "Exynos 1280", "camera": "50MP"},
            "rating": 4.2
        },
        {
            "id": "phone_008",
            "name": "Xiaomi Redmi Note 13",
            "brand": "Xiaomi",
            "price": 6_500_000,
            "specs": {"screen": "6.67 inch", "chip": "Snapdragon 685", "camera": "108MP"},
            "rating": 4.1
        },
    ]
}


# ============================================================================
# Product Recommendation Agent V2
# ============================================================================

class ProductRecommendationAgentV2:
    """Product recommendation agent with cleaner workflow and better ranking."""

    def __init__(
        self,
        llm: LLMProvider,
        max_steps: int = 10,
        max_clarification_loops: int = 2,
        min_recommendations: int = 3
    ):
        self.llm = llm
        self.max_steps = max_steps
        self.max_clarification_loops = max_clarification_loops
        self.min_recommendations = min_recommendations

    # ------------------------------------------------------------------------
    # Workflow Helpers
    # ------------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Extract the first JSON object from text."""
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return None
            return json.loads(match.group())
        except Exception:
            return None

    @staticmethod
    def _language_safe_product_type(query: str) -> str:
        if "điện thoại" in query.lower() or "phone" in query.lower():
            return "phone"
        return "phone"

    def _build_understand_prompt(self, user_input: str) -> Dict[str, str]:
        return {
            "system_prompt": (
                "You are an expert product recommendation analyst. "
                "Extract product_type, price_min, price_max, requirements, and brand_preference from the user query. "
                "Answer only with valid JSON containing these keys."
            ),
            "user_prompt": (
                f"Analyze the user query and return JSON.\n\nUser query: \"{user_input}\""
            )
        }

    def _format_product_card(self, product: Product) -> str:
        return (
            f"- {product.name} ({product.brand}) | {product.price:,} VND | Rating: {product.rating}/5 | "
            f"Score: {product.score:.1f}"
        )

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _update_history(self, state: AgentState, node: str, data: Dict[str, Any]) -> None:
        state.history.append({
            "step": state.step_count,
            "node": node,
            **data
        })

    # ------------------------------------------------------------------------
    # Workflow Nodes
    # ------------------------------------------------------------------------

    def _understand_query(self, state: AgentState) -> AgentState:
        logger.log_event("NODE_UNDERSTAND_QUERY", {"input": state.user_input})
        state.step_count += 1

        prompt_data = self._build_understand_prompt(state.user_input)
        result = self.llm.generate(prompt_data["user_prompt"], system_prompt=prompt_data["system_prompt"])
        response_text = result.get("content", "")

        json_data = self._extract_json(response_text)
        if json_data:
            state.query_info = QueryInfo(
                product_type=json_data.get("product_type") or self._language_safe_product_type(state.user_input),
                price_min=self._safe_float(json_data.get("price_min")),
                price_max=self._safe_float(json_data.get("price_max")),
                requirements=json_data.get("requirements", []),
                brand_preference=json_data.get("brand_preference")
            )
        else:
            state.query_info = QueryInfo(
                product_type=self._language_safe_product_type(state.user_input),
                requirements=[state.user_input]
            )

        self._update_history(state, "understand_query", {
            "response_text": response_text,
            "query_info": state.query_info.dict()
        })
        return state

    def _check_info(self, state: AgentState) -> AgentState:
        logger.log_event("NODE_CHECK_INFO", {"query_info": state.query_info.dict() if state.query_info else None})
        state.step_count += 1

        if not state.query_info:
            state.query_info = QueryInfo(missing_info=["product type", "price range"])
            state.needs_clarification = True
            self._update_history(state, "check_info", {"missing_info": state.query_info.missing_info})
            return state

        missing_info: List[str] = []
        if not state.query_info.product_type:
            missing_info.append("product type")
        if state.query_info.price_min <= 0 and state.query_info.price_max <= 0:
            missing_info.append("price range")
        if not state.query_info.requirements and not state.query_info.brand_preference:
            missing_info.append("specific requirements or brand preference")

        state.query_info.missing_info = missing_info
        state.needs_clarification = len(missing_info) > 0

        self._update_history(state, "check_info", {
            "missing_info": missing_info,
            "needs_clarification": state.needs_clarification
        })
        return state

    def _ask_clarification(self, state: AgentState) -> AgentState:
        logger.log_event("NODE_ASK_CLARIFICATION", {"missing_info": state.query_info.missing_info})
        state.step_count += 1
        state.clarification_loops += 1

        prompt = (
            "The user query is missing some details. "
            f"Ask for the following information in Vietnamese: {', '.join(state.query_info.missing_info)}. "
            f"Original query: \"{state.user_input}\""
        )
        result = self.llm.generate(prompt, system_prompt="You are a polite assistant asking for clarification.")
        question = result.get("content", "")

        # Simulate user response to keep the workflow simple.
        state.needs_clarification = False
        self._update_history(state, "ask_clarification", {
            "question": question,
            "clarification_loop": state.clarification_loops
        })
        return state

    def _search_products(self, state: AgentState) -> AgentState:
        logger.log_event("NODE_SEARCH_PRODUCTS", {"product_type": state.query_info.product_type if state.query_info else None})
        state.step_count += 1

        product_type = (state.query_info.product_type or "phone").lower()
        products_data = PRODUCT_DATABASE.get(product_type, PRODUCT_DATABASE["phone"])

        price_min = state.query_info.price_min if state.query_info.price_min else 0
        price_max = state.query_info.price_max if state.query_info.price_max else float("inf")

        filtered = [p for p in products_data if price_min <= p["price"] <= price_max]
        if state.query_info and state.query_info.brand_preference:
            brand = state.query_info.brand_preference.lower()
            filtered = [p for p in filtered if brand in p["brand"].lower()]

        state.products = [
            Product(
                id=p["id"],
                name=p["name"],
                brand=p["brand"],
                price=p["price"],
                specs=p.get("specs", {}),
                rating=p.get("rating", 0.0)
            )
            for p in filtered
        ]

        self._update_history(state, "search_products", {
            "products_found": len(state.products),
            "products": [p.dict() for p in state.products[:5]]
        })
        return state

    def _score_product(self, product: Product, state: AgentState) -> float:
        score = 0.0
        score += (product.rating / 5.0) * 40

        if state.query_info and state.query_info.price_min and state.query_info.price_max:
            mid_price = (state.query_info.price_min + state.query_info.price_max) / 2
            diff = abs(product.price - mid_price)
            max_diff = max(1, (state.query_info.price_max - state.query_info.price_min) / 2)
            score += max(0, 30 - (diff / max_diff) * 30)

        if state.query_info and state.query_info.brand_preference:
            score += 30 if state.query_info.brand_preference.lower() in product.brand.lower() else 10
        else:
            score += 10

        requirements = state.query_info.requirements if state.query_info else []
        bonus = 0
        for requirement in requirements:
            kw = requirement.lower()
            if kw in product.name.lower() or any(kw in str(v).lower() for v in product.specs.values()):
                bonus += 5
        score += min(bonus, 20)
        return score

    def _filter_rank(self, state: AgentState) -> AgentState:
        logger.log_event("NODE_FILTER_RANK", {"products_count": len(state.products)})
        state.step_count += 1

        if not state.products:
            state.filtered_products = []
            return state

        for product in state.products:
            product.score = self._score_product(product, state)

        ranked = sorted(state.products, key=lambda p: p.score, reverse=True)
        state.filtered_products = ranked[: max(self.min_recommendations, 5)]
        state.recommendations = state.filtered_products

        self._update_history(state, "filter_rank", {
            "top_products": [
                {"name": p.name, "price": p.price, "score": p.score}
                for p in state.filtered_products
            ]
        })
        return state

    def _explain_recommendation(self, state: AgentState) -> AgentState:
        logger.log_event("NODE_EXPLAIN_RECOMMENDATION", {"recommendations_count": len(state.recommendations)})
        state.step_count += 1

        if not state.recommendations:
            state.explanation = "Xin lỗi, tôi không tìm được sản phẩm phù hợp với yêu cầu của bạn."
            return state

        products_info = "\n".join([self._format_product_card(p) for p in state.recommendations])
        prompt = (
            "You are a professional product recommendation advisor. "
            "Explain why these recommendations are best for the customer. "
            "Use Vietnamese and keep the answer concise.\n\n"
            f"User query: {state.user_input}\n\nRecommendations:\n{products_info}"
        )
        result = self.llm.generate(prompt, system_prompt="Explain the recommendation clearly and respectfully.")
        state.explanation = result.get("content", "")

        self._update_history(state, "explain_recommendation", {
            "explanation_length": len(state.explanation)
        })
        return state

    def _format_final_answer(self, state: AgentState) -> str:
        if not state.recommendations:
            return "Xin lỗi, không có đề xuất phù hợp ở thời điểm này."

        details = ""
        for index, product in enumerate(state.recommendations, start=1):
            details += (
                f"\n{index}. {product.name}\n"
                f"   Brand: {product.brand}\n"
                f"   Price: {product.price:,} VND\n"
                f"   Rating: {product.rating}/5\n"
                f"   Specs: {json.dumps(product.specs, ensure_ascii=False)}\n"
            )

        return (
            f"=== PRODUCT RECOMMENDATION RESULT ===\n"
            f"User Query: {state.user_input}\n\n"
            f"Found {len(state.recommendations)} recommendation(s):\n"
            f"{details}\n"
            f"💡 Reason why these products are suitable:\n{state.explanation}\n"
            f"=== END RECOMMENDATION ==="
        )

    def _return_result(self, state: AgentState) -> AgentState:
        logger.log_event("NODE_RETURN_RESULT", {"total_steps": state.step_count})
        state.step_count += 1
        state.final_answer = self._format_final_answer(state)
        self._update_history(state, "return_result", {
            "final_answer_length": len(state.final_answer)
        })
        return state

    # ------------------------------------------------------------------------
    # Main Workflow
    # ------------------------------------------------------------------------

    def run(self, user_input: str) -> Dict[str, Any]:
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name,
            "timestamp": datetime.utcnow().isoformat()
        })

        state = AgentState(user_input=user_input.strip())

        state = self._understand_query(state)
        if state.step_count >= self.max_steps:
            return self._prepare_result(state)

        state = self._check_info(state)
        if state.step_count >= self.max_steps:
            return self._prepare_result(state)

        while state.needs_clarification and state.clarification_loops < self.max_clarification_loops:
            state = self._ask_clarification(state)
            if state.step_count >= self.max_steps:
                return self._prepare_result(state)
            state = self._check_info(state)
            if state.step_count >= self.max_steps:
                return self._prepare_result(state)

        state = self._search_products(state)
        if state.step_count >= self.max_steps:
            return self._prepare_result(state)

        state = self._filter_rank(state)
        if state.step_count >= self.max_steps:
            return self._prepare_result(state)

        state = self._explain_recommendation(state)
        if state.step_count >= self.max_steps:
            return self._prepare_result(state)

        state = self._return_result(state)

        logger.log_event("AGENT_END", {
            "steps": state.step_count,
            "recommendations_count": len(state.recommendations),
            "timestamp": datetime.utcnow().isoformat()
        })

        return self._prepare_result(state)

    def _prepare_result(self, state: AgentState) -> Dict[str, Any]:
        return {
            "user_input": state.user_input,
            "recommendations": [p.dict() for p in state.recommendations],
            "explanation": state.explanation,
            "final_answer": state.final_answer,
            "steps": state.step_count,
            "clarification_loops": state.clarification_loops,
            "history": state.history
        }


# ============================================================================
# Demo Runner
# ============================================================================

if __name__ == "__main__":
    import sys
    from src.core.openai_provider import OpenAIProvider

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    llm = OpenAIProvider(model_name="gpt-4o", api_key=api_key)
    agent = ProductRecommendationAgentV2(llm=llm, max_steps=10, max_clarification_loops=2)

    query = "Tôi muốn mua điện thoại pin trâu, giá khoảng 10 triệu, ưu tiên camera tốt và màn hình lớn"
    result = agent.run(query)
    print(result["final_answer"])
    print(f"Steps: {result['steps']}, Clarification loops: {result['clarification_loops']}")
