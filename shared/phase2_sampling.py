"""
Stratified sampling for Phase 2 — cap corpus size while preserving rating mix.
"""
import random
from collections import defaultdict
from typing import Optional


def stratified_sample(
    reviews: list[dict],
    max_size: int,
    seed: Optional[int] = 42,
) -> list[dict]:
    """
    Sample up to max_size reviews with proportional representation per star rating.

    Args:
        reviews: Review dicts with at least 'rating' key.
        max_size: Maximum reviews to return.
        seed: RNG seed for reproducible weekly runs.

    Returns:
        Subset of reviews (all if len(reviews) <= max_size).
    """
    if len(reviews) <= max_size:
        return list(reviews)

    rng = random.Random(seed)
    by_rating: dict[int, list[dict]] = defaultdict(list)
    for review in reviews:
        rating = int(review.get("rating") or 3)
        rating = min(5, max(1, rating))
        by_rating[rating].append(review)

    total = len(reviews)
    selected: list[dict] = []
    quotas: dict[int, int] = {}
    allocated = 0

    for rating, bucket in by_rating.items():
        share = len(bucket) / total
        count = int(max_size * share)
        quotas[rating] = count
        allocated += count

    remainder = max_size - allocated
    ratings_sorted = sorted(by_rating.keys(), key=lambda r: len(by_rating[r]), reverse=True)
    for rating in ratings_sorted:
        if remainder <= 0:
            break
        quotas[rating] = quotas.get(rating, 0) + 1
        remainder -= 1

    for rating, bucket in by_rating.items():
        take = min(quotas.get(rating, 0), len(bucket))
        if take > 0:
            selected.extend(rng.sample(bucket, take))

    if len(selected) < max_size:
        remaining = [r for r in reviews if r not in selected]
        need = max_size - len(selected)
        if remaining:
            selected.extend(rng.sample(remaining, min(need, len(remaining))))

    return selected[:max_size]
