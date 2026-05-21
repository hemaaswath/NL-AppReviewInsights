"""
Script to create sample review data in the database for demonstration.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone
from shared.database import DatabaseManager

def create_sample_reviews():
    """Create sample reviews in the database."""
    db = DatabaseManager("data/reviews.db")
    
    # Sample Google Play reviews
    google_play_reviews = [
        {
            "id": "gp_001",
            "source": "google_play",
            "rating": 5,
            "title": "Great investment app",
            "text": "This app has made investing so easy for me. The UI is intuitive and the features are amazing!",
            "date": datetime.now(timezone.utc).isoformat(),
            "version": "2.5.0",
            "processed": False
        },
        {
            "id": "gp_002",
            "source": "google_play",
            "rating": 4,
            "title": "Good but needs improvement",
            "text": "Overall a good app but sometimes it crashes when I try to buy stocks. Please fix this.",
            "date": (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)).isoformat(),
            "version": "2.4.8",
            "processed": False
        },
        {
            "id": "gp_003",
            "source": "google_play",
            "rating": 5,
            "title": "Best trading platform",
            "text": "I've tried many trading apps but this one is the best. Low fees and great customer support.",
            "date": (datetime.now(timezone.utc).replace(day=15)).isoformat(),
            "version": "2.5.0",
            "processed": False
        },
        {
            "id": "gp_004",
            "source": "google_play",
            "rating": 3,
            "title": "Average experience",
            "text": "The app is okay but the fees are a bit high compared to competitors.",
            "date": (datetime.now(timezone.utc).replace(day=10)).isoformat(),
            "version": "2.4.5",
            "processed": False
        },
        {
            "id": "gp_005",
            "source": "google_play",
            "rating": 2,
            "title": "Too many bugs",
            "text": "App keeps crashing and customer support is slow to respond.",
            "date": (datetime.now(timezone.utc).replace(day=5)).isoformat(),
            "version": "2.4.0",
            "processed": False
        }
    ]
    
    # Sample Apple App Store reviews
    apple_reviews = [
        {
            "id": "as_001",
            "source": "apple_app_store",
            "rating": 5,
            "title": "Excellent for beginners",
            "text": "Perfect app for anyone starting their investment journey. Very user-friendly.",
            "date": datetime.now(timezone.utc).isoformat(),
            "version": "2.5.0",
            "processed": False
        },
        {
            "id": "as_002",
            "source": "apple_app_store",
            "rating": 4,
            "title": "Solid investment app",
            "text": "Good features and reliable performance. Would recommend to friends.",
            "date": (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)).isoformat(),
            "version": "2.4.8",
            "processed": False
        },
        {
            "id": "as_003",
            "source": "apple_app_store",
            "rating": 5,
            "title": "Love this app!",
            "text": "Been using it for 6 months now and it's been great. The portfolio tracking is excellent.",
            "date": (datetime.now(timezone.utc).replace(day=15)).isoformat(),
            "version": "2.5.0",
            "processed": False
        }
    ]
    
    # Save reviews
    all_reviews = google_play_reviews + apple_reviews
    saved_count = db.save_reviews_batch(all_reviews)
    
    print(f"Created {saved_count} sample reviews in database")
    print(f"Total Google Play reviews: {db.get_review_count('google_play')}")
    print(f"Total Apple App Store reviews: {db.get_review_count('apple_app_store')}")
    print(f"Total reviews in database: {db.get_review_count()}")
    
    db.close()

if __name__ == "__main__":
    create_sample_reviews()
