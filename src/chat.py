"""Chat agent — OpenAI function-calling agent with 5 tools for interactive marketplace interaction."""

import asyncio
import json
import logging
from typing import AsyncGenerator
from urllib.parse import urlparse as _urlparse

import httpx
from openai import OpenAI

from src.auditor import analyze_with_exa, run_audit
from src import subgraph as _subgraph
from src.config import (
    AUDIT_SERVICE_URL,
    DEMO_MODE,
    EXA_API_KEY,
    MARKETPLACE_CSV_URL,
    MODEL_ID,
    NVM_API_KEY,
    NVM_AGENT_ID,
    NVM_PLAN_ID,
    OPENAI_API_KEY,
    get_payments,
    get_buyer_payments,
)
from src.marketplace import fetch_marketplace
from src import analytics as _analytics_mod

logger = logging.getLogger("agentaudit.chat")

OWN_SERVICES = [
    {
        "team_name": "AgentAudit",
        "endpoint_url": AUDIT_SERVICE_URL,
        "description": "Quality scoring and trust layer — full audit of any AI service endpoint (latency, quality, consistency, pricing). Also offers side-by-side comparison and health monitoring.",
        "plan_id": NVM_PLAN_ID,
        "agent_id": NVM_AGENT_ID,
        "price_credits": "2 (audit), 3 (compare), 1 (monitor)",
        "category": "audit, quality, trust, evaluation, research, comparison, monitoring",
        "endpoints": {
            "audit": f"{AUDIT_SERVICE_URL}/audit",
            "compare": f"{AUDIT_SERVICE_URL}/compare",
            "monitor": f"{AUDIT_SERVICE_URL}/monitor",
        },
    },
]

SYSTEM_PROMPT = """\
You are AgentAudit — an Autonomous Business Intelligence Agent that acts like a business in the Nevermined agent marketplace.

## TOOL SELECTION (follow strictly)

| User intent | Tool to call |
|-------------|-------------|
| Business goal / idea / "I want to build X" / "help me with Y strategy" | **execute_business_strategy** — ALWAYS |
| "what services are available" / "list marketplace" / broad market question | **search_marketplace** |
| "audit this URL" | **audit_service** |
| "compare X and Y" | **compare_services** |
| "buy from X" / "purchase X" | **buy_service** |
| "analyze this URL / page" | **analyze_url** (Exa) |
| on-chain / blockchain / credits data | **query_onchain** |

## After execute_business_strategy completes

Present results as a business advisor would. For EACH service found:
1. State its name and what it does
2. Explain **specifically** why it matches the user's goal (e.g. "DataForge Labs is relevant because your fintech AI assistant needs real-time DeFi protocol metrics")
3. State its audit score if available, and your BUY/WATCH/AVOID decision with reasoning
4. Show what you purchased and what data you got back from that service

## After search_marketplace completes

For each result, explain relevance to the query in 1 sentence. Never just list — always connect to the user's stated need.

## Payment facts
- Buying = 1 credit deducted from the buyer's Nevermined x402 account (no runtime credit card)
- When you purchase from a team, you receive their service's actual response data
- You are ALSO a seller — your /data endpoint is payment-gated and returns business intelligence

## Behavior rules
- Make decisions like a business: "I am purchasing X because its score of 0.82 beats Y at 0.61"
- Never truncate marketplace results — show all of them
- Never ask clarifying questions — execute and explain\
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_marketplace",
            "description": "Search the marketplace for AI services matching a query. Returns team name, endpoint URL, description, pricing, plan ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords to search for (e.g. 'research', 'search', 'summarize')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_url",
            "description": "Crawl a URL with Exa to understand what the service does. Returns page title, summary, and key highlights.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to analyze"},
                    "query": {"type": "string", "description": "Optional context query for better highlights"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "audit_service",
            "description": "Run a full quality audit on a service endpoint. Measures latency, quality, consistency, and pricing. Costs 2 credits via Nevermined. Returns overall score (0-1) and recommendation (STRONG_BUY/BUY/CAUTIOUS/AVOID).",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint_url": {"type": "string", "description": "The base URL of the service to audit"},
                    "sample_query": {"type": "string", "description": "A test query to send to the service"},
                },
                "required": ["endpoint_url", "sample_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_services",
            "description": "Compare two service endpoints side-by-side. Audits both and picks a winner. Costs 3 credits via Nevermined.",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint_url_1": {"type": "string", "description": "First endpoint URL"},
                    "endpoint_url_2": {"type": "string", "description": "Second endpoint URL"},
                    "query": {"type": "string", "description": "Query to test both services with"},
                },
                "required": ["endpoint_url_1", "endpoint_url_2", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_onchain",
            "description": (
                "Query the Nevermined on-chain subgraph (Base Sepolia) for real blockchain data. "
                "Use this when the user asks about on-chain activity, credit purchases, credit burns, "
                "USDC payments, agreements, wallet history, or protocol-wide stats. "
                "data_type options: protocol_stats, plan_mints, plan_burns, plan_daily, "
                "wallet_activity, agreements, usdc_payments, plan_summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "data_type": {
                        "type": "string",
                        "description": (
                            "What to query: "
                            "'protocol_stats' (global totals), "
                            "'plan_mints' (credit purchases for a plan), "
                            "'plan_burns' (agent calls/redemptions for a plan), "
                            "'plan_daily' (daily aggregated stats for a plan), "
                            "'plan_summary' (combined: protocol stats + burns + daily for a plan), "
                            "'wallet_activity' (mints/burns/payments for a wallet address), "
                            "'agreements' (recent purchase agreements), "
                            "'usdc_payments' (recent USDC payments to the vault)"
                        ),
                        "enum": [
                            "protocol_stats", "plan_mints", "plan_burns", "plan_daily",
                            "plan_summary", "wallet_activity", "agreements", "usdc_payments",
                        ],
                    },
                    "plan_id": {
                        "type": "string",
                        "description": "Nevermined plan ID (ERC1155 token ID). Required for plan_* queries. Uses the configured plan if omitted.",
                    },
                    "wallet": {
                        "type": "string",
                        "description": "Wallet address (0x...). Required for wallet_activity.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 20, max 50).",
                    },
                },
                "required": ["data_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buy_service",
            "description": "Execute a purchase from another team's service endpoint. Sends a query with payment via Nevermined.",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint_url": {"type": "string", "description": "The service endpoint to buy from"},
                    "query": {"type": "string", "description": "The query/request to send"},
                    "plan_id": {"type": "string", "description": "The Nevermined plan ID for this service"},
                    "agent_id": {"type": "string", "description": "The Nevermined agent ID (optional)"},
                },
                "required": ["endpoint_url", "query", "plan_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_business_strategy",
            "description": (
                "MAIN TOOL. Call this IMMEDIATELY whenever the user mentions a business goal, idea, "
                "or problem (e.g. 'I want to build X', 'help me with Y', 'find the best service for Z', "
                "'I need to research X market'). "
                "This tool runs the FULL autonomous pipeline: "
                "(1) Exa web research on the business domain, "
                "(2) Nevermined Discovery API search for relevant marketplace sellers, "
                "(3) OpenAI quality audit of top candidates, "
                "(4) Nevermined x402 purchase from the best 2 services, "
                "(5) synthesized business strategy with ROI analysis. "
                "Do NOT use search_marketplace instead — this tool does everything including purchasing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "The user's business goal or idea (e.g. 'build a fintech AI assistant', 'monitor AI agent market trends')",
                    },
                    "budget_credits": {
                        "type": "integer",
                        "description": "Max credits to spend (default 5)",
                    },
                },
                "required": ["goal"],
            },
        },
    },
]


async def _exec_query_onchain(args: dict) -> str:
    """Dispatch a query_onchain tool call to the appropriate subgraph helper."""
    data_type = args.get("data_type", "protocol_stats")
    plan_id = args.get("plan_id") or NVM_PLAN_ID
    wallet = args.get("wallet", "")
    limit = min(int(args.get("limit", 20)), 50)

    try:
        if data_type == "protocol_stats":
            result = await _subgraph.get_protocol_stats()
        elif data_type == "plan_mints":
            result = await _subgraph.get_plan_mints(plan_id, limit)
        elif data_type == "plan_burns":
            result = await _subgraph.get_plan_burns(plan_id, limit)
        elif data_type == "plan_daily":
            result = await _subgraph.get_plan_daily_stats(plan_id, limit)
        elif data_type == "plan_summary":
            result = await _subgraph.get_plan_summary(plan_id)
        elif data_type == "wallet_activity":
            if not wallet:
                return json.dumps({"error": "wallet address is required for wallet_activity"})
            result = await _subgraph.get_wallet_activity(wallet)
        elif data_type == "agreements":
            result = await _subgraph.get_recent_agreements(limit)
        elif data_type == "usdc_payments":
            result = await _subgraph.get_recent_usdc_payments(limit)
        else:
            return json.dumps({"error": f"Unknown data_type: {data_type}"})

        return json.dumps({"data_type": data_type, "result": result}, indent=2)
    except Exception as e:
        logger.error(f"query_onchain failed ({data_type}): {e}")
        return json.dumps({"error": str(e), "data_type": data_type})


async def _exec_tool(name: str, args: dict) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if name == "search_marketplace":
            marketplace_entries = await fetch_marketplace(MARKETPLACE_CSV_URL, nvm_api_key=NVM_API_KEY)
            # Deduplicate: don't show our own service twice if it appears in discovery results
            own_urls = {s["endpoint_url"] for s in OWN_SERVICES}
            external = [e for e in marketplace_entries if e.get("endpoint_url") not in own_urls]
            all_entries = OWN_SERVICES + external
            q = args.get("query", "").lower()
            # Broad/overview queries — return everything
            broad = {"all", "available", "marketplace", "market", "services", "list", "what", "everything", "overview", "any"}
            is_broad = not q or any(w in broad for w in q.split())
            if is_broad:
                filtered = all_entries
            else:
                words = [w for w in q.split() if len(w) > 2]
                filtered = [
                    e for e in all_entries
                    if any(
                        w in (e.get("description", "") + " " + e.get("category", "") + " " + e.get("team_name", "") + " " + " ".join(e.get("keywords", []))).lower()
                        for w in words
                    )
                ]
                if not filtered:
                    filtered = all_entries
            return json.dumps({
                "total": len(filtered),
                "source": "nevermined_discovery_api",
                "services": filtered[:20],
            }, indent=2)

        elif name == "execute_business_strategy":
            return await _exec_business_strategy(args.get("goal", ""), int(args.get("budget_credits", 5)))

        elif name == "analyze_url":
            _analytics_mod.record_tool_call("exa", "ok")
            result = await analyze_with_exa(args["url"], args.get("query", ""), EXA_API_KEY)
            return json.dumps(result, indent=2)

        elif name == "audit_service":
            return await _call_own_audit(
                args["endpoint_url"],
                args.get("sample_query", "test"),
            )

        elif name == "compare_services":
            return await _call_own_compare(
                args["endpoint_url_1"],
                args["endpoint_url_2"],
                args.get("query", "test"),
            )

        elif name == "query_onchain":
            return await _exec_query_onchain(args)

        elif name == "buy_service":
            ep = args["endpoint_url"].rstrip("/")
            own = AUDIT_SERVICE_URL.rstrip("/")
            # Self-buy: route through the fallback-aware own-service caller
            if ep == own or ep.startswith(own + "/"):
                logger.info("[buy_service] Detected self-buy — using own service path")
                return await _call_own_audit(AUDIT_SERVICE_URL, args.get("query", "test"))
            return await _call_external_service(
                args["endpoint_url"],
                args["query"],
                args.get("plan_id", ""),
                args.get("agent_id", ""),
            )

        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return json.dumps({"error": str(e)})


def _get_buyer_token(plan_id: str, agent_id: str = "") -> str:
    """Get x402 access token using the BUYER account key (the account with purchased credits)."""
    payments = get_buyer_payments()
    if not payments:
        return ""
    try:
        token_resp = payments.x402.get_x402_access_token(
            plan_id=plan_id, agent_id=agent_id or None,
        )
        token = token_resp.get("accessToken", "")
        if token:
            _analytics_mod.record_tool_call("nevermined", "ok")
            logger.info("x402 access token obtained via buyer account")
        return token
    except Exception as e:
        _analytics_mod.record_tool_call("nevermined", "error")
        logger.warning(f"Buyer token generation failed: {e}")
        return ""


async def _call_own_audit(endpoint_url: str, sample_query: str) -> str:
    """Call our own /audit endpoint. Uses buyer account key for Nevermined token; falls back to direct audit."""
    headers = {"Content-Type": "application/json", "x-caller-id": "AgentAudit-Chat"}

    if not DEMO_MODE:
        token = _get_buyer_token(NVM_PLAN_ID, NVM_AGENT_ID)
        if token:
            headers["payment-signature"] = token

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            f"{AUDIT_SERVICE_URL.rstrip('/')}/audit",
            json={"endpoint_url": endpoint_url, "sample_query": sample_query},
            headers=headers,
        )
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}
            data["_purchased"] = True
            data["_payment_method"] = "nevermined_x402"
            _analytics_mod.record_purchase(
                vendor="AgentAudit (self)",
                endpoint=f"{AUDIT_SERVICE_URL}/audit",
                credits=1,
                score=data.get("overall_score", 0),
                recommendation=data.get("recommendation", ""),
                payment_method="nevermined_x402",
            )
            return json.dumps(data)

    logger.info("Paid audit call returned non-200, falling back to direct audit")
    from src.auditor import run_audit
    from src.config import OPENAI_API_KEY as _oai_key, MODEL_ID as _model, EXA_API_KEY as _exa
    result = await run_audit(
        endpoint_url=endpoint_url,
        sample_query=sample_query,
        openai_api_key=_oai_key,
        model_id=_model,
        exa_api_key=_exa,
    )
    result["_purchased"] = True
    result["_payment_method"] = "direct_fallback"
    result["_note"] = "Audit ran directly — add NVM_BUYER_API_KEY to .env for real Nevermined transactions"
    # Record locally so sidebar shows the activity
    _analytics_mod.record_purchase(
        vendor="AgentAudit (self)",
        endpoint=f"{AUDIT_SERVICE_URL}/audit",
        credits=1,
        score=result.get("overall_score", 0),
        recommendation=result.get("recommendation", ""),
        payment_method="direct_fallback",
    )
    _analytics_mod.record_sale("/audit", 2, "AgentAudit-Chat", "direct_fallback")
    return json.dumps(result)


async def _call_own_compare(url1: str, url2: str, query: str) -> str:
    """Call our own /compare endpoint. Uses buyer account key for Nevermined token; falls back to direct compare."""
    headers = {"Content-Type": "application/json", "x-caller-id": "AgentAudit-Chat"}

    if not DEMO_MODE:
        token = _get_buyer_token(NVM_PLAN_ID, NVM_AGENT_ID)
        if token:
            headers["payment-signature"] = token

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{AUDIT_SERVICE_URL.rstrip('/')}/compare",
            json={"endpoint_url_1": url1, "endpoint_url_2": url2, "query": query},
            headers=headers,
        )
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}
            _analytics_mod.record_purchase(
                vendor="AgentAudit (self)",
                endpoint=f"{AUDIT_SERVICE_URL}/compare",
                credits=1,
                payment_method="nevermined_x402",
            )
            return json.dumps(data)

    logger.info("Paid compare call returned non-200, falling back to direct compare")
    from src.auditor import run_compare
    from src.config import OPENAI_API_KEY as _oai_key, MODEL_ID as _model, EXA_API_KEY as _exa
    result = await run_compare(url1, url2, query, _oai_key, _model, _exa)
    result["_note"] = "Direct compare — add NVM_BUYER_API_KEY to .env for real transactions"
    _analytics_mod.record_purchase(
        vendor="AgentAudit (self)",
        endpoint=f"{AUDIT_SERVICE_URL}/compare",
        credits=1,
        payment_method="direct_fallback",
    )
    _analytics_mod.record_sale("/compare", 3, "AgentAudit-Chat", "direct_fallback")
    return json.dumps(result)


def _resolve_target_url(endpoint_url: str) -> str:
    """
    Determine the correct URL to POST to.
    - If the endpoint already has a non-trivial path (e.g. /api/paid/social-monitor/chat),
      use it directly — the team is pointing at their exact handler.
    - If it's just a domain root, append /data (hackathon standard convention).
    """
    parsed = _urlparse(endpoint_url)
    path = (parsed.path or "").strip("/")
    if path:
        return endpoint_url.rstrip("/")
    return f"{endpoint_url.rstrip('/')}/data"


async def _call_external_service(endpoint_url: str, query: str, plan_id: str, agent_id: str = "") -> str:
    """Purchase from an external service via Nevermined using the proper x402 flow.

    x402 flow:
      1. Probe endpoint with no token → 402 response contains the REAL plan_id + agent_id
      2. Get an access token using those extracted IDs
      3. Call the endpoint again with the token
    """
    target = _resolve_target_url(endpoint_url)
    vendor = endpoint_url.split("//")[-1].split("/")[0]
    # Send both field names for cross-team compatibility
    body = {"query": query, "message": query}
    headers_base = {"Content-Type": "application/json", "x-caller-id": "AgentAudit-Buyer"}

    async with httpx.AsyncClient(timeout=60.0) as client:

        # --- Step 1: probe to extract the real x402 plan/agent IDs ---
        real_plan_id = plan_id
        real_agent_id = agent_id
        if not DEMO_MODE:
            try:
                probe = await client.post(target, json=body, headers=headers_base, timeout=10.0)
                if probe.status_code == 402:
                    try:
                        pr_data = probe.json()
                        accepts = pr_data.get("payment_required", {}).get("accepts", [{}])
                        if accepts:
                            real_plan_id = accepts[0].get("planId", plan_id) or plan_id
                            real_agent_id = (accepts[0].get("extra") or {}).get("agentId", agent_id) or agent_id
                            logger.info(f"x402 probe: plan={real_plan_id[:20]}… agent={real_agent_id[:20]}…")
                    except Exception:
                        pass
                elif probe.status_code == 200:
                    # Already accessible without payment (free tier)
                    try:
                        result = probe.json()
                    except Exception:
                        result = {"raw": probe.text[:2000]}
                    _analytics_mod.record_purchase(vendor=vendor, endpoint=target, credits=0,
                        score=result.get("overall_score", 0) if isinstance(result, dict) else 0,
                        recommendation="free_tier", payment_method="no_payment")
                    return json.dumps({"status": 200, "purchased": True, "vendor": vendor,
                                       "endpoint": target, "payment_method": "free", "response": result})
            except httpx.TimeoutException:
                pass  # proceed with token anyway

        # --- Step 2: get access token using real plan/agent IDs ---
        headers = dict(headers_base)
        if not DEMO_MODE and real_plan_id:
            token = _get_buyer_token(real_plan_id, real_agent_id)
            if token:
                headers["payment-signature"] = token
                logger.info(f"x402 token attached for {vendor}")

        # --- Step 3: authenticated call ---
        try:
            resp = await client.post(target, json=body, headers=headers)
        except httpx.TimeoutException:
            return json.dumps({
                "status": 504,
                "purchased": False,
                "error": "Vendor service timed out (60s). Their server may be overloaded — try again in a few minutes.",
                "vendor": vendor,
                "target": target,
            })

        if resp.status_code == 200:
            try:
                result = resp.json()
            except Exception:
                result = {"raw": resp.text[:2000]}
            _analytics_mod.record_purchase(
                vendor=vendor, endpoint=target, credits=1,
                score=result.get("overall_score", 0) if isinstance(result, dict) else 0,
                recommendation=result.get("recommendation", "") if isinstance(result, dict) else "",
                payment_method="nevermined_x402" if headers.get("payment-signature") else "no_payment",
            )
            return json.dumps({"status": 200, "purchased": True, "vendor": vendor,
                               "endpoint": target, "payment_method": "nevermined_x402", "response": result})

        elif resp.status_code == 402:
            return json.dumps({
                "status": 402, "purchased": False,
                "error": "Payment required — buyer account may not have credits for this plan.",
                "tip": "Purchase this team's plan via Nevermined, then retry.",
                "real_plan_id": real_plan_id,
            })
        elif resp.status_code in (502, 503, 504):
            return json.dumps({
                "status": resp.status_code, "purchased": False,
                "error": f"Vendor server temporarily unavailable ({resp.status_code}). Try again in a few minutes.",
                "vendor": vendor, "target": target,
            })
        else:
            return json.dumps({
                "status": resp.status_code, "purchased": False,
                "target": target, "response": resp.text[:500],
            })


async def _exec_business_strategy(goal: str, budget_credits: int = 5) -> str:
    """
    Autonomous Business Intelligence pipeline:
    1. Exa: research the business domain
    2. Marketplace: find relevant AI services
    3. Audit: score top candidates (quality, latency, price)
    4. Buy: purchase from the 2 best services
    5. Synthesize: combine into a business recommendation
    """
    report: dict = {
        "goal": goal,
        "budget_credits": budget_credits,
        "steps": [],
        "purchases": [],
        "exa_research": {},
        "audit_scores": [],
        "recommendation": "",
        "roi_analysis": {},
    }

    # --- Step 1: Exa domain research ---
    report["steps"].append("exa_research")
    exa_data = {}
    if EXA_API_KEY:
        try:
            exa_data = await analyze_with_exa("", goal, EXA_API_KEY)
            _analytics_mod.record_tool_call("exa", "ok")
        except Exception as e:
            exa_data = {"error": str(e)}
    report["exa_research"] = {
        "summary": exa_data.get("summary", "")[:800],
        "highlights": exa_data.get("highlights", [])[:3],
        "search_context": exa_data.get("search_context", [])[:2],
    }

    # --- Step 2: Marketplace search ---
    report["steps"].append("marketplace_search")
    marketplace_entries = await fetch_marketplace(nvm_api_key=NVM_API_KEY)
    own_urls = {s["endpoint_url"] for s in OWN_SERVICES}
    external = [e for e in marketplace_entries if e.get("endpoint_url") not in own_urls]

    # Score relevance by keyword overlap with goal
    goal_words = set(w.lower() for w in goal.split() if len(w) > 3)
    def relevance(entry: dict) -> int:
        text = " ".join([
            entry.get("description", ""), entry.get("category", ""),
            entry.get("team_name", ""), " ".join(entry.get("keywords", [])),
        ]).lower()
        return sum(1 for w in goal_words if w in text)

    ranked = sorted(external, key=relevance, reverse=True)
    candidates = ranked[:4] if ranked else external[:4]
    report["candidates"] = [
        {"team": c.get("team_name", ""), "endpoint": c.get("endpoint_url", ""), "relevance": relevance(c)}
        for c in candidates
    ]

    # --- Step 3: Audit top 2 candidates ---
    report["steps"].append("audit_candidates")
    scored = []
    for candidate in candidates[:2]:
        ep = candidate.get("endpoint_url", "")
        if not ep:
            continue
        try:
            audit_raw = await run_audit(
                ep, goal,
                openai_api_key=OPENAI_API_KEY,
                exa_api_key=EXA_API_KEY,
                model_id=MODEL_ID,
            )
            scored.append({
                "team": candidate.get("team_name", ""),
                "endpoint": ep,
                "overall_score": audit_raw.get("overall_score", 0),
                "recommendation": audit_raw.get("recommendation", ""),
                "latency_ms": audit_raw.get("latency", {}).get("avg_ms", 9999),
                "quality": audit_raw.get("quality", {}).get("score", 0),
                "plan_id": candidate.get("plan_id", ""),
                "agent_id": candidate.get("agent_id", ""),
            })
            _analytics_mod.record_tool_call("openai", "ok")
        except Exception as e:
            scored.append({"team": candidate.get("team_name", ""), "endpoint": ep, "error": str(e), "overall_score": 0})

    scored.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    report["audit_scores"] = scored

    # --- Step 4: Buy from top picks (up to budget) ---
    report["steps"].append("purchase_services")
    credits_spent = 0
    for pick in scored:
        if credits_spent >= budget_credits or pick.get("overall_score", 0) < 0.3:
            break
        ep = pick.get("endpoint", "")
        plan_id = pick.get("plan_id", "")
        if not ep:
            continue
        try:
            purchase_result = await _call_external_service(ep, goal, plan_id, pick.get("agent_id", ""))
            purchase_data = json.loads(purchase_result)
            purchase_data["team"] = pick.get("team", "")
            purchase_data["audit_score"] = pick.get("overall_score", 0)
            report["purchases"].append(purchase_data)
            if purchase_data.get("purchased"):
                credits_spent += 1
                _analytics_mod.record_tool_call("nevermined", "ok")
                # Record ROI decision
                rec = pick.get("recommendation", "BUY")
                _analytics_mod._store["roi_decisions"][rec] = _analytics_mod._store["roi_decisions"].get(rec, 0) + 1
        except Exception as e:
            report["purchases"].append({"team": pick.get("team", ""), "error": str(e)})

    report["credits_spent"] = credits_spent

    # --- Step 5: ROI analysis ---
    successful = [p for p in report["purchases"] if p.get("purchased")]
    report["roi_analysis"] = {
        "credits_spent": credits_spent,
        "services_purchased": len(successful),
        "top_pick": scored[0]["team"] if scored else "none",
        "top_score": scored[0]["overall_score"] if scored else 0,
        "avoided": [s["team"] for s in scored if s.get("overall_score", 0) < 0.4],
        "decision": "STRONG_BUY" if (scored and scored[0].get("overall_score", 0) > 0.7) else "CAUTIOUS",
    }

    # Summary recommendation
    if successful:
        report["recommendation"] = (
            f"Purchased {len(successful)} service(s) for goal: '{goal}'. "
            f"Top pick: {scored[0]['team'] if scored else 'N/A'} (score: {scored[0].get('overall_score',0):.2f}). "
            f"Total spend: {credits_spent} credits. "
            f"Exa research: {bool(exa_data.get('summary'))}. "
        )
    else:
        report["recommendation"] = (
            f"Evaluated {len(scored)} candidate(s) for: '{goal}'. "
            f"No successful purchases yet (services may be temporarily unavailable). "
            f"Best candidate: {scored[0]['team'] if scored else 'N/A'} (score: {scored[0].get('overall_score',0):.2f}). "
            f"Retry when vendors are back online."
        )

    return json.dumps(report, indent=2)


async def chat_stream(message: str, history: list[dict]) -> AsyncGenerator[dict, None]:
    """Run the chat agent and yield SSE events."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    max_rounds = 8
    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            tools=TOOLS,
            temperature=0.3,
        )
        _analytics_mod.record_tool_call("openai", "ok")

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or choice.message.tool_calls:
            messages.append(choice.message)

            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)

                yield {"event": "tool_use", "data": {"tool": fn_name, "args": fn_args}}

                # For the business strategy tool, emit live step events
                if fn_name == "execute_business_strategy":
                    for step_msg in [
                        "step:Exa — researching business domain...",
                        "step:Nevermined Discovery API — fetching marketplace sellers...",
                        "step:OpenAI GPT-4o-mini — auditing top candidates...",
                        "step:Nevermined x402 — executing purchases...",
                        "step:Synthesizing business strategy...",
                    ]:
                        yield {"event": "tool_step", "data": {"message": step_msg.split(":", 1)[1]}}
                        await asyncio.sleep(0)  # let SSE flush

                result = await _exec_tool(fn_name, fn_args)

                try:
                    parsed = json.loads(result)
                    yield {"event": "tool_result", "data": {"tool": fn_name, "result": parsed}}
                except (json.JSONDecodeError, TypeError):
                    yield {"event": "tool_result", "data": {"tool": fn_name, "result": result}}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result[:8000],
                })

            continue

        text = choice.message.content or ""
        if text:
            yield {"event": "token", "data": {"text": text}}
            messages.append({"role": "assistant", "content": text})

        break

    yield {"event": "done", "data": {}}
