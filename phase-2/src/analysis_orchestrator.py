"""
Orchestrator for Phase 2: Analysis Engine.

Loads unprocessed reviews from the database, runs sentiment analysis,
theme clustering, quote extraction, and action generation, then stores
the structured WeeklyInsights back to the database.
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv

from shared.database import DatabaseManager
from shared.models import WeeklyInsights, SentimentLabel, ReviewSentiment
from shared.pii_scrubber import scrub_review_dict
from shared.phase2_config import (
    DEFAULT_GROQ_MODEL,
    PHASE2_LLM_SENTIMENT_MAX,
    PHASE2_MAX_REVIEWS,
    PHASE2_QUOTE_SAMPLE_SIZE,
    PHASE2_THEME_SAMPLE_SIZE,
)
from shared.phase2_sampling import stratified_sample

from sentiment_analyser import SentimentAnalyser
from theme_clusterer import ThemeClusterer
from quote_extractor import QuoteExtractor
from action_generator import ActionGenerator

load_dotenv()


def _current_week() -> str:
    """Return ISO week string e.g. '2026-W20'."""
    now = datetime.now(timezone.utc)
    return f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"


class AnalysisOrchestrator:
    """Runs the full Phase 2 analysis pipeline."""

    def __init__(
        self,
        database_path: Optional[str] = None,
        model: Optional[str] = None,
    ):
        load_dotenv()
        model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        self.database_path = database_path or os.getenv("DATABASE_PATH", "data/reviews.db")
        self.db = DatabaseManager(self.database_path)
        self.sentiment_analyser = SentimentAnalyser(model=model)
        self.theme_clusterer = ThemeClusterer(model=model)
        self.quote_extractor = QuoteExtractor(model=model)
        self.action_generator = ActionGenerator(model=model)

    def run(
        self,
        week: Optional[str] = None,
        max_reviews: Optional[int] = None,
        mark_processed: bool = True,
    ) -> WeeklyInsights:
        """Run the full analysis pipeline.

        Args:
            week: Week identifier (defaults to current ISO week).
            max_reviews: Cap on reviews to analyse (None = PHASE2_MAX_REVIEWS from env).
            mark_processed: Whether to mark reviews as processed after analysis.

        Returns:
            WeeklyInsights: Structured insights object.
        """
        week = week or _current_week()
        cap = max_reviews if max_reviews is not None else PHASE2_MAX_REVIEWS

        print(f"\n{'='*60}")
        print(f"Phase 2 Analysis — {week}")
        print(f"{'='*60}")

        # ── 1. Load reviews ───────────────────────────────────────────────────
        reviews = self.db.get_unprocessed_reviews()
        if not reviews:
            reviews = self.db.get_reviews_by_source("google_play")
            reviews += self.db.get_reviews_by_source("apple_app_store")

        reviews = [scrub_review_dict(r) for r in reviews]
        if len(reviews) > cap:
            before = len(reviews)
            reviews = stratified_sample(reviews, cap)
            print(f"Reviews loaded: {before} → stratified sample: {len(reviews)} (cap {cap})")
        else:
            print(f"Reviews loaded: {len(reviews)}")

        if not reviews:
            return self._empty_insights(week)

        theme_reviews = stratified_sample(reviews, min(PHASE2_THEME_SAMPLE_SIZE, len(reviews)))

        # ── 2. Sentiment analysis ─────────────────────────────────────────────
        print("\n[1/4] Running sentiment analysis...")
        if len(reviews) > PHASE2_LLM_SENTIMENT_MAX:
            sentiments = self._sentiment_from_ratings(reviews)
            print(f"  Mode: rating-based (>{PHASE2_LLM_SENTIMENT_MAX} reviews — saves Groq quota)")
        else:
            sentiments = self.sentiment_analyser.analyse_batch(reviews)
            print("  Mode: LLM batch")

        sentiment_map = {s.review_id: s for s in sentiments}
        summary = {
            SentimentLabel.POSITIVE.value: 0,
            SentimentLabel.NEGATIVE.value: 0,
            SentimentLabel.NEUTRAL.value: 0,
        }
        for s in sentiments:
            summary[s.sentiment.value] += 1

        print(f"  Positive: {summary['positive']}  "
              f"Negative: {summary['negative']}  "
              f"Neutral: {summary['neutral']}")

        # ── 3. Theme clustering ───────────────────────────────────────────────
        print(f"\n[2/4] Clustering themes ({len(theme_reviews)}-review LLM digest)...")
        themes = self.theme_clusterer.cluster(theme_reviews)
        print(f"  Themes identified: {len(themes)}")
        for t in themes:
            print(f"    • {t.name} ({t.review_count} reviews, {t.sentiment.value})")

        # ── 4. Quote extraction ───────────────────────────────────────────────
        print("\n[3/4] Extracting representative quotes...")
        quote_reviews = stratified_sample(reviews, min(PHASE2_QUOTE_SAMPLE_SIZE, len(reviews)))
        quotes = self.quote_extractor.extract(quote_reviews, themes)
        print(f"  Quotes extracted: {len(quotes)}")

        # ── 5. Action generation ──────────────────────────────────────────────
        print("\n[4/4] Generating action items...")
        actions = self.action_generator.generate(themes, quotes, summary)
        print(f"  Actions generated: {len(actions)}")
        for a in actions:
            print(f"    [{a.priority.upper()}] {a.description[:70]}")

        # ── 6. Build WeeklyInsights ───────────────────────────────────────────
        insights = WeeklyInsights(
            week=week,
            total_reviews_analysed=len(reviews),
            themes=themes,
            quotes=quotes,
            actions=actions,
            sentiment_summary=summary,
        )

        # ── 7. Persist to DB ──────────────────────────────────────────────────
        insights_dict = insights.model_dump(mode="json")
        self.db.save_insights(insights_dict)
        print(f"\nInsights saved to DB for week {week}")

        # ── 8. Mark reviews as processed ─────────────────────────────────────
        if mark_processed:
            for r in reviews:
                self.db.mark_review_as_processed(r["id"])
            print(f"Marked {len(reviews)} reviews as processed")

        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*60}\n")

        return insights

    @staticmethod
    def _sentiment_from_ratings(reviews: list[dict]) -> list[ReviewSentiment]:
        """Derive sentiment from star ratings (no Groq calls)."""
        results: list[ReviewSentiment] = []
        for review in reviews:
            rating = int(review.get("rating") or 3)
            if rating >= 4:
                label = SentimentLabel.POSITIVE
            elif rating <= 2:
                label = SentimentLabel.NEGATIVE
            else:
                label = SentimentLabel.NEUTRAL
            results.append(
                ReviewSentiment(
                    review_id=review["id"],
                    sentiment=label,
                    confidence=0.75,
                    reasoning="Derived from star rating (Groq skipped for scale).",
                )
            )
        return results

    def _empty_insights(self, week: str) -> WeeklyInsights:
        """Return an empty insights object when no reviews are available."""
        print("No reviews available for analysis.")
        return WeeklyInsights(
            week=week,
            total_reviews_analysed=0,
            themes=[],
            quotes=[],
            actions=[],
            sentiment_summary={"positive": 0, "negative": 0, "neutral": 0},
        )

    def get_insights_json(self, week: Optional[str] = None) -> str:
        """Retrieve stored insights as a formatted JSON string.

        Args:
            week: Week identifier, or None for latest.

        Returns:
            str: Pretty-printed JSON.
        """
        data = self.db.get_insights(week)
        if not data:
            return json.dumps({"error": "No insights found"}, indent=2)
        return json.dumps(data, indent=2, default=str)

    def close(self):
        self.db.close()


def main():
    """Entry point for Phase 2."""
    orchestrator = AnalysisOrchestrator()
    insights = orchestrator.run()
    print(orchestrator.get_insights_json())
    orchestrator.close()
    return insights


if __name__ == "__main__":
    main()
