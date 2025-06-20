import requests
from bs4 import BeautifulSoup
import re
import time
import json
from urllib.parse import urljoin
from requests.exceptions import RequestException

BASE_URL = "https://cabraloutdoors.com"

#––– Helpers –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

def get_soup(url):
    """Fetch a URL and return BeautifulSoup object, with error handling."""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except RequestException as e:
        print(f"[ERROR] Failed to fetch URL: {url}\n{e}")
        return None

#––– STEP 1: Scrape collections hierarchy –––––––––––––––––––––––––––––––––––

def scrape_collections():
    """
    Scrape only the specified collections from the header:
    Fishing, Archery, Camping & Outdoor, Apparel / Merchandise
    Returns dict { handle: { 'title': title, 'subs': { sub_handle: sub_title, ... } } }
    """
    soup = get_soup(BASE_URL)
    if soup is None:
        return {}

    allowed_categories = {
        "Fishing": {},
        "Archery": {},
        "Camping & Outdoor": {},
        "Apparel / Merchandise": {},
    }

    # XPath Equivalent: /html/body/div[2]/store-header/header/main-menu/details/div/nav/ul/li
    nav_items = soup.select("store-header main-menu details > div > nav > ul > li")

    hierarchy = {}
    for li in nav_items:
        summary = li.select_one("summary > a")
        if not summary:
            continue
        title = summary.get_text(strip=True)
        if title not in allowed_categories:
            continue

        # Extract top-level handle from href
        top_href = summary.get("href", "")
        top_match = re.match(r"^/collections/([^/?#]+)", top_href)
        top_handle = top_match.group(1) if top_match else title.lower().replace(" ", "-")

        subs = {}
        sub_links = li.select("ul a[href*='/collections/']")
        for a in sub_links:
            href = a.get("href", "")
            m = re.match(r"^/collections/([^/?#]+)", href)
            if not m:
                continue
            handle = m.group(1)
            sub_title = a.get_text(strip=True)
            subs[handle] = sub_title

        hierarchy[top_handle] = {"title": title, "subs": subs}

    return hierarchy


#––– STEP 2: Walk all products in a sub‑collection –––––––––––––––––––––––––––

def scrape_products_in_collection(handle):
    """
    Returns list of product page URLs for given collection handle.
    Paginates until no more products.
    """
    urls = []
    page = 1
    while True:
        col_url = f"{BASE_URL}/collections/{handle}?page={page}"
        soup = get_soup(col_url)
        if soup is None:
            break

        if not "/collections/" in soup.find_all("link",rel="canonical")[0].get("href"):
            print(f"No products found in: {col_url}")
            break

        
        
        cards = soup.select("a[href*='/products/']")
        if not cards:
            break
        for a in cards:
            prod_url = urljoin(BASE_URL, a.get("href", "").split("?")[0])
            if prod_url and prod_url not in urls:
                urls.append(prod_url)
        page += 1
        time.sleep(0.5)
    return urls

#––– STEP 3: Scrape individual product + reviews ––––––––––––––––––––––––––––

import json

def scrape_product_details(url):
    """
    Extracts product data from JSON-LD embedded in <script type="application/ld+json">.
    """
    soup = get_soup(url)
    if soup is None:
        return {"url": url, "error": "Failed to load page"}

    data = {"url": url}

    # ----- STEP 1: Extract product details from JSON-LD -----
    # Find JSON-LD script
    json_ld_script = soup.find("script", type="application/ld+json")
    if not json_ld_script:
        data["error"] = "No JSON-LD script found"
        return data

    try:
        json_data = json.loads(json_ld_script.string.strip())

        # If it's a list of JSON-LD objects, find the Product one
        if isinstance(json_data, list):
            json_data = next((item for item in json_data if item.get("@type") == "Product"), json_data[0])

        data["title"] = json_data.get("name")
        data["description"] = json_data.get("description")
        data["sku"] = json_data.get("sku")
        data["price"] = (
            json_data.get("offers",{})[0].get("price")
            if isinstance(json_data.get("offers"), list)
            else None
        )
        data["currency"] = (
            json_data.get("offers",{})[0].get("priceCurrency")
            if isinstance(json_data.get("offers"), list)
            else None
        )
        data["images"] = json_data.get("image", [])
        if isinstance(data["images"], str):
            data["images"] = [data["images"]]

    except Exception as e:
        data["error"] = f"Failed to parse JSON-LD: {e}"


    # ----- STEP 2: Extract reviews from Judge.me -----
    reviews = []
    reviews_container = soup.find("div", class_="jdgm-gallery-data")
    if reviews_container:
        try:
            json_reviews = reviews_container.get("data-json", "[]")
            review_data = json.loads(json_reviews)

            for review in review_data:
                review_entry = {
                    "reviewer": review.get("reviewer_name"),
                    "title": review.get("title"),
                    "body": BeautifulSoup(review.get("body_html", ""), "html.parser").get_text(),
                    "rating": review.get("rating"),
                    "created_at": review.get("created_at"),
                    "image_urls": [img.get("original") for img in review.get("pictures_urls", [])]
                }
                reviews.append(review_entry)
        except Exception as e:
            data["review_error"] = f"Failed to parse Judge.me reviews: {e}"

    data["reviews"] = reviews

    return data


#––– MAIN –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

if __name__ == "__main__":
    #all_collections = scrape_collections()
    #print("Found collections hierarchy:")
    #print(json.dumps(all_collections, indent=2))

    # Save to JSON
    with open("all_collections.json", "r") as f:
        all_collections = json.load(f)
    print("\n✅ Done! Data saved to all_collections.json")

    
    result = {}
    for parent, info in all_collections.items():
        result[parent] = {"title": info["title"], "subs": {}}
        # if no subs, treat parent itself as sub
        sub_handles = info["subs"] or {parent: info["title"]}
        for sub_handle, sub_title in sub_handles.items():

            if sub_title.find("Go to") < 0:
                print(f"\nScraping '{parent}' → '{sub_title}' …")
                prod_urls = scrape_products_in_collection(sub_handle)
                print(f"  ↳ {len(prod_urls)} products found")
                # scrape each product
                products_data = []
                for pu in prod_urls:
                    products_data.append(scrape_product_details(pu))
                    time.sleep(0.3)
                result[parent]["subs"][sub_handle] = {
                    "title": sub_title,
                    "products": products_data
            }

            #break
        #break

    # Save to JSON
    with open("cabral_full_catalog.html_scrape.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n✅ Done! Data saved to cabral_full_catalog.html_scrape.json")