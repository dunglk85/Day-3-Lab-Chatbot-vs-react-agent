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
    """Extracted information from user query"""
    product_type: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    requirements: List[str] = Field(default_factory=list)
    brand_preference: Optional[str] = None
    missing_info: List[str] = Field(default_factory=list)


class Product(BaseModel):
    """Product data structure"""
    id: str
    name: str
    brand: str
    price: float
    specs: Dict[str, Any] = Field(default_factory=dict)
    rating: float = 0.0
    score: float = 0.0  # Ranking score


class AgentState(BaseModel):
    """State for the agent workflow"""
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
# Product Recommendation Agent (No LangGraph - Manual Flow Control)
# ============================================================================

class ProductRecommendationAgent:
    """Product recommendation agent using ReAct pattern WITHOUT LangGraph"""
    
    def __init__(self, llm: LLMProvider, max_steps: int = 10, max_clarification_loops: int = 2):
        self.llm = llm
        self.max_steps = max_steps
        self.max_clarification_loops = max_clarification_loops
    
    # ========================================================================
    # Workflow Nodes (Step Functions)
    # ========================================================================
    
    def _understand_query(self, state: AgentState) -> AgentState:
        """Step 1: Parse and extract query information"""
        logger.log_event("NODE_UNDERSTAND_QUERY", {"input": state.user_input})
        state.step_count += 1
        
        system_prompt = """You are an expert at understanding product purchase queries.
        Extract the following information from the user query:
        - product_type (what type of product they want)
        - price_min and price_max (price range in VND)
        - requirements (list of specific needs or features)
        - brand_preference (preferred brand if mentioned)
        
        Respond in JSON format with these exact keys."""
        
        prompt = f"""Analyze this query and extract product information:
        "{state.user_input}"
        
        Return JSON with keys: product_type, price_min, price_max, requirements (list), brand_preference"""
        
        result = self.llm.generate(prompt, system_prompt=system_prompt)
        response_text = result["content"]
        
        # Try to extract JSON
        try:
            # Find JSON in response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                state.query_info = QueryInfo(
                    product_type=data.get("product_type"),
                    price_min=data.get("price_min"),
                    price_max=data.get("price_max"),
                    requirements=data.get("requirements", []),
                    brand_preference=data.get("brand_preference")
                )
        except Exception as e:
            logger.log_event("PARSE_ERROR", {"error": str(e), "response": response_text})
            # Fallback: try to extract key info
            state.query_info = QueryInfo(
                product_type="phone" if "điện thoại" in state.user_input.lower() else "unknown",
                requirements=[state.user_input]
            )
        
        state.history.append({
            "step": state.step_count,
            "node": "understand_query",
            "query_info": state.query_info.dict() if state.query_info else None
        })
        
        return state
    
    def _check_info(self, state: AgentState) -> AgentState:
        """Step 2: Check if we have enough information"""
        logger.log_event("NODE_CHECK_INFO", {"query_info": state.query_info.dict() if state.query_info else None})
        state.step_count += 1
        
        if not state.query_info:
            state.needs_clarification = True
            state.query_info = QueryInfo(missing_info=["Unable to parse query"])
            return state
        
        missing_info = []
        
        # Check for mandatory fields
        if not state.query_info.product_type:
            missing_info.append("product type")
        
        if state.query_info.price_min is None and state.query_info.price_max is None:
            missing_info.append("price range")
        
        if not state.query_info.requirements and not state.query_info.brand_preference:
            missing_info.append("specific requirements or preferences")
        
        state.query_info.missing_info = missing_info
        state.needs_clarification = len(missing_info) > 0
        
        state.history.append({
            "step": state.step_count,
            "node": "check_info",
            "missing_info": missing_info,
            "needs_clarification": state.needs_clarification
        })
        
        return state
    
    def _ask_clarification(self, state: AgentState) -> AgentState:
        """Step 3: Ask user for missing information"""
        logger.log_event("NODE_ASK_CLARIFICATION", {"missing_info": state.query_info.missing_info})
        state.step_count += 1
        state.clarification_loops += 1
        
        system_prompt = """You are a helpful sales assistant. 
        Ask the user to provide missing information in a natural and polite way."""
        
        missing = ", ".join(state.query_info.missing_info)
        prompt = f"""The user query is missing: {missing}
        
        Ask them to provide this information in a friendly way.
        Original query: "{state.user_input}" """
        
        result = self.llm.generate(prompt, system_prompt=system_prompt)
        question = result["content"]
        
        # Simulate user providing clarification
        # For now, assume we got info after one clarification loop
        state.needs_clarification = False
        
        state.history.append({
            "step": state.step_count,
            "node": "ask_clarification",
            "question": question,
            "clarification_loop": state.clarification_loops
        })
        
        return state
    
    def _search_products(self, state: AgentState) -> AgentState:
        """Step 4: Search products matching criteria"""
        logger.log_event("NODE_SEARCH_PRODUCTS", {
            "product_type": state.query_info.product_type if state.query_info else None
        })
        state.step_count += 1
        
        product_type = state.query_info.product_type if state.query_info else "phone"
        
        # Get products from database
        products_data = PRODUCT_DATABASE.get(product_type.lower(), PRODUCT_DATABASE.get("phone", []))
        
        # Filter by price range
        price_min = state.query_info.price_min if state.query_info else 0
        price_max = state.query_info.price_max if state.query_info else float('inf')
        
        filtered = [p for p in products_data if price_min <= p["price"] <= price_max]
        
        # Filter by brand if specified
        if state.query_info and state.query_info.brand_preference:
            brand = state.query_info.brand_preference.lower()
            filtered = [p for p in filtered if brand in p["brand"].lower()]
        
        # Convert to Product objects
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
        
        state.history.append({
            "step": state.step_count,
            "node": "search_products",
            "products_found": len(state.products),
            "products": [p.dict() for p in state.products[:5]]
        })
        
        return state
    
    def _filter_rank(self, state: AgentState) -> AgentState:
        """Step 5: Filter and rank products"""
        logger.log_event("NODE_FILTER_RANK", {"products_count": len(state.products)})
        state.step_count += 1
        
        if not state.products:
            state.filtered_products = []
            return state
        
        # Score products based on requirements
        for product in state.products:
            score = 0.0
            
            # Rating score (0-40 points)
            score += (product.rating / 5.0) * 40
            
            # Price score - prefer products near middle of range (0-30 points)
            if state.query_info and state.query_info.price_min and state.query_info.price_max:
                mid_price = (state.query_info.price_min + state.query_info.price_max) / 2
                price_diff = abs(product.price - mid_price)
                max_diff = (state.query_info.price_max - state.query_info.price_min) / 2
                price_score = max(0, 30 - (price_diff / max_diff) * 30)
                score += price_score
            
            # Brand preference score (0-30 points)
            if state.query_info and state.query_info.brand_preference:
                if state.query_info.brand_preference.lower() in product.brand.lower():
                    score += 30
                else:
                    score += 10
            else:
                score += 10
            
            product.score = score
        
        # Sort by score (descending)
        ranked = sorted(state.products, key=lambda p: p.score, reverse=True)
        
        # Keep top products
        state.filtered_products = ranked[:5]
        state.recommendations = state.filtered_products
        
        state.history.append({
            "step": state.step_count,
            "node": "filter_rank",
            "top_products": [
                {
                    "name": p.name,
                    "price": p.price,
                    "score": p.score
                }
                for p in state.filtered_products
            ]
        })
        
        return state
    
    def _explain_recommendation(self, state: AgentState) -> AgentState:
        """Step 6: Generate explanation for recommendations"""
        logger.log_event("NODE_EXPLAIN_RECOMMENDATION", {"recommendations_count": len(state.recommendations)})
        state.step_count += 1
        
        if not state.recommendations:
            state.explanation = "Xin lỗi, không tìm được sản phẩm phù hợp với yêu cầu của bạn."
            return state
        
        system_prompt = """You are an expert product recommendation specialist. 
        Explain why each recommended product is suitable for the user's needs.
        Provide clear, concise explanations in Vietnamese."""
        
        products_info = "\n".join([
            f"- {p.name} ({p.brand}): {p.price:,} VND | Specs: {p.specs} | Rating: {p.rating}/5 | Score: {p.score:.1f}"
            for p in state.recommendations
        ])
        
        prompt = f"""User Query: {state.user_input}
        
Top Recommended Products:
{products_info}

Explain why these are the best recommendations for this user. 
Highlight unique features and value propositions."""
        
        result = self.llm.generate(prompt, system_prompt=system_prompt)
        state.explanation = result["content"]
        
        state.history.append({
            "step": state.step_count,
            "node": "explain_recommendation",
            "explanation_length": len(state.explanation)
        })
        
        return state
    
    def _return_result(self, state: AgentState) -> AgentState:
        """Step 7: Format and return final result"""
        logger.log_event("NODE_RETURN_RESULT", {"total_steps": state.step_count})
        state.step_count += 1
        
        # Build final answer
        final_answer = f"""
=== PRODUCT RECOMMENDATION RESULT ===
User Query: {state.user_input}

📋 Found {len(state.recommendations)} recommendations:

"""
        
        for idx, product in enumerate(state.recommendations, 1):
            final_answer += f"""
{idx}. {product.name}
   Brand: {product.brand}
   Price: {product.price:,} VND
   Rating: {product.rating}/5 ⭐
   Specs: {json.dumps(product.specs, ensure_ascii=False)}
"""
        
        final_answer += f"""

💡 Why these recommendations:
{state.explanation}

=== END RECOMMENDATION ===
"""
        
        state.final_answer = final_answer
        
        state.history.append({
            "step": state.step_count,
            "node": "return_result",
            "total_steps": state.step_count,
            "recommendations_count": len(state.recommendations)
        })
        
        return state
    
    # ========================================================================
    # Main Workflow Loop (ReAct Pattern - Manual Control Flow)
    # ========================================================================
    
    def run(self, user_input: str) -> Dict[str, Any]:
        """
        Execute the agent workflow using manual ReAct loop.
        
        Flow:
        1. Understand Query
        2. Check Info (loop to ask clarification if needed)
        3. Search Products
        4. Filter & Rank
        5. Explain Recommendations
        6. Return Result
        """
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name,
            "timestamp": datetime.now().isoformat()
        })
        
        state = AgentState(user_input=user_input)
        
        # ====== STEP 1: Understand Query ======
        state = self._understand_query(state)
        if state.step_count >= self.max_steps:
            logger.log_event("MAX_STEPS_REACHED", {"step": state.step_count})
            return self._prepare_result(state)
        
        # ====== STEP 2-3: Check Info & Loop for Clarification ======
        state = self._check_info(state)
        if state.step_count >= self.max_steps:
            return self._prepare_result(state)
        
        # Loop back to ask clarification if needed
        while state.needs_clarification and state.clarification_loops < self.max_clarification_loops:
            state = self._ask_clarification(state)
            if state.step_count >= self.max_steps:
                return self._prepare_result(state)
            
            # After asking, check info again
            state = self._check_info(state)
            if state.step_count >= self.max_steps:
                return self._prepare_result(state)
        
        # ====== STEP 4: Search Products ======
        state = self._search_products(state)
        if state.step_count >= self.max_steps:
            return self._prepare_result(state)
        
        # ====== STEP 5: Filter & Rank ======
        state = self._filter_rank(state)
        if state.step_count >= self.max_steps:
            return self._prepare_result(state)
        
        # ====== STEP 6: Explain Recommendation ======
        state = self._explain_recommendation(state)
        if state.step_count >= self.max_steps:
            return self._prepare_result(state)
        
        # ====== STEP 7: Return Result ======
        state = self._return_result(state)
        
        logger.log_event("AGENT_END", {
            "steps": state.step_count,
            "recommendations_count": len(state.recommendations),
            "timestamp": datetime.now().isoformat()
        })
        
        return self._prepare_result(state)
    
    def _prepare_result(self, state: AgentState) -> Dict[str, Any]:
        """Prepare the final result dictionary"""
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
# Main Demo
# ============================================================================

if __name__ == "__main__":
    import sys
    from src.core.openai_provider import OpenAIProvider
    
    # Initialize LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)
    
    llm = OpenAIProvider(model_name="gpt-4o", api_key=api_key)
    
    # Create agent
    agent = ProductRecommendationAgent(llm=llm, max_steps=10, max_clarification_loops=2)
    
    # Example query
    user_query = "Tôi muốn mua điện thoại giá từ 5 triệu đến 10 triệu, cần camera tốt và pin lâu"
    
    print(f"🚀 Starting agent for query: {user_query}\n")
    
    result = agent.run(user_query)
    
    print(result["final_answer"])
    print(f"\n📊 Workflow completed in {result['steps']} steps")
    print(f"📝 Clarification loops: {result['clarification_loops']}")
