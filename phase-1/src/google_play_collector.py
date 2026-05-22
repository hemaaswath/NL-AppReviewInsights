"""
Google Play Store review collector.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from google_play_scraper import Sort, reviews as fetch_gp_reviews
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from shared.models import Review, ReviewSource, ReviewCollection
from shared.review_normalizer import normalize_review_fields


class GooglePlayCollector:
    """Collector for Google Play Store reviews."""
    
    def __init__(self, package_name: str, weeks_back: int = 12):
        """Initialize Google Play Store collector.
        
        Args:
            package_name: Google Play package name (e.g., com.nextbillion.groww)
            weeks_back: Number of weeks back to collect reviews from
        """
        self.package_name = package_name
        self.weeks_back = weeks_back
        self.cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks_back)
    
    def _parse_review(self, review_data: dict) -> Optional[Review]:
        """Parse a single review from Google Play Store response.
        
        Args:
            review_data: Raw review data from google-play-scraper
            
        Returns:
            Review: Parsed review object or None if invalid
        """
        try:
            # Extract review content from google-play-scraper format
            # Fields: reviewId, userName, content, score, at (datetime), appVersion
            author_name = review_data.get("userName", "")
            review_id_raw = review_data.get("reviewId", "")
            title = review_data.get("title", "")  # not always present
            text = review_data.get("content", "")
            rating = review_data.get("score", 0)
            
            # 'at' is already a datetime object from google-play-scraper
            at_dt = review_data.get("at")
            if isinstance(at_dt, datetime):
                # Ensure timezone-aware
                date = at_dt if at_dt.tzinfo else at_dt.replace(tzinfo=timezone.utc)
            else:
                date = datetime.now(timezone.utc)
            
            # Extract version
            version = review_data.get("appVersion", "") or review_data.get("reviewCreatedVersion", "")
            
            # Generate unique ID — prefer the native reviewId, fall back to hash
            if review_id_raw:
                review_id = hashlib.md5(review_id_raw.encode()).hexdigest()
            else:
                review_id = hashlib.md5(
                    f"{self.package_name}_{author_name}_{date.isoformat()}".encode()
                ).hexdigest()
            
            if rating == 0:
                return None

            normalized = normalize_review_fields(title or "", text)
            if not normalized:
                return None
            title, text = normalized

            # Check if review is within date range
            if date < self.cutoff_date:
                return None

            return Review(
                id=review_id,
                source=ReviewSource.GOOGLE_PLAY,
                rating=rating,
                title=title,
                text=text,
                date=date,
                version=version,
                processed=False
            )
        except Exception as e:
            print(f"Error parsing review: {e}")
            return None
    
    def _fetch_reviews_batch(
        self,
        batch_size: int,
        continuation_token: Optional[object],
    ) -> tuple:
        """Fetch one batch of reviews from Google Play with retry.

        Args:
            batch_size: Number of reviews to request.
            continuation_token: Pagination token from previous call.

        Returns:
            tuple: (result list, next continuation_token)
        """
        return fetch_gp_reviews(
            self.package_name,
            lang='en',
            country='in',
            sort=Sort.NEWEST,
            count=batch_size,
            filter_score_with=None,
            continuation_token=continuation_token,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _fetch_reviews_batch_with_retry(
        self,
        batch_size: int,
        continuation_token: Optional[object],
    ) -> tuple:
        """Fetch one batch with exponential-backoff retry (up to 3 attempts).

        Args:
            batch_size: Number of reviews to request.
            continuation_token: Pagination token from previous call.

        Returns:
            tuple: (result list, next continuation_token)
        """
        return self._fetch_reviews_batch(batch_size, continuation_token)

    def collect_reviews(self, max_reviews: Optional[int] = None) -> ReviewCollection:
        """Collect reviews from Google Play Store.
        
        Args:
            max_reviews: Maximum number of reviews to collect (None for no limit)
            
        Returns:
            ReviewCollection: Collection of reviews
        """
        collected = []
        total_collected = 0
        continuation_token = None
        
        print(f"Collecting reviews from Google Play Store for {self.package_name}")
        
        while True:
            try:
                batch_size = 100 if not max_reviews else min(100, max_reviews - total_collected)
                
                # Fetch reviews using google-play-scraper (with retry)
                result, continuation_token = self._fetch_reviews_batch_with_retry(
                    batch_size, continuation_token
                )
                
                # Parse reviews
                for review_data in result:
                    review = self._parse_review(review_data)
                    if review:
                        collected.append(review)
                        total_collected += 1
                        
                        if max_reviews and total_collected >= max_reviews:
                            break
                
                # Check if we should continue
                if max_reviews and total_collected >= max_reviews:
                    break
                
                # Check if there are more pages
                if not continuation_token:
                    break
                
                print(f"Collected {total_collected} reviews so far...")
                
            except Exception as e:
                print(f"Error fetching reviews: {e}")
                break
        
        print(f"Total reviews collected from Google Play Store: {len(collected)}")
        
        return ReviewCollection(
            reviews=collected,
            source=ReviewSource.GOOGLE_PLAY
        )
