"""
Theme clusterer — groups reviews into up to 5 coherent themes using Groq LLM.
"""
import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from shared.models import Theme, SentimentLabel
from shared.phase2_config import DEFAULT_GROQ_MODEL
from shared.groq_throttle import wait_for_groq_slot

load_dotenv()

_SYSTEM_PROMPT = """You are a product analyst specialising in mobile app review analysis.
Given a list of app reviews, identify the top recurring themes (maximum 5).

Rules:
- Themes must be distinct and non-overlapping
- Each theme must have a short name (2-4 words), a one-sentence description,
  an approximate review count, dominant sentiment, and 3-5 keywords
- Order themes by frequency (most common first)
- Respond ONLY with valid JSON array, no markdown, no extra text.

Output format (array of theme objects):
[
  {
    "name": "Theme Name",
    "description": "One sentence describing what users say about this.",
    "review_count": <integer>,
    "sentiment": "positive" | "negative" | "neutral",
    "keywords": ["word1", "word2", "word3"]
  }
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
            themes = []
            for item in data[: self.MAX_THEMES]:
                themes.append(Theme(
                    name=item["name"],
                    description=item["description"],
                    review_count=int(item.get("review_count", 0)),
                    sentiment=SentimentLabel(item.get("sentiment", "neutral")),
                    keywords=item.get("keywords", []),
                ))
            return themes
        except Exception as e:
            print(f"Theme clustering error: {e}")
            # Fallback: single generic theme
            return [Theme(
                name="General Feedback",
                description="Mixed user feedback about the app.",
                review_count=len(reviews),
                sentiment=SentimentLabel.NEUTRAL,
                keywords=["app", "feedback"],
            )]
