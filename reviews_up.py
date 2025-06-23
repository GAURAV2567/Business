import json
import time
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

# Constants
INPUT_JSON = "cabral_full_catalog.html_scrape.json"
OUTPUT_JSON = "cabral_full_catalog_with_ratings.json"
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9"
}

def get_soup(url):
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        resp = requests.get(url, headers=BASE_HEADERS, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except RequestException as e:
        print(f"[ERROR] Could not fetch {url}: {e}")
        return None

def scrape_ratings_summary(soup):
    """
    From a BeautifulSoup-parsed product page, extract:
      - average_rating
      - count_reviews
    Returns a dict with those two keys (values may be None).
    """
    badge = soup.find("div", class_="jdgm-prev-badge")
    if not badge:
        return {"average_rating": None, "count_reviews": None}

    return {
        "average_rating": badge.get("data-average-rating"),
        "count_reviews": badge.get("data-number-of-reviews")
    }

def main():
    # 1. Load existing catalog JSON
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # 2. Iterate through every product and update ratings
    for coll_handle, coll_info in catalog.items():
        for sub_handle, sub_info in coll_info.get("subs", {}).items():
            for product in sub_info.get("products", []):
                url = product.get("url")
                if not url:
                    continue

                print(f"Scraping ratings for: {url}")
                soup = get_soup(url)
                if soup is None:
                    print("  → Failed to load page, skipping.")
                    continue

                ratings = scrape_ratings_summary(soup)
                product.update(ratings)

                # be polite
                time.sleep(1)

    # 3. Save updated catalog
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\nUpdated catalog written to {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
