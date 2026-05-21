"""
Quote extractor — picks the 3 most representative user quotes across all themes.
"""
import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from shared.models import Quote, Theme, SentimentLabel
from shared.phase2_config import DEFAULT_GROQ_MODEL, PHASE2_QUOTE_SAMPLE_SIZE
from shared.groq_throttle import wait_for_groq_slot

load_dotenv()

_SYSTEM_PROMPT = """You are a UX researcher selecting representative user quotes from app reviews.
Given a list of reviews and identified themes, select exactly 3 quotes that best represent
the most important user feedback.

Rules:
- Each quote must come verbatim from one of the provided reviews (do not paraphrase)
- Each quote must be assigned to the most relevant theme
- Prefer quotes that are specific, vivid, and actionable (not vague)
- Cover different themes if possible
- Respond ONLY with valid JSON array, no markdown, no extra text.

Output format:
[
  {
    "text": "exact quote from review",
    "theme_name": "Theme Name",
    "rating": <1-5>,
    "sentiment": "positive" | "negative" | "neutral"
  }
]"""


class QuoteExtractor:
    """Extracts top 3 representative quotes using Groq LLM."""

    MAX_QUOTES = 3
    MAX_REVIEW_CHARS = 120
    MAX_REVIEWS_IN_PROMPT = PHASE2_QUOTE_SAMPLE_SIZE

    def __init__(self, model: str = DEFAULT_GROQ_MODEL):
        self.llm = ChatGroq(
            model=model,
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY"),
            timeout=20,
            max_retries=1,
        )

    def extract(self, reviews: list[dict], themes: list[Theme]) -> list[Quote]:
        """Extract top 3 representative quotes.

        Args:
            reviews: List of review dicts (id, text, rating).
            themes: Identified themes from ThemeClusterer.

        Returns:
            List of up to 3 Quote objects.
        """
        if not reviews:
            return []

        theme_names = [t.name for t in themes] if themes else ["General Feedback"]

        review_lines = []
        for i, r in enumerate(reviews[:self.MAX_REVIEWS_IN_PROMPT], 1):  # cap to stay within tokens
            text = (r.get("text") or "")[:self.MAX_REVIEW_CHARS]
            review_lines.append(f"{i}. [{r.get('rating', '?')}★] {text}")

        prompt = (
            f"Themes: {', '.join(theme_names)}\n\n"
            f"Reviews:\n" + "\n".join(review_lines) +
            f"\n\nSelect exactly {self.MAX_QUOTES} representative quotes."
        )

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
            quotes = []
            for item in data[: self.MAX_QUOTES]:
                quotes.append(Quote(
                    text=item["text"],
                    theme_name=item.get("theme_name", theme_names[0]),
                    rating=int(item.get("rating", 3)),
                    sentiment=SentimentLabel(item.get("sentiment", "neutral")),
                ))
            return quotes
        except Exception as e:
            print(f"Quote extraction error: {e}")
            # Fallback: pick first 3 reviews with non-empty text
            fallback = []
            for r in reviews:
                if r.get("text") and len(fallback) < self.MAX_QUOTES:
                    rating = r.get("rating", 3)
                    sentiment = (
                        SentimentLabel.POSITIVE if rating >= 4
                        else SentimentLabel.NEGATIVE if rating <= 2
                        else SentimentLabel.NEUTRAL
                    )
                    fallback.append(Quote(
                        text=r["text"][:200],
                        theme_name=theme_names[0],
                        rating=rating,
                        sentiment=sentiment,
                    ))
            return fallback
