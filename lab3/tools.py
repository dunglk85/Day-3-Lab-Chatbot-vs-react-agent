from typing import Any, Dict, List

INVENTORY = {
    "iphone": {"stock": 12, "unit_price": 1200.0},
    "airpods": {"stock": 30, "unit_price": 150.0},
}
DEFAULT_TAX_RATE = 0.1


def check_stock(item_name: str) -> Dict[str, Any]:
    item_key = item_name.strip().lower()
    data = INVENTORY.get(item_key)
    if not data:
        return {"item": item_name, "error": "Item not found"}
    return {
        "item": item_name,
        "stock": data["stock"],
        "unit_price": data["unit_price"],
    }


def apply_tax(amount: float, tax_rate: float = DEFAULT_TAX_RATE) -> Dict[str, float]:
    tax = amount * tax_rate
    total = amount + tax
    return {
        "subtotal": round(amount, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
    }


def build_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "check_stock",
            "description": "Get stock and unit_price for an item. Args: {'item_name': str}.",
            "function": check_stock,
        },
        {
            "name": "apply_tax",
            "description": "Apply tax rate to amount. Args: {'amount': float, 'tax_rate': float}.",
            "function": apply_tax,
        },
    ]
