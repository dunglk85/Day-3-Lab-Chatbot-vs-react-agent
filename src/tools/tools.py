"""
Tool Definitions for the Phone Consultant Agent.
These are actual implementations of tools that the ReAct agent can call.
"""

import json
from typing import Dict, Any

# Mock database for products
PRODUCT_DATABASE = {
    "iPhone 15": {
        "price": 799,
        "stock": 50,
        "battery_hours": 20,
        "specs": "A17 Pro, 6.1\" OLED, 48MP camera"
    },
    "Samsung Galaxy S24": {
        "price": 899,
        "stock": 30,
        "battery_hours": 22,
        "specs": "Snapdragon 8 Gen 3, 6.2\" AMOLED, 50MP camera"
    },
    "Google Pixel 8": {
        "price": 799,
        "stock": 40,
        "battery_hours": 18,
        "specs": "Tensor G3, 6.2\" OLED, AI features"
    },
}

SHIPPING_RATES = {
    "USA": 5.0,
    "Vietnam": 10.0,
    "Europe": 15.0,
    "Asia": 12.0,
}


def check_stock(args: str) -> str:
    """
    Check if a product is in stock.
    Args: product_name (string)
    Returns: Stock availability and quantity
    """
    try:
        product_name = args.strip().strip('"\'').lower()
        
        # Find product (case-insensitive)
        for key, value in PRODUCT_DATABASE.items():
            if key.lower() == product_name:
                stock = value["stock"]
                status = "In Stock" if stock > 0 else "Out of Stock"
                return f"{status}: {stock} units available for {key}"
        
        return f"Product '{args}' not found in database."
    except Exception as e:
        return f"Error checking stock: {e}"


def get_product_price(args: str) -> str:
    """
    Get the price of a product.
    Args: product_name (string)
    Returns: Price in USD
    """
    try:
        product_name = args.strip().strip('"\'').lower()
        
        for key, value in PRODUCT_DATABASE.items():
            if key.lower() == product_name:
                return f"Price of {key}: ${value['price']}"
        
        return f"Product '{args}' not found."
    except Exception as e:
        return f"Error getting price: {e}"


def calculate_tax(args: str) -> str:
    """
    Calculate 10% tax on an amount.
    Args: amount (float or string)
    Returns: Tax amount
    """
    try:
        # Handle simple format like "100" or "100.00"
        amount = float(args.strip().replace("$", ""))
        tax = amount * 0.1
        total = amount + tax
        return f"Amount: ${amount:.2f}, Tax (10%): ${tax:.2f}, Total: ${total:.2f}"
    except ValueError:
        return f"Error: Could not parse amount '{args}'. Please provide a number."
    except Exception as e:
        return f"Error calculating tax: {e}"


def get_shipping_cost(args: str) -> str:
    """
    Get shipping cost to a destination.
    Args: destination (string) - City or country name
    Returns: Shipping cost in USD
    """
    try:
        destination = args.strip().strip('"\'').lower()
        
        # Match destination to region
        if "hanoi" in destination or "vietnam" in destination or "viet" in destination:
            cost = SHIPPING_RATES["Vietnam"]
            return f"Shipping to Vietnam: ${cost}"
        elif "usa" in destination or "united states" in destination:
            cost = SHIPPING_RATES["USA"]
            return f"Shipping to USA: ${cost}"
        elif "europe" in destination or "uk" in destination or "france" in destination:
            cost = SHIPPING_RATES["Europe"]
            return f"Shipping to Europe: ${cost}"
        elif "asia" in destination or "singapore" in destination or "thailand" in destination:
            cost = SHIPPING_RATES["Asia"]
            return f"Shipping to Asia: ${cost}"
        else:
            return f"Unknown destination '{args}'. Available: USA, Vietnam, Europe, Asia"
    except Exception as e:
        return f"Error getting shipping cost: {e}"


def get_battery_life(args: str) -> str:
    """
    Get battery life for a product.
    Args: product_name (string)
    Returns: Battery hours
    """
    try:
        product_name = args.strip().strip('"\'').lower()
        
        for key, value in PRODUCT_DATABASE.items():
            if key.lower() == product_name:
                return f"Battery life of {key}: {value['battery_hours']} hours"
        
        return f"Product '{args}' not found."
    except Exception as e:
        return f"Error getting battery life: {e}"


def compare_products(args: str) -> str:
    """
    Compare two products side-by-side.
    Args: "product1 vs product2" or "product1, product2"
    Returns: Comparison table
    """
    try:
        # Parse the two products
        if " vs " in args.lower():
            products = [p.strip().strip('"\'') for p in args.lower().split(" vs ")]
        elif "," in args:
            products = [p.strip().strip('"\'') for p in args.split(",")]
        else:
            return "Error: Use format 'iPhone 15 vs Samsung Galaxy S24'"
        
        if len(products) != 2:
            return "Error: Please compare exactly 2 products."
        
        # Find both products
        product_data = {}
        for product_name in products:
            for key, value in PRODUCT_DATABASE.items():
                if key.lower() == product_name:
                    product_data[key] = value
                    break
        
        if len(product_data) != 2:
            return f"Could not find both products. Available: {', '.join(PRODUCT_DATABASE.keys())}"
        
        # Build comparison
        keys = list(product_data.keys())
        p1_name, p2_name = keys[0], keys[1]
        p1, p2 = product_data[p1_name], product_data[p2_name]
        
        comparison = f"""
COMPARISON: {p1_name} vs {p2_name}
{'='*50}
Price:       ${p1['price']}           vs  ${p2['price']}
Stock:       {p1['stock']} units      vs  {p2['stock']} units
Battery:     {p1['battery_hours']}h           vs  {p2['battery_hours']}h
Specs:       {p1['specs'][:20]}... vs {p2['specs'][:20]}...
"""
        return comparison.strip()
    except Exception as e:
        return f"Error comparing products: {e}"


# List of tools available to the agent
TOOLS = [
    {
        "name": "check_stock",
        "description": "Check if a product is in stock and how many units are available. Input: product_name (e.g., 'iPhone 15')",
        "function": check_stock
    },
    {
        "name": "get_product_price",
        "description": "Get the price of a product in USD. Input: product_name (e.g., 'iPhone 15')",
        "function": get_product_price
    },
    {
        "name": "calculate_tax",
        "description": "Calculate 10% tax on a purchase amount. Input: amount (e.g., '999' or '$999')",
        "function": calculate_tax
    },
    {
        "name": "get_shipping_cost",
        "description": "Get shipping cost to a destination country or city. Input: destination (e.g., 'Vietnam' or 'Hanoi')",
        "function": get_shipping_cost
    },
    {
        "name": "get_battery_life",
        "description": "Get battery life in hours for a product. Input: product_name (e.g., 'iPhone 15')",
        "function": get_battery_life
    },
    {
        "name": "compare_products",
        "description": "Compare two products side-by-side. Input: 'product1 vs product2' (e.g., 'iPhone 15 vs Samsung Galaxy S24')",
        "function": compare_products
    },
]
