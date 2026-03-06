"""Apify integration — search the Apify Store and run actors as additional marketplace services."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger("agentaudit.apify")

APIFY_STORE_ACTOR = "louisdeconinck~apify-store-scraper-api"
APIFY_BASE = "https://api.apify.com/v2"


async def search_apify_store(
    query: str,
    apify_api_key: str,
    category: str = "AI",
    max_results: int = 8,
    pricing_model: str = "",
) -> list[dict]:
    """Search the Apify Store for actors matching the query.

    Returns a normalised list compatible with our marketplace entry format.
    """
    if not apify_api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{APIFY_BASE}/acts/{APIFY_STORE_ACTOR}/run-sync-get-dataset-items",
                params={"token": apify_api_key},
                json={
                    "search": query,
                    "sortBy": "popularity",
                    "category": category if category else "AI",
                    **({"pricingModel": pricing_model} if pricing_model else {}),
                    "offset": 0,
                },
            )
            if resp.status_code not in (200, 201):
                logger.warning(f"[apify] Store search returned {resp.status_code}")
                return []
            items = resp.json()
            if not isinstance(items, list):
                return []

            results = []
            for item in items[:max_results]:
                actor_id = f"{item.get('username', '')}~{item.get('name', '')}"
                pricing = item.get("currentPricingInfo") or {}
                pricing_model_val = pricing.get("pricingModel", "unknown")
                price_usd = pricing.get("pricePerUnitUsd", 0) or 0
                runs = (item.get("stats") or {}).get("totalRuns", 0)
                results.append({
                    "team_name": f"Apify: {item.get('title', actor_id)}",
                    "endpoint_url": f"apify://{actor_id}",
                    "description": (item.get("readmeSummary") or item.get("description") or "")[:300],
                    "source": "apify",
                    "actor_id": actor_id,
                    "category": ", ".join(item.get("categories") or []),
                    "keywords": [],
                    "price_credits": f"${price_usd:.4f}/run" if price_usd else "free",
                    "pricing_model": pricing_model_val,
                    "stats": {"total_runs": runs, "rating": item.get("actorReviewRating")},
                    "apify_url": item.get("url", ""),
                    "agentic_payments": item.get("isWhiteListedForAgenticPayments", False),
                })
            logger.info(f"[apify] Store search for '{query}' returned {len(results)} results")
            return results
    except Exception as e:
        logger.warning(f"[apify] Store search error: {e}")
        return []


async def run_apify_actor(
    actor_id: str,
    input_data: dict,
    apify_api_key: str,
    timeout: float = 60.0,
) -> dict:
    """Run an Apify actor synchronously and return its dataset items.

    actor_id format: 'username~actorname' e.g. 'apify~rag-web-browser'
    """
    if not apify_api_key or not actor_id:
        return {"error": "missing actor_id or api_key"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items",
                params={"token": apify_api_key},
                json=input_data,
            )
            if resp.status_code not in (200, 201):
                return {"error": f"Apify actor returned {resp.status_code}", "body": resp.text[:300]}
            items = resp.json()
            return {"actor_id": actor_id, "items": items if isinstance(items, list) else [items], "count": len(items) if isinstance(items, list) else 1}
    except httpx.TimeoutException:
        return {"error": f"Apify actor {actor_id} timed out ({timeout}s). Try async run instead."}
    except Exception as e:
        return {"error": str(e)}


# Well-known actors we can reliably run with a plain query input
RUNNABLE_ACTORS: dict[str, dict] = {
    "apify~rag-web-browser": {
        "description": "RAG Web Browser — searches the web and returns clean text for LLMs",
        "input_fn": lambda query: {"query": query, "maxResults": 5},
    },
    "apify~website-content-crawler": {
        "description": "Website Content Crawler — extracts structured content from any URL",
        "input_fn": lambda query: {"startUrls": [{"url": query}], "maxCrawlPages": 1} if query.startswith("http") else {"startUrls": []},
    },
    "apify~ai-web-agent": {
        "description": "AI Web Agent — autonomous browser agent that completes web tasks",
        "input_fn": lambda query: {"task": query},
    },
}


async def run_best_apify_actor(query: str, apify_api_key: str) -> dict:
    """Pick and run the most appropriate Apify actor for the given query."""
    if not apify_api_key:
        return {"error": "APIFY_API_KEY not set"}

    # RAG browser is the most versatile for research queries
    actor_id = "apify~rag-web-browser"
    actor_info = RUNNABLE_ACTORS[actor_id]
    input_data = actor_info["input_fn"](query)
    if not input_data.get("query") and not input_data.get("task"):
        return {"error": "Could not build valid input for actor"}

    logger.info(f"[apify] Running {actor_id} for query: {query[:60]}")
    result = await run_apify_actor(actor_id, input_data, apify_api_key, timeout=45.0)
    result["actor_used"] = actor_id
    result["actor_description"] = actor_info["description"]
    return result
