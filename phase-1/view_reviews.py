"""
Script to view reviews from the database.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.database import DatabaseManager
from datetime import datetime, timezone

def view_reviews(source=None, limit=10):
    """View reviews from the database.
    
    Args:
        source: Filter by source ('google_play' or 'apple_app_store')
        limit: Maximum number of reviews to display
    """
    db = DatabaseManager("data/reviews.db")
    
    if source:
        reviews = db.get_reviews_by_source(source, limit=limit)
        print(f"\n=== Reviews from {source} ===")
    else:
        reviews = db.get_reviews_by_source("google_play", limit=limit)
        reviews.extend(db.get_reviews_by_source("apple_app_store", limit=limit))
        print(f"\n=== All Reviews (last {limit} per source) ===")
    
    for i, review in enumerate(reviews, 1):
        print(f"\n--- Review {i} ---")
        print(f"ID: {review['id']}")
        print(f"Source: {review['source']}")
        print(f"Rating: {review['rating']}/5")
        print(f"Title: {review['title']}")
        print(f"Text: {review['text']}")
        print(f"Date: {review['date']}")
        print(f"Version: {review['version']}")
        print(f"Processed: {review['processed']}")
    
    print(f"\nTotal displayed: {len(reviews)}")
    print(f"Total in database: {db.get_review_count()}")
    print(f"Google Play: {db.get_review_count('google_play')}")
    print(f"Apple App Store: {db.get_review_count('apple_app_store')}")
    
    db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='View reviews from database')
    parser.add_argument('--source', choices=['google_play', 'apple_app_store'], 
                        help='Filter by source')
    parser.add_argument('--limit', type=int, default=10, 
                        help='Number of reviews to display')
    
    args = parser.parse_args()
    view_reviews(source=args.source, limit=args.limit)
