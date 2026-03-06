"""Nevermined subgraph client — Base Sepolia (Goldsky).

Async helpers for querying on-chain protocol activity:
  - Protocol-wide cumulative stats
  - Per-plan credit mints / burns / daily aggregates
  - Wallet activity (mints + burns + USDC payments)
  - Recent purchase agreements
"""

import logging

import httpx

logger = logging.getLogger("agentaudit.subgraph")

SUBGRAPH_URL = (
    "https://api.goldsky.com/api/public/project_cmmdxa29pqd7301x809tn06ng"
    "/subgraphs/nevermined-base-sepolia/1.0.0/gn"
)


async def _gql(query: str) -> dict:
    """Execute a raw GraphQL query against the Goldsky endpoint."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            SUBGRAPH_URL,
            json={"query": query},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            logger.warning(f"Subgraph errors: {payload['errors']}")
        return payload.get("data", {})


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

async def get_protocol_stats() -> dict:
    """Global cumulative protocol metrics (single 'global' entity)."""
    data = await _gql("""
    {
      protocolStats(id: "global") {
        totalMints
        totalBurns
        totalCreditsMinted
        totalCreditsBurned
        totalUSDCVolume
        totalAgreements
        totalFulfilledConditions
      }
    }
    """)
    return data.get("protocolStats") or {}


async def get_plan_mints(plan_id: str, limit: int = 20) -> list:
    """Recent credit mints (purchases) for a specific plan."""
    data = await _gql(f"""
    {{
      creditTransfers(
        where: {{ type: "mint", planId: "{plan_id}" }}
        orderBy: blockTimestamp
        orderDirection: desc
        first: {limit}
      ) {{
        id
        to
        planId
        amount
        blockTimestamp
        transactionHash
      }}
    }}
    """)
    return data.get("creditTransfers") or []


async def get_plan_burns(plan_id: str, limit: int = 20) -> list:
    """Recent credit burns (agent calls / redemptions) for a specific plan."""
    data = await _gql(f"""
    {{
      creditTransfers(
        where: {{ type: "burn", planId: "{plan_id}" }}
        orderBy: blockTimestamp
        orderDirection: desc
        first: {limit}
      ) {{
        id
        from
        planId
        amount
        blockTimestamp
        transactionHash
      }}
    }}
    """)
    return data.get("creditTransfers") or []


async def get_plan_daily_stats(plan_id: str, days: int = 30) -> list:
    """Pre-aggregated daily stats for a plan. Ordered most-recent first."""
    data = await _gql(f"""
    {{
      dailyPlanStats(
        where: {{ planId: "{plan_id}" }}
        orderBy: date
        orderDirection: desc
        first: {days}
      ) {{
        date
        planId
        mintCount
        burnCount
        transferCount
        creditsMinted
        creditsBurned
        creditsTransferred
      }}
    }}
    """)
    return data.get("dailyPlanStats") or []


async def get_wallet_activity(address: str) -> dict:
    """All on-chain activity for a wallet: mints received, burns (agent calls), USDC payments."""
    addr = address.lower()
    data = await _gql(f"""
    {{
      mints: creditTransfers(
        where: {{ to: "{addr}", type: "mint" }}
        orderBy: blockTimestamp
        orderDirection: desc
        first: 50
      ) {{
        planId
        amount
        blockTimestamp
        transactionHash
      }}
      burns: creditTransfers(
        where: {{ from: "{addr}", type: "burn" }}
        orderBy: blockTimestamp
        orderDirection: desc
        first: 50
      ) {{
        planId
        amount
        blockTimestamp
        transactionHash
      }}
      payments: usdcpayments(
        where: {{ from: "{addr}" }}
        orderBy: blockTimestamp
        orderDirection: desc
        first: 50
      ) {{
        amount
        rawAmount
        blockTimestamp
        transactionHash
      }}
    }}
    """)
    return {
        "mints": data.get("mints") or [],
        "burns": data.get("burns") or [],
        "payments": data.get("payments") or [],
    }


async def get_recent_agreements(limit: int = 10) -> list:
    """Recent purchase agreements with their condition states."""
    data = await _gql(f"""
    {{
      agreements(
        orderBy: blockTimestamp
        orderDirection: desc
        first: {limit}
      ) {{
        id
        creator
        blockTimestamp
        transactionHash
        conditions {{
          conditionId
          state
          blockTimestamp
        }}
      }}
    }}
    """)
    return data.get("agreements") or []


async def get_recent_usdc_payments(limit: int = 20) -> list:
    """Recent USDC payments to the Nevermined PaymentsVault."""
    data = await _gql(f"""
    {{
      usdcpayments(
        orderBy: blockTimestamp
        orderDirection: desc
        first: {limit}
      ) {{
        from
        amount
        rawAmount
        blockTimestamp
        transactionHash
      }}
    }}
    """)
    return data.get("usdcpayments") or []


async def get_plan_summary(plan_id: str) -> dict:
    """Convenience: combine protocol stats + plan-specific burns + today's daily stats."""
    import asyncio
    proto, burns, daily = await asyncio.gather(
        get_protocol_stats(),
        get_plan_burns(plan_id, limit=10),
        get_plan_daily_stats(plan_id, days=7),
    )
    return {
        "protocol": proto,
        "recent_burns": burns,
        "daily": daily,
    }
