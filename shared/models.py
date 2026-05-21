"""
Shared data models for the App Review Insights Analyzer.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_serializer


class ReviewSource(str, Enum):
    """Enum for review sources."""
    GOOGLE_PLAY = "google_play"
    APPLE_APP_STORE = "apple_app_store"


class Review(BaseModel):
    """Model representing a single app review."""
    id: Optional[str] = None
    source: ReviewSource
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    title: str = Field(..., description="Review title")
    text: str = Field(..., description="Review content")
    date: datetime = Field(..., description="Review date")
    version: Optional[str] = Field(None, description="App version")
    processed: bool = Field(default=False, description="Whether review has been processed")
    
    @field_serializer('date')
    def serialize_date(self, date: datetime) -> str:
        return date.isoformat()


class ReviewCollection(BaseModel):
    """Model representing a collection of reviews."""
    reviews: list[Review]
    source: ReviewSource
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_count: int = Field(default=0, description="Total number of reviews")
    
    def __init__(self, **data):
        super().__init__(**data)
        self.total_count = len(self.reviews)


# ── Phase 2: Analysis models ──────────────────────────────────────────────────

class SentimentLabel(str, Enum):
    """Sentiment classification labels."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class ReviewSentiment(BaseModel):
    """Sentiment result for a single review."""
    review_id: str
    sentiment: SentimentLabel
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: Optional[str] = Field(None, description="Brief reasoning for classification")


class Theme(BaseModel):
    """A clustered theme extracted from reviews."""
    name: str = Field(..., description="Short theme label, e.g. 'App Crashes'")
    description: str = Field(..., description="One-sentence description of the theme")
    review_count: int = Field(..., ge=0, description="Number of reviews in this theme")
    sentiment: SentimentLabel = Field(..., description="Dominant sentiment for this theme")
    keywords: list[str] = Field(default_factory=list, description="Key terms for this theme")


class Quote(BaseModel):
    """A representative user quote."""
    text: str = Field(..., description="The quote text (PII-scrubbed)")
    theme_name: str = Field(..., description="Theme this quote represents")
    rating: int = Field(..., ge=1, le=5, description="Star rating of the source review")
    sentiment: SentimentLabel


class ActionItem(BaseModel):
    """An actionable improvement idea."""
    description: str = Field(..., description="What should be done")
    priority: str = Field(..., description="high / medium / low")
    theme_name: str = Field(..., description="Theme this action addresses")
    rationale: str = Field(..., description="Why this action matters")


class WeeklyInsights(BaseModel):
    """Full structured insights output for one analysis run."""
    week: str = Field(..., description="ISO week identifier, e.g. '2026-W20'")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_reviews_analysed: int
    themes: list[Theme] = Field(..., max_length=5, description="Up to 5 themes")
    quotes: list[Quote] = Field(..., max_length=3, description="Top 3 representative quotes")
    actions: list[ActionItem] = Field(..., max_length=3, description="3 actionable ideas")
    sentiment_summary: dict = Field(
        default_factory=dict,
        description="Counts: {positive: N, negative: N, neutral: N}"
    )
    doc_id: Optional[str] = Field(None, description="Google Docs document ID (Phase 3)")
    email_id: Optional[str] = Field(None, description="Gmail draft ID (Phase 4)")

    @field_serializer('generated_at')
    def serialize_generated_at(self, dt: datetime) -> str:
        return dt.isoformat()
