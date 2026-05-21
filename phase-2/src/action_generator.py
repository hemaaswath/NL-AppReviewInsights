"""
Action generator — produces 3 specific, prioritised action items from insights.
"""
import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from shared.models import ActionItem, Theme, Quote
from shared.phase2_config import DEFAULT_GROQ_MODEL
from shared.groq_throttle import wait_for_groq_slot

load_dotenv()

_SYSTEM_PROMPT = """You are a product manager generating actionable improvement ideas
from mobile app review analysis.

Given identified themes and representative quotes, generate exactly 3 specific,
implementable action items for the engineering/product team.

Rules:
- Each action must be specific (not vague like "improve UX")
- Each action must have a priority: high, medium, or low
- Each action must reference the theme it addresses
- Each action must include a brief rationale (1 sentence) citing user evidence
- Order by priority (high first)
- Respond ONLY with valid JSON array, no markdown, no extra text.

Output format:
[
  {
    "description": "Specific action to take",
    "priority": "high" | "medium" | "low",
    "theme_name": "Theme Name",
    "rationale": "One sentence citing user evidence"
  }
]"""


class ActionGenerator:
    """Generates 3 actionable improvement ideas using Groq LLM."""

    NUM_ACTIONS = 3

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.llm = ChatGroq(
            model=model,
            temperature=0.2,
            api_key=os.getenv("GROQ_API_KEY"),
            timeout=20,
            max_retries=1,
        )

    def generate(
        self,
        themes: list[Theme],
        quotes: list[Quote],
        sentiment_summary: dict,
    ) -> list[ActionItem]:
        """Generate 3 action items from themes and quotes.

        Args:
            themes: Identified themes.
            quotes: Representative quotes.
            sentiment_summary: Dict with positive/negative/neutral counts.

        Returns:
            List of exactly 3 ActionItem objects.
        """
        if not themes:
            return self._fallback_actions()

        theme_lines = []
        for t in themes:
            theme_lines.append(
                f"- {t.name} ({t.sentiment.value}, {t.review_count} reviews): {t.description}"
            )

        quote_lines = []
        for q in quotes:
            quote_lines.append(f'  [{q.rating}★] "{q.text[:150]}"')

        total = sum(sentiment_summary.values()) or 1
        neg_pct = round(sentiment_summary.get("negative", 0) / total * 100)

        prompt = (
            f"Sentiment summary: {sentiment_summary} ({neg_pct}% negative)\n\n"
            f"Themes:\n" + "\n".join(theme_lines) + "\n\n"
            f"Representative quotes:\n" + "\n".join(quote_lines) + "\n\n"
            f"Generate exactly {self.NUM_ACTIONS} action items."
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
            actions = []
            for item in data[: self.NUM_ACTIONS]:
                actions.append(ActionItem(
                    description=item["description"],
                    priority=item.get("priority", "medium"),
                    theme_name=item.get("theme_name", themes[0].name),
                    rationale=item.get("rationale", ""),
                ))
            # Pad to exactly 3 if LLM returned fewer
            while len(actions) < self.NUM_ACTIONS:
                actions.extend(self._fallback_actions()[: self.NUM_ACTIONS - len(actions)])
            return actions[: self.NUM_ACTIONS]
        except Exception as e:
            print(f"Action generation error: {e}")
            return self._fallback_actions()

    def _fallback_actions(self) -> list[ActionItem]:
        return [
            ActionItem(
                description="Investigate and fix reported app crashes on key screens.",
                priority="high",
                theme_name="App Stability",
                rationale="Multiple users report crashes preventing core functionality.",
            ),
            ActionItem(
                description="Improve customer support response time and resolution quality.",
                priority="medium",
                theme_name="Customer Support",
                rationale="Users frequently mention slow or unhelpful support responses.",
            ),
            ActionItem(
                description="Simplify the onboarding flow to reduce setup friction.",
                priority="medium",
                theme_name="Onboarding",
                rationale="New users report confusion during initial app setup.",
            ),
        ]
