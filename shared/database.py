"""
Database schema and connection management for the App Review Insights Analyzer.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from contextlib import contextmanager
import os

from shared.db_paths import resolve_database_path, sqlite_url

Base = declarative_base()


class ReviewModel(Base):
    """SQLAlchemy model for storing app reviews."""
    __tablename__ = "reviews"
    
    id = Column(String, primary_key=True)
    source = Column(String, nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    version = Column(String, nullable=True)
    processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "source": self.source,
            "rating": self.rating,
            "title": self.title,
            "text": self.text,
            "date": self.date.isoformat() if self.date else None,
            "version": self.version,
            "processed": self.processed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class InsightsModel(Base):
    """SQLAlchemy model for storing weekly analysis insights."""
    __tablename__ = "insights"

    id = Column(String, primary_key=True)          # week identifier e.g. "2026-W20"
    week = Column(String, nullable=False, index=True)
    generated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    total_reviews_analysed = Column(Integer, nullable=False, default=0)
    themes = Column(JSON, nullable=False, default=list)
    quotes = Column(JSON, nullable=False, default=list)
    actions = Column(JSON, nullable=False, default=list)
    sentiment_summary = Column(JSON, nullable=False, default=dict)
    doc_id = Column(String, nullable=True)
    email_id = Column(String, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "week": self.week,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "total_reviews_analysed": self.total_reviews_analysed,
            "themes": self.themes,
            "quotes": self.quotes,
            "actions": self.actions,
            "sentiment_summary": self.sentiment_summary,
            "doc_id": self.doc_id,
            "email_id": self.email_id,
        }


class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self, database_path: str | None = None):
        """Initialize database manager.
        
        Args:
            database_path: Path to the SQLite database file (resolved for cloud)
        """
        self.database_path = resolve_database_path(database_path)
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection and create tables."""
        self.engine = create_engine(
            sqlite_url(self.database_path),
            echo=False,
            connect_args={"check_same_thread": False},
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session context manager.
        
        Yields:
            Session: SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_review(self, review_data: dict) -> bool:
        """Save a single review to the database.
        
        Args:
            review_data: Dictionary containing review data
            
        Returns:
            bool: True if saved successfully, False if already exists
        """
        with self.get_session() as session:
            # Check if review already exists
            existing = session.query(ReviewModel).filter_by(id=review_data["id"]).first()
            if existing:
                return False
            
            # Create new review
            review = ReviewModel(
                id=review_data["id"],
                source=review_data["source"],
                rating=review_data["rating"],
                title=review_data["title"],
                text=review_data["text"],
                date=datetime.fromisoformat(review_data["date"]) if isinstance(review_data["date"], str) else review_data["date"],
                version=review_data.get("version"),
                processed=review_data.get("processed", False)
            )
            
            session.add(review)
            return True
    
    def save_reviews_batch(self, reviews_data: list[dict]) -> int:
        """Save multiple reviews to the database.
        
        Args:
            reviews_data: List of review dictionaries
            
        Returns:
            int: Number of reviews saved (excluding duplicates)
        """
        saved_count = 0
        with self.get_session() as session:
            for review_data in reviews_data:
                # Check if review already exists
                existing = session.query(ReviewModel).filter_by(id=review_data["id"]).first()
                if existing:
                    continue
                
                # Create new review
                review = ReviewModel(
                    id=review_data["id"],
                    source=review_data["source"],
                    rating=review_data["rating"],
                    title=review_data["title"],
                    text=review_data["text"],
                    date=datetime.fromisoformat(review_data["date"]) if isinstance(review_data["date"], str) else review_data["date"],
                    version=review_data.get("version"),
                    processed=review_data.get("processed", False)
                )
                
                session.add(review)
                saved_count += 1
                session.flush()  # Flush to catch duplicate errors immediately
        
        return saved_count
    
    def get_reviews_by_source(self, source: str, limit: Optional[int] = None) -> list[dict]:
        """Get reviews by source.
        
        Args:
            source: Review source (google_play or apple_app_store)
            limit: Maximum number of reviews to return
            
        Returns:
            list[dict]: List of review dictionaries
        """
        with self.get_session() as session:
            query = session.query(ReviewModel).filter_by(source=source)
            if limit:
                query = query.limit(limit)
            
            reviews = query.all()
            return [review.to_dict() for review in reviews]
    
    def get_unprocessed_reviews(self, limit: Optional[int] = None) -> list[dict]:
        """Get unprocessed reviews.
        
        Args:
            limit: Maximum number of reviews to return
            
        Returns:
            list[dict]: List of unprocessed review dictionaries
        """
        with self.get_session() as session:
            query = session.query(ReviewModel).filter_by(processed=False)
            if limit:
                query = query.limit(limit)
            
            reviews = query.all()
            return [review.to_dict() for review in reviews]
    
    def mark_review_as_processed(self, review_id: str) -> bool:
        """Mark a review as processed.
        
        Args:
            review_id: ID of the review to mark as processed
            
        Returns:
            bool: True if updated successfully
        """
        with self.get_session() as session:
            review = session.query(ReviewModel).filter_by(id=review_id).first()
            if review:
                review.processed = True
                return True
            return False
    
    def get_top_reviews(
        self,
        limit: int = 8,
        mode: str = "positive",
        source: Optional[str] = None,
    ) -> list[dict]:
        """Return top reviews for dashboard display.

        mode: positive (4–5★), negative (1–2★), recent (all, newest first)
        """
        with self.get_session() as session:
            query = session.query(ReviewModel)
            if source:
                query = query.filter_by(source=source)
            if mode == "positive":
                query = query.filter(ReviewModel.rating >= 4)
            elif mode == "negative":
                query = query.filter(ReviewModel.rating <= 2)
            query = query.order_by(ReviewModel.date.desc()).limit(limit)
            return [review.to_dict() for review in query.all()]

    def get_rating_distribution(self, source: Optional[str] = None) -> dict[int, int]:
        """Count reviews per star rating (1–5)."""
        dist = {i: 0 for i in range(1, 6)}
        with self.get_session() as session:
            query = session.query(ReviewModel)
            if source:
                query = query.filter_by(source=source)
            for row in query.all():
                if 1 <= row.rating <= 5:
                    dist[row.rating] += 1
        return dist

    def clear_all_data(self) -> None:
        """Remove all reviews and insights (e.g. after wrong app package was collected)."""
        with self.get_session() as session:
            session.query(ReviewModel).delete()
            session.query(InsightsModel).delete()

    def get_review_count(self, source: Optional[str] = None) -> int:
        """Get total review count.
        
        Args:
            source: Filter by source if provided
            
        Returns:
            int: Total number of reviews
        """
        with self.get_session() as session:
            query = session.query(ReviewModel)
            if source:
                query = query.filter_by(source=source)
            return query.count()
    
    def close(self):
        """Close database connections and cleanup."""
        if self.engine:
            self.engine.dispose()
            self.engine = None

    # ── Phase 2: Insights storage ─────────────────────────────────────────────

    def save_insights(self, insights_data: dict) -> bool:
        """Save or replace weekly insights.

        Args:
            insights_data: Dict matching WeeklyInsights schema.

        Returns:
            bool: True if saved successfully.
        """
        with self.get_session() as session:
            existing = session.query(InsightsModel).filter_by(
                id=insights_data["week"]
            ).first()
            if existing:
                # Update in place
                existing.generated_at = datetime.fromisoformat(
                    insights_data["generated_at"]
                ) if isinstance(insights_data["generated_at"], str) else insights_data["generated_at"]
                existing.total_reviews_analysed = insights_data["total_reviews_analysed"]
                existing.themes = insights_data["themes"]
                existing.quotes = insights_data["quotes"]
                existing.actions = insights_data["actions"]
                existing.sentiment_summary = insights_data["sentiment_summary"]
                existing.doc_id = insights_data.get("doc_id")
                existing.email_id = insights_data.get("email_id")
            else:
                record = InsightsModel(
                    id=insights_data["week"],
                    week=insights_data["week"],
                    generated_at=datetime.fromisoformat(
                        insights_data["generated_at"]
                    ) if isinstance(insights_data["generated_at"], str) else insights_data["generated_at"],
                    total_reviews_analysed=insights_data["total_reviews_analysed"],
                    themes=insights_data["themes"],
                    quotes=insights_data["quotes"],
                    actions=insights_data["actions"],
                    sentiment_summary=insights_data["sentiment_summary"],
                    doc_id=insights_data.get("doc_id"),
                    email_id=insights_data.get("email_id"),
                )
                session.add(record)
        return True

    def get_insights(self, week: Optional[str] = None) -> Optional[dict]:
        """Retrieve insights for a given week, or the most recent if week is None.

        Args:
            week: ISO week string e.g. '2026-W20', or None for latest.

        Returns:
            dict or None
        """
        with self.get_session() as session:
            if week:
                record = session.query(InsightsModel).filter_by(week=week).first()
            else:
                record = (
                    session.query(InsightsModel)
                    .order_by(InsightsModel.generated_at.desc())
                    .first()
                )
            return record.to_dict() if record else None

    def list_insights_weeks(self) -> list[str]:
        """Return all stored week identifiers, newest first."""
        with self.get_session() as session:
            rows = (
                session.query(InsightsModel.week)
                .order_by(InsightsModel.generated_at.desc())
                .all()
            )
            return [r.week for r in rows]
