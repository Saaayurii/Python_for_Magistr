from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterator

import httpx


def parse_google_play_csv(filepath: str | Path) -> Iterator[dict]:
    """Parse Kaggle Google Play Store dataset CSV."""
    with open(filepath, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("App", "").strip()
            if not name:
                continue

            price_raw = row.get("Price", "0").strip().lstrip("$").replace(",", "")
            try:
                price = float(price_raw) if price_raw not in ("0", "", "Free", "NaN") else 0.0
            except ValueError:
                price = 0.0

            rating_raw = row.get("Rating", "").strip()
            try:
                rating = float(rating_raw)
                if rating > 5:
                    rating = None
            except ValueError:
                rating = None

            reviews_raw = row.get("Reviews", "0").strip()
            try:
                rating_count = int(reviews_raw)
            except ValueError:
                rating_count = 0

            app_type = row.get("Type", "Free").strip()
            has_iap = app_type == "Paid" or price > 0

            category = row.get("Category", "").strip().replace("_", " ").title()
            genres = row.get("Genres", "").strip()
            category = genres if genres else category

            external_id = re.sub(r"[^a-zA-Z0-9._-]", "_", name.lower())[:100]

            yield {
                "external_id": f"gplay_{external_id}",
                "platform": "android",
                "name": name,
                "developer": None,
                "category": category,
                "rating": rating,
                "rating_count": rating_count,
                "price": price,
                "has_ads": None,
                "has_iap": has_iap,
                "description": None,
                "short_desc": row.get("Content Rating", ""),
                "languages": None,
                "permissions": None,
                "icon_url": None,
                "store_url": f"https://play.google.com/store/search?q={name.replace(' ', '+')}",
                "metadata": {"genres": genres, "installs": row.get("Installs", "")},
            }


async def fetch_itunes_apps(categories: list[str] | None = None) -> list[dict]:
    """Fetch apps from iTunes Search API."""
    if categories is None:
        categories = [
            "games", "productivity", "education", "health", "fitness",
            "entertainment", "music", "photo", "video", "social",
            "travel", "news", "sports", "finance", "food", "shopping",
            "lifestyle", "weather", "navigation", "utilities",
        ]

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for category in categories:
            try:
                resp = await client.get(
                    "https://itunes.apple.com/search",
                    params={
                        "term": category,
                        "entity": "software",
                        "limit": 200,
                        "country": "us",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("results", []):
                    track_id = str(item.get("trackId", ""))
                    if not track_id:
                        continue
                    price = item.get("price", 0.0) or 0.0
                    results.append({
                        "external_id": f"itunes_{track_id}",
                        "platform": "ios",
                        "name": item.get("trackName", ""),
                        "developer": item.get("sellerName"),
                        "category": item.get("primaryGenreName"),
                        "rating": item.get("averageUserRating"),
                        "rating_count": item.get("userRatingCount"),
                        "price": price,
                        "has_ads": None,
                        "has_iap": bool(item.get("isGameCenterEnabled")),
                        "description": item.get("description"),
                        "short_desc": (item.get("description") or "")[:200],
                        "languages": item.get("languageCodesISO2A"),
                        "permissions": None,
                        "icon_url": item.get("artworkUrl100"),
                        "store_url": item.get("trackViewUrl", ""),
                        "metadata": {
                            "bundle_id": item.get("bundleId"),
                            "genre_ids": item.get("genreIds", []),
                        },
                    })
            except Exception as e:
                print(f"Error fetching iTunes category '{category}': {e}")

    return results
