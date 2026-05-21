"""
Sentiment analyser — classifies each review as positive, negative, or neutral
using the Groq LLM. Uses a single batch prompt for efficiency.
"""
import json
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from shared.models import SentimentLabel, ReviewSentiment
from shared.phase2_config import DEFAULT_GROQ_MODEL, SENTIMENT_BATCH_SIZE
from shared.groq_throttle import wait_for_groq_slot

load_dotenv()

_SYSTEM_PROMPT = """You are a sentiment analysis expert for mobile app reviews.
Classify each review as positive, negative, or neutral.

Rules:
- positive: user is satisfied, praises features, recommends the app
- negative: user is frustrated, reports bugs, requests refunds, gives low rating
- neutral: mixed feelings, factual statements, neither clearly positive nor negative
- A 1-2 star review is almost always negative; 4-5 star is almost always positive
- Respond ONLY with a valid JSON array, no markdown, no explanation outside the JSON.

Output format — one object per review, in the same order as input:
[
  {"id": "<review_id>", "sentiment": "positive"|"negative"|"neutral", "confidence": 0.0-1.0, "reasoning": "one sentence"},
  ...
]"""

_SINGLE_SYSTEM_PROMPT = """You are a sentiment analysis expert for mobile app reviews.
Classify the review as positive, negative, or neutral.

Rules:
- positive: user is satisfied, praises features, recommends the app
- negative: user is frustrated, reports bugs, requests refunds, gives low rating
- neutral: mixed feelings, factual statements, neither clearly positive nor negative
- A 1-2 star review is almost always negative; 4-5 star is almost always positive
- Respond ONLY with valid JSON, no markdown, no explanation outside the JSON.

Output format:
{"sentiment": "positive"|"negative"|"neutral", "confidence": 0.0-1.0, "reasoning": "one sentence"}"""


class SentimentAnalyser:
    """Classifies review sentiment using Groq LLM (batch mode)."""

    BATCH_SIZE = SENTIMENT_BATCH_SIZE
    MAX_TEXT_CHARS = 80

    def __init__(self, model: str = DEFAULT_GROQ_MODEL):
        self.llm = ChatGroq(
            model=model,
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY"),
            timeout=15,          # fail fast — don't hang on rate-limit stalls
            max_retries=1,
        )

    def analyse(self, review_id: str, text: str, rating: int) -> ReviewSentiment:
        """Classify a single review (used in tests / one-off calls)."""
        prompt = f"Rating: {rating}/5\nReview: {text}"
        try:
            wait_for_groq_slot()
            response = self.llm.invoke([
                SystemMessage(content=_SINGLE_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return ReviewSentiment(
                review_id=review_id,
                sentiment=SentimentLabel(data["sentiment"]),
                confidence=float(data.get("confidence", 0.8)),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            return self._fallback(review_id, rating, str(e))

    def analyse_batch(self, reviews: list[dict]) -> list[ReviewSentiment]:
        """Classify a list of reviews using batched LLM calls.

        Args:
            reviews: List of dicts with keys: id, text, rating.

        Returns:
            List of ReviewSentiment objects in the same order.
        """
        if not reviews:
            return []

        results: list[ReviewSentiment] = []
        total = len(reviews)

        for batch_start in range(0, total, self.BATCH_SIZE):
            batch = reviews[batch_start: batch_start + self.BATCH_SIZE]
            batch_results = self._analyse_batch_chunk(batch)
            results.extend(batch_results)
            print(f"  Sentiment: {min(batch_start + self.BATCH_SIZE, total)}/{total} done")

        return results

    def _analyse_batch_chunk(self, batch: list[dict]) -> list[ReviewSentiment]:
        """Send one batch of reviews to the LLM and parse results."""
        lines = []
        for r in batch:
            text = (r.get("text") or "")[:self.MAX_TEXT_CHARS]
            lines.append(f'{{"id": "{r["id"]}", "rating": {r.get("rating", 3)}, "text": "{text}"}}')

        prompt = "Classify these reviews:\n[\n" + ",\n".join(lines) + "\n]"

        try:
            wait_for_groq_slot()
            response = self.llm.invoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)

            # Build a map by id for safe lookup
            result_map = {item["id"]: item for item in data if "id" in item}
            results = []
            for r in batch:
                item = result_map.get(r["id"])
                if item:
                    results.append(ReviewSentiment(
                        review_id=r["id"],
                        sentiment=SentimentLabel(item.get("sentiment", "neutral")),
                        confidence=float(item.get("confidence", 0.8)),
                        reasoning=item.get("reasoning", ""),
                    ))
                else:
                    results.append(self._fallback(r["id"], r.get("rating", 3), "missing from response"))
            return results

        except Exception as e:
            # Fall back to rating-based classification for the whole batch
            return [self._fallback(r["id"], r.get("rating", 3), str(e)) for r in batch]

    def _fallback(self, review_id: str, rating: int, reason: str) -> ReviewSentiment:
        if rating >= 4:
            sentiment = SentimentLabel.POSITIVE
        elif rating <= 2:
            sentiment = SentimentLabel.NEGATIVE
        else:
            sentiment = SentimentLabel.NEUTRAL
        return ReviewSentiment(
            review_id=review_id,
            sentiment=sentiment,
            confidence=0.6,
            reasoning=f"Fallback from rating (error: {reason})",
        )

