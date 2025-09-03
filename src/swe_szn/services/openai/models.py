from typing import Dict, Union

MODELS = {
    # gpt-5 family
    "gpt-5": {
        "temperature": False,
        "pricing": {
            "input": 0.00125,
            "output": 0.01000,
        },
        "reasoning": True,
        "effort": "low",
    },
    "gpt-5-mini": {
        "temperature": False,
        "pricing": {
            "input": 0.00025,
            "output": 0.00200,
        },
        "reasoning": True,
        "effort": "low",
    },
    "gpt-5-nano": {
        "temperature": False,
        "pricing": {
            "input": 0.00005,
            "output": 0.00040,
        },
        "reasoning": True,
        "effort": "low",
    },
    # gpt-4.1 family
    "gpt-4.1": {
        "temperature": True,
        "pricing": {
            "input": 0.00300,
            "output": 0.01200,
        },
    },
    "gpt-4.1-mini": {
        "temperature": True,
        "pricing": {
            "input": 0.00080,
            "output": 0.00320,
        },
    },
    "gpt-4.1-nano": {
        "temperature": True,
        "pricing": {
            "input": 0.00020,
            "output": 0.00080,
        },
    },
    # gpt-4o family
    "gpt-4o": {
        "temperature": True,
        "pricing": {
            "input": 0.00250,
            "output": 0.01000,
        },
        "reasoning": False,
        "effort": None,
    },
    "gpt-4o-mini": {
        "temperature": True,
        "pricing": {
            "input": 0.00060,
            "output": 0.00240,
        },
        "reasoning": False,
        "effort": None,
    },
}


def supports_temperature(model: str) -> bool:
    cfg = MODELS.get(model) or MODELS["gpt-4o-mini"]
    return bool(cfg.get("temperature", False))


def pricing(model: str) -> Dict[str, float]:
    cfg = MODELS.get(model) or MODELS["gpt-4o-mini"]
    return cfg.get("pricing", {})


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int
) -> Dict[str, Union[float, str, dict]]:
    """Estimate the cost of an OpenAI API request"""
    model_pricing = pricing(model)
    input_cost = (input_tokens / 1000) * model_pricing.get("input", 0.0)
    output_cost = (output_tokens / 1000) * model_pricing.get("output", 0.0)
    total_cost = input_cost + output_cost

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total_cost, 6),
        "pricing_per_1k": model_pricing,
    }
