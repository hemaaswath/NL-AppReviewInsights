"""
Apple App Store review collector.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from shared.models import Review, ReviewSource, ReviewCollection
from shared.review_normalizer import normalize_review_fields


class AppleAppStoreCollector:
    """Collector for Apple App Store reviews."""
    
    BASE_URL = "https://itunes.apple.com/us/rss/customerreviews/page"
    
    def __init__(self, app_id: str, weeks_back: int = 12):
        """Initialize Apple App Store collector.
        
        Args:
            app_id: Apple App Store ID
            weeks_back: Number of weeks back to collect reviews from
        """
        self.app_id = app_id
        self.weeks_back = weeks_back
        self.cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks_back)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _fetch_reviews_page(self, page: int = 1) -> str:
        """Fetch a page of reviews from Apple App Store.
        
        Args:
            page: Page number to fetch
            
        Returns:
            str: XML response containing reviews
        """
        url = f"{self.BASE_URL}/{page}/id/{self.app_id}/sortby=mostrecent/xml"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Save raw response for debugging
        import os
        os.makedirs("data/raw/apple_app_store", exist_ok=True)
        with open(f"data/raw/apple_app_store/page_{page}.xml", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        return response.text
    
    def _parse_review(self, entry) -> Optional[Review]:
        """Parse a single review from Apple App Store RSS feed.
        
        Args:
            entry: XML entry element
            
        Returns:
            Review: Parsed review object or None if invalid
        """
        try:
            # Extract review content
            author = entry.find("author")
            author_name = author.find("name").text if author else ""
            
            title_tag = entry.find("title")
            title = title_tag.text if title_tag else ""
            
            content_tag = entry.find("content")
            text = content_tag.text if content_tag else ""
            
            # Extract rating - try both with and without namespace
            rating_tag = entry.find("im:rating")
            if not rating_tag:
                rating_tag = entry.find("rating")
            rating = int(rating_tag.text) if rating_tag and rating_tag.text else 0
            
            # Extract date
            updated_tag = entry.find("updated")
            date_str = updated_tag.text if updated_tag else ""
            try:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                date = datetime.now(timezone.utc)
            
            # Extract version - try both with and without namespace
            version_tag = entry.find("im:version")
            if not version_tag:
                version_tag = entry.find("version")
            version = version_tag.text if version_tag else ""
            
            # Generate unique ID
            review_id = hashlib.md5(
                f"{self.app_id}_{author_name}_{date_str}".encode()
            ).hexdigest()
            
            if rating == 0:
                return None

            normalized = normalize_review_fields(title, text)
            if not normalized:
                return None
            title, text = normalized

            if date < self.cutoff_date:
                return None

            return Review(
                id=review_id,
                source=ReviewSource.APPLE_APP_STORE,
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
    
    def collect_reviews(self, max_reviews: Optional[int] = None) -> ReviewCollection:
        """Collect reviews from Apple App Store.
        
        Args:
            max_reviews: Maximum number of reviews to collect (None for no limit)
            
        Returns:
            ReviewCollection: Collection of reviews
        """
        reviews = []
        page = 1
        total_collected = 0
        
        print(f"Collecting reviews from Apple App Store for app ID: {self.app_id}")
        
        while True:
            try:
                # Fetch reviews page
                xml_content = self._fetch_reviews_page(page)
                
                # Parse XML
                soup = BeautifulSoup(xml_content, "xml")
                entries = soup.find_all("entry")
                
                # Skip first entry (it's the app info, not a review)
                for entry in entries[1:]:
                    review = self._parse_review(entry)
                    if review:
                        reviews.append(review)
                        total_collected += 1
                        
                        if max_reviews and total_collected >= max_reviews:
                            break
                
                # Check if we should continue
                if max_reviews and total_collected >= max_reviews:
                    break
                
                # Check if there are more pages
                if len(entries) <= 1:
                    break
                
                page += 1
                print(f"Collected {total_collected} reviews so far...")
                
            except Exception as e:
                print(f"Error fetching reviews page {page}: {e}")
                break
        
        print(f"Total reviews collected from Apple App Store: {len(reviews)}")
        
        return ReviewCollection(
            reviews=reviews,
            source=ReviewSource.APPLE_APP_STORE
        )
