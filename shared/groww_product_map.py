"""
Groww fintech product-area taxonomy for review theme clustering.
"""
from __future__ import annotations

from typing import Iterable

from shared.models import SentimentLabel, Theme

# Canonical areas (order = default display priority)
GROWW_PRODUCT_AREAS: list[str] = [
    "KYC & Onboarding",
    "Payments & UPI",
    "Mutual Funds & SIP",
    "Stocks & F&O",
    "Withdrawals & Settlement",
    "Charts & UX",
    "Fees & Pricing",
    "Customer Support",
    "Trust & Fraud",
]

# Keywords per area (lowercase); used for fallback clustering
AREA_KEYWORDS: dict[str, list[str]] = {
    "KYC & Onboarding": [
        "kyc", "onboard", "signup", "sign up", "pan", "aadhaar", "verify", "verification",
        "register", "account open",
    ],
    "Payments & UPI": [
        "upi", "payment", "pay", "add money", "deposit", "bank", "transfer", "neft", "imps",
    ],
    "Mutual Funds & SIP": [
        "mutual", "sip", "nav", "expense ratio", "mf ", "fund", "elss", "portfolio",
    ],
    "Stocks & F&O": [
        "stock", "share", "fno", "f&o", "option", "future", "commodity", "demat", "trading",
        "brokerage", "order", "intraday", "nifty", "sensex",
    ],
    "Withdrawals & Settlement": [
        "withdraw", "withdrawal", "payout", "settlement", "not received", "stuck", "pending",
        "transfer out", "money back",
    ],
    "Charts & UX": [
        "chart", "candle", "ui", "ux", "lag", "slow", "crash", "freeze", "navigation", "design",
        "dark mode", "screen", "interface",
    ],
    "Fees & Pricing": [
        "fee", "charge", "brokerage", "amc", "pricing", "cost", "expensive", "deduct",
    ],
    "Customer Support": [
        "support", "customer care", "help", "call", "chat", "ticket", "response", "resolve",
    ],
    "Trust & Fraud": [
        "fraud", "scam", "cheat", "unauthorized", "stolen", "fake", "illegal", "complaint",
        "sebi", "regulator",
    ],
}

_AREA_ALIASES: dict[str, str] = {
    "onboarding": "KYC & Onboarding",
    "kyc": "KYC & Onboarding",
    "payments": "Payments & UPI",
    "upi": "Payments & UPI",
    "mutual funds": "Mutual Funds & SIP",
    "sip": "Mutual Funds & SIP",
    "stocks": "Stocks & F&O",
    "trading": "Stocks & F&O",
    "withdrawals": "Withdrawals & Settlement",
    "withdrawal": "Withdrawals & Settlement",
    "charts": "Charts & UX",
    "ux": "Charts & UX",
    "ui": "Charts & UX",
    "fees": "Fees & Pricing",
    "support": "Customer Support",
    "fraud": "Trust & Fraud",
    "trust": "Trust & Fraud",
}


def product_map_prompt_block() -> str:
    """LLM instruction block listing allowed theme names."""
    lines = ["Use ONLY these exact product-area names (pick up to 5 with non-zero volume):"]
    for i, area in enumerate(GROWW_PRODUCT_AREAS, 1):
        hints = ", ".join(AREA_KEYWORDS[area][:6])
        lines.append(f'{i}. "{area}" — e.g. {hints}')
    return "\n".join(lines)


def normalize_area_name(name: str) -> str | None:
    """Map free-text or LLM theme name to a canonical product area."""
    if not name:
        return None
    raw = name.strip()
    for area in GROWW_PRODUCT_AREAS:
        if area.lower() == raw.lower():
            return area
    low = raw.lower()
    for alias, area in _AREA_ALIASES.items():
        if alias in low:
            return area
    for area in GROWW_PRODUCT_AREAS:
        if area.split("&")[0].strip().lower() in low:
            return area
        for kw in AREA_KEYWORDS[area]:
            if kw in low:
                return area
    return None


def _rating_sentiment(rating: int) -> SentimentLabel:
    if rating >= 4:
        return SentimentLabel.POSITIVE
    if rating <= 2:
        return SentimentLabel.NEGATIVE
    return SentimentLabel.NEUTRAL


def cluster_by_keywords(reviews: list[dict], max_themes: int = 5) -> list[Theme]:
    """Fallback: assign reviews to product areas by keyword hits."""
    counts: dict[str, int] = {a: 0 for a in GROWW_PRODUCT_AREAS}
    sent_scores: dict[str, list[int]] = {a: [] for a in GROWW_PRODUCT_AREAS}

    for r in reviews:
        blob = f"{r.get('title', '')} {r.get('text', '')}".lower()
        rating = int(r.get("rating") or 3)
        matched = False
        for area, keywords in AREA_KEYWORDS.items():
            if any(kw in blob for kw in keywords):
                counts[area] += 1
                sent_scores[area].append(rating)
                matched = True
                break
        if not matched:
            counts["Charts & UX"] += 1
            sent_scores["Charts & UX"].append(rating)

    ranked = sorted(
        ((a, counts[a]) for a in GROWW_PRODUCT_AREAS if counts[a] > 0),
        key=lambda x: x[1],
        reverse=True,
    )[:max_themes]

    themes: list[Theme] = []
    for area, count in ranked:
        ratings = sent_scores[area]
        avg = sum(ratings) / len(ratings) if ratings else 3
        if avg >= 3.5:
            sent = SentimentLabel.POSITIVE
        elif avg <= 2.5:
            sent = SentimentLabel.NEGATIVE
        else:
            sent = SentimentLabel.NEUTRAL
        themes.append(
            Theme(
                name=area,
                description=f"User feedback about {area.lower()}.",
                review_count=count,
                sentiment=sent,
                keywords=AREA_KEYWORDS[area][:5],
            )
        )
    if not themes:
        return [
            Theme(
                name="Charts & UX",
                description="General app experience feedback.",
                review_count=len(reviews),
                sentiment=SentimentLabel.NEUTRAL,
                keywords=["app", "experience"],
            )
        ]
    return themes


def normalize_themes_from_llm(items: Iterable[dict], total_reviews: int) -> list[Theme]:
    """Merge LLM theme rows onto canonical product-area names."""
    merged: dict[str, dict] = {}
    for item in items:
        raw_name = item.get("name", "")
        area = normalize_area_name(raw_name) or raw_name
        if area not in GROWW_PRODUCT_AREAS:
            continue
        count = int(item.get("review_count", 0))
        if area not in merged:
            merged[area] = {
                "review_count": 0,
                "descriptions": [],
                "sentiment": item.get("sentiment", "neutral"),
                "keywords": item.get("keywords", []),
            }
        merged[area]["review_count"] += count
        if item.get("description"):
            merged[area]["descriptions"].append(item["description"])
        merged[area]["keywords"] = list(
            dict.fromkeys(merged[area]["keywords"] + item.get("keywords", []))
        )[:5]

    themes: list[Theme] = []
    for area, data in sorted(merged.items(), key=lambda x: x[1]["review_count"], reverse=True):
        try:
            sent = SentimentLabel(data["sentiment"])
        except ValueError:
            sent = SentimentLabel.NEUTRAL
        desc = data["descriptions"][0] if data["descriptions"] else f"Feedback on {area}."
        themes.append(
            Theme(
                name=area,
                description=desc,
                review_count=data["review_count"],
                sentiment=sent,
                keywords=data["keywords"] or AREA_KEYWORDS[area][:5],
            )
        )
    return themes[:5]


def themes_to_area_counts(themes: list[dict]) -> dict[str, int]:
    """Full product-map counts for dashboard (includes zero areas)."""
    counts = {a: 0 for a in GROWW_PRODUCT_AREAS}
    for t in themes:
        name = t.get("name", "")
        area = normalize_area_name(name) or name
        if area in counts:
            counts[area] += int(t.get("review_count", 0))
    return counts
