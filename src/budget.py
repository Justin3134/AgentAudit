"""Budget tracking and enforcement for the buyer agent."""

import threading
from datetime import datetime, timezone


class Budget:
    def __init__(
        self,
        max_daily: int = 100,
        max_per_request: int = 10,
        max_vendor_percent: float = 0.4,
    ):
        self.max_daily = max_daily
        self.max_per_request = max_per_request
        self.max_vendor_percent = max_vendor_percent
        self._lock = threading.Lock()
        self._daily_spent = 0
        self._daily_date = datetime.now(timezone.utc).date()
        self._total_spent = 0
        self._vendor_spend: dict[str, int] = {}
        self._purchases: list[dict] = []

    def _reset_if_new_day(self):
        today = datetime.now(timezone.utc).date()
        if today != self._daily_date:
            self._daily_spent = 0
            self._daily_date = today

    def can_spend(self, credits: int, vendor: str = "") -> tuple[bool, str]:
        with self._lock:
            self._reset_if_new_day()

            if self.max_per_request > 0 and credits > self.max_per_request:
                return False, f"Exceeds per-request limit ({credits} > {self.max_per_request})"

            if self.max_daily > 0 and self._daily_spent + credits > self.max_daily:
                return False, f"Would exceed daily limit ({self._daily_spent + credits} > {self.max_daily})"

            if vendor and self.max_vendor_percent > 0 and self._total_spent > 0:
                vendor_total = self._vendor_spend.get(vendor, 0) + credits
                if vendor_total / (self._total_spent + credits) > self.max_vendor_percent:
                    return False, (
                        f"Would exceed vendor concentration limit "
                        f"({self.max_vendor_percent*100:.0f}% max for {vendor})"
                    )

            return True, "OK"

    def record_purchase(self, credits: int, vendor: str, query: str = "", reason: str = ""):
        with self._lock:
            self._reset_if_new_day()
            self._daily_spent += credits
            self._total_spent += credits
            self._vendor_spend[vendor] = self._vendor_spend.get(vendor, 0) + credits
            self._purchases.append({
                "credits": credits,
                "vendor": vendor,
                "query": query,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def get_status(self) -> dict:
        with self._lock:
            self._reset_if_new_day()
            return {
                "daily_limit": self.max_daily,
                "daily_spent": self._daily_spent,
                "daily_remaining": max(0, self.max_daily - self._daily_spent) if self.max_daily > 0 else "unlimited",
                "total_spent": self._total_spent,
                "total_purchases": len(self._purchases),
                "vendor_breakdown": dict(self._vendor_spend),
                "recent_purchases": self._purchases[-10:],
                "max_vendor_percent": self.max_vendor_percent,
            }

    def get_vendor_spend(self, vendor: str) -> int:
        with self._lock:
            return self._vendor_spend.get(vendor, 0)
