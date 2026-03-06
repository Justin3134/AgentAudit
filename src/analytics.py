"""Shared in-memory analytics store.

Imported by both seller.py (records paid API calls) and chat.py
(records fallback/direct calls so the dashboard sidebar stays accurate).
"""

from datetime import datetime, timezone

_store = {
    "total_audits": 0,
    "total_compares": 0,
    "total_monitors": 0,
    "total_datas": 0,
    "total_revenue_credits": 0,
    "unique_callers": set(),
    "transactions": [],
    # Buyer-side spend tracking
    "total_purchases": 0,
    "total_spent_credits": 0,
    "vendors_bought_from": set(),
    "purchase_history": [],
    # ROI tracking
    "roi_decisions": {"BUY": 0, "WATCH": 0, "AVOID": 0, "SWITCH": 0},
    # ZeroClick ad funnel tracking
    "zeroclick_ads_served": 0,
    "zeroclick_impressions": 0,
    "zeroclick_conversions": 0,
    "zeroclick_revenue_driven": 0,
    "zeroclick_ad_log": [],
    # Sponsor tool usage counters
    "tools": {
        "openai":     {"calls": 0, "status": "active", "last_used": None},
        "exa":        {"calls": 0, "status": "active", "last_used": None},
        "nevermined": {"calls": 0, "status": "active", "last_used": None},
        "zeroclick":  {"calls": 0, "status": "pending_approval", "last_used": None},
    },
}


def record_sale(endpoint: str, credits: int, caller: str = "unknown", payment_method: str = "nevermined"):
    """Record an incoming sale (seller side)."""
    name = endpoint.strip("/")
    key = f"total_{name}s"
    if key in _store:
        _store[key] += 1
    _store["total_revenue_credits"] += credits
    _store["unique_callers"].add(caller)
    _store["transactions"].append({
        "type": "sale",
        "endpoint": endpoint,
        "credits": credits,
        "caller": caller,
        "payment_method": payment_method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def record_purchase(
    vendor: str,
    endpoint: str,
    credits: int,
    score: float = 0.0,
    recommendation: str = "",
    payment_method: str = "nevermined",
    session_id: str = "",
):
    """Record an outgoing purchase (buyer side)."""
    _store["total_purchases"] += 1
    _store["total_spent_credits"] += credits
    _store["vendors_bought_from"].add(vendor)
    entry = {
        "type": "purchase",
        "vendor": vendor,
        "endpoint": endpoint,
        "credits": credits,
        "score": score,
        "recommendation": recommendation,
        "payment_method": payment_method,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _store["purchase_history"].append(entry)
    if recommendation in _store["roi_decisions"]:
        _store["roi_decisions"][recommendation] += 1
    return entry


def record_zeroclick_ad_served(ad: dict, audited_url: str, audit_score: float):
    """Record that a ZeroClick ad was served in a seller response."""
    _store["zeroclick_ads_served"] += 1
    _store["zeroclick_ad_log"].append({
        "type": "served",
        "sponsor": ad.get("sponsor", "Unknown"),
        "message": ad.get("message", ""),
        "audited_url": audited_url,
        "audit_score": audit_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def record_zeroclick_impression(ad: dict, audited_url: str, audit_score: float):
    """Record that a buyer agent received and processed a ZeroClick ad."""
    _store["zeroclick_impressions"] += 1
    _store["zeroclick_ad_log"].append({
        "type": "impression",
        "sponsor": ad.get("sponsor", "Unknown"),
        "message": ad.get("message", ""),
        "endpoint_url": ad.get("click_url") or ad.get("endpoint_url", ""),
        "audited_url": audited_url,
        "audit_score": audit_score,
        "converted": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def record_zeroclick_conversion(ad: dict, credits: int, audited_url: str):
    """Record that a buyer agent purchased a service driven by a ZeroClick ad."""
    _store["zeroclick_conversions"] += 1
    _store["zeroclick_revenue_driven"] += credits
    # Mark the most recent matching impression as converted
    for entry in reversed(_store["zeroclick_ad_log"]):
        if entry.get("type") == "impression" and not entry.get("converted"):
            if entry.get("sponsor") == ad.get("sponsor"):
                entry["converted"] = True
                break
    _store["zeroclick_ad_log"].append({
        "type": "conversion",
        "sponsor": ad.get("sponsor", "Unknown"),
        "endpoint_url": ad.get("endpoint_url", ""),
        "audited_url": audited_url,
        "credits": credits,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def record_tool_call(tool: str, status: str = "ok"):
    """Track a sponsor tool API call."""
    if tool in _store["tools"]:
        _store["tools"][tool]["calls"] += 1
        _store["tools"][tool]["last_used"] = datetime.now(timezone.utc).isoformat()
        if status == "ok" and _store["tools"][tool]["status"] not in ("pending_approval",):
            _store["tools"][tool]["status"] = "active"
        elif status == "error":
            _store["tools"][tool]["status"] = "error"
        elif status == "pending":
            _store["tools"][tool]["status"] = "pending_approval"


def get_stats() -> dict:
    return {
        "seller": {
            "total_audits": _store["total_audits"],
            "total_compares": _store["total_compares"],
            "total_monitors": _store["total_monitors"],
            "total_datas": _store["total_datas"],
            "total_revenue_credits": _store["total_revenue_credits"],
            "unique_buyers": len(_store["unique_callers"]),
            "transactions": list(reversed(_store["transactions"][-20:])),
        },
        "buyer": {
            "total_purchases": _store["total_purchases"],
            "total_spent_credits": _store["total_spent_credits"],
            "vendors_count": len(_store["vendors_bought_from"]),
            "vendors": list(_store["vendors_bought_from"]),
            "roi_decisions": dict(_store["roi_decisions"]),
            "purchase_history": list(reversed(_store["purchase_history"][-20:])),
        },
        "zeroclick": {
            "ads_served": _store["zeroclick_ads_served"],
            "impressions": _store["zeroclick_impressions"],
            "conversions": _store["zeroclick_conversions"],
            "conversion_rate": round(
                _store["zeroclick_conversions"] / max(_store["zeroclick_impressions"], 1), 3
            ),
            "revenue_driven": _store["zeroclick_revenue_driven"],
            "recent": list(reversed(_store["zeroclick_ad_log"][-10:])),
        },
        "tools": {k: dict(v) for k, v in _store["tools"].items()},
    }
