"""
Theme clusterer — groups reviews into up to 5 coherent themes using Groq LLM.
"""
import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from shared.models import Theme, SentimentLabel
from shared.groq_throttle import wait_for_groq_slot
from shared.groww_product_map import (
    cluster_by_keywords,
    normalize_themes_from_llm,
    product_map_prompt_block,
)

load_dotenv()

_SYSTEM_PROMPT = f"""You are a product analyst for Groww, an Indian fintech investment app.
Group Play Store reviews into Groww product areas (maximum 5 areas with clear signal).

{product_map_prompt_block()}

Rules:
- Each theme "name" MUST be one of the exact product-area strings listed above
- review_count = approximate number of reviews mentioning that area (sum ≤ total reviews)
- Order by review_count descending
- Respond ONLY with valid JSON array, no markdown, no extra text.

Output format (array of theme objects):
[
  {{
    "name": "Stocks & F&O",
    "description": "One sentence describing what users say about this area.",
    "review_count": <integer>,
    "sentiment": "positive" | "negative" | "neutral",
    "keywords": ["word1", "word2", "word3"]
  }}
]"""


class ThemeClusterer:
    """Clusters reviews into themes using Groq LLM."""

    MAX_THEMES = 5
    # Max chars of review text to send per review to stay within token limits
    MAX_REVIEW_CHARS = 100

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.llm = ChatGroq(
            model=model,
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY"),
            timeout=20,
            max_retries=1,
        )

    def _build_review_digest(self, reviews: list[dict]) -> str:
        """Build a compact text digest of reviews for the prompt."""
        lines = []
        for i, r in enumerate(reviews, 1):
            text = (r.get("text") or "")[:self.MAX_REVIEW_CHARS]
            lines.append(f"{i}. [{r.get('rating', '?')}★] {text}")
        return "\n".join(lines)

    def cluster(self, reviews: list[dict]) -> list[Theme]:
        """Identify themes from a list of review dicts.

        Args:
            reviews: List of dicts with keys: id, text, rating.

        Returns:
            List of Theme objects (max 5).
        """
        if not reviews:
            return []

        digest = self._build_review_digest(reviews)
        prompt = (
            f"Total reviews: {len(reviews)}\n\n"
            f"Reviews:\n{digest}\n\n"
            f"Identify up to {self.MAX_THEMES} themes."
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
            if not isinstance(data, list):
                raise ValueError("Expected JSON array")
            themes = normalize_themes_from_llm(data[: self.MAX_THEMES], len(reviews))
            if themes:
                return themes
            return cluster_by_keywords(reviews, self.MAX_THEMES)
        except Exception as e:
            print(f"Theme clustering error: {e}")
            return cluster_by_keywords(reviews, self.MAX_THEMES)
