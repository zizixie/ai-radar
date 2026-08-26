#!/usr/bin/env python3
"""Fetch GitHub Trending and Product Hunt RSS into one JSON file."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "data" / "news.json"
GITHUB_TRENDING_URL = "https://github.com/trending"
PRODUCT_HUNT_RSS_URL = "https://www.producthunt.com/?format=rss"
MAX_ITEMS = 20
HEADERS = {
    "User-Agent": "ai-radar/1.0 (+https://github.com/)",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def fetch_github_trending() -> list[dict]:
    """Return today's public GitHub Trending repositories."""
    response = requests.get(GITHUB_TRENDING_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    projects = []

    for row in soup.select("article.Box-row")[:MAX_ITEMS]:
        title_link = row.select_one("h2 a")
        if not title_link:
            continue
        href = title_link.get("href", "").strip()
        name = clean_text(title_link.get_text(" ", strip=True)).replace(" / ", "/")
        description_node = row.select_one("p")
        language_node = row.select_one('[itemprop="programmingLanguage"]')
        description = clean_text(description_node.get_text(" ", strip=True) if description_node else "")
        language = clean_text(language_node.get_text(" ", strip=True) if language_node else "")
        row_text = clean_text(row.get_text(" ", strip=True))
        stars_match = re.search(r"([\d,]+)\s+stars?\s+today", row_text, re.IGNORECASE)
        today_stars = int(stars_match.group(1).replace(",", "")) if stars_match else 0

        projects.append(
            {
                "title": name,
                "url": f"https://github.com{href}" if href.startswith("/") else href,
                "description": description,
                "language": language or "未标注",
                "today_stars": today_stars,
            }
        )
    return projects


def fetch_product_hunt() -> list[dict]:
    """Return the most recent Product Hunt RSS entries."""
    response = requests.get(PRODUCT_HUNT_RSS_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"无法解析 Product Hunt RSS: {feed.bozo_exception}")

    products = []
    for entry in feed.entries[:MAX_ITEMS]:
        summary_html = entry.get("summary", entry.get("description", ""))
        description = clean_text(BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True))
        published = entry.get("published", entry.get("updated", ""))
        products.append(
            {
                "title": clean_text(entry.get("title", "未命名产品")),
                "url": entry.get("link", ""),
                "description": description,
                "published_at": published,
            }
        )
    return products


def load_existing() -> dict:
    if not OUTPUT_FILE.exists():
        return {"updated_at": None, "github_trending": [], "product_hunt": []}
    try:
        return json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"updated_at": None, "github_trending": [], "product_hunt": []}


def main() -> int:
    existing = load_existing()
    data = {
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "github_trending": existing.get("github_trending", []),
        "product_hunt": existing.get("product_hunt", []),
    }
    failures = []

    for key, fetcher, label in (
        ("github_trending", fetch_github_trending, "GitHub Trending"),
        ("product_hunt", fetch_product_hunt, "Product Hunt"),
    ):
        try:
            data[key] = fetcher()
            print(f"{label}: 已获取 {len(data[key])} 条")
        except Exception as error:  # Keep prior data if a single source is unavailable.
            failures.append(label)
            print(f"警告：{label} 抓取失败，将保留上次结果：{error}", file=sys.stderr)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        print(f"已完成，失败来源：{', '.join(failures)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
