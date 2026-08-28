#!/usr/bin/env python3
"""Collect public AI and technology updates into data/news.json."""

from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from time import time
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "data" / "news.json"
MAX_ITEMS = 20
TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Radar/1.1; +https://github.com/zizixie/ai-radar)",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9,*/*;q=0.8",
}

GITHUB_TRENDING_URL = "https://github.com/trending"
# Product Hunt's `?format=rss` can return HTML; `/feed` is its Atom feed.
PRODUCT_HUNT_FEEDS = ("https://www.producthunt.com/feed", "https://www.producthunt.com/?format=rss")
OPENAI_RSS_URL = "https://openai.com/news/rss.xml"
DEEPMIND_RSS_URL = "https://deepmind.google/blog/rss.xml"
ANTHROPIC_NEWS_URL = "https://www.anthropic.com/news"
HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"

AI_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|generative ai|genai|llm|large language model|foundation model|"
    r"language model|agentic|ai agent|copilot|chatbot|claude|chatgpt|openai|anthropic|gemini|deepmind|"
    r"machine learning|neural network|ai coding|coding agent|vibe coding|diffusion|text-to-image|"
    r"image generation|computer vision|model|models|agent|gpt)\b|"
    r"人工智能|生成式 AI|大模型|智能体|机器学习|神经网络|AI 编程|AI 工具|模型|智能助手",
    re.IGNORECASE,
)


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def to_iso(value: str | None, parsed_value=None) -> str:
    """Normalize feed and page dates to an ISO-8601 UTC string when possible."""
    if parsed_value:
        try:
            return datetime(*parsed_value[:6], tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError):
            pass
    if not value:
        return ""
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, IndexError):
        pass
    for pattern in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    return clean_text(value)


def request(url: str) -> requests.Response:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response


def item(title: str, url: str, description: str, source: str, published_at: str, **extra) -> dict:
    """Build the common item contract used by every source."""
    result = {
        "title": clean_text(title) or "未命名条目",
        "url": url,
        "description": clean_text(description) or f"{source} 官方更新。",
        "source": source,
        "published_at": published_at,
    }
    result.update(extra)
    return result


def is_ai_related(title: str, description: str) -> bool:
    """Keep entries whose title or description clearly signals an AI topic."""
    return bool(AI_PATTERN.search(f"{title} {description}"))


def dedupe(items: list[dict]) -> list[dict]:
    seen, unique = set(), []
    for entry in items:
        identity = entry.get("url") or entry.get("title")
        if identity and identity not in seen:
            seen.add(identity)
            unique.append(entry)
    return unique[:MAX_ITEMS]


def fetch_github_trending() -> list[dict]:
    soup = BeautifulSoup(request(GITHUB_TRENDING_URL).text, "html.parser")
    projects = []
    for row in soup.select("article.Box-row"):
        title_link = row.select_one("h2 a")
        if not title_link:
            continue
        href = title_link.get("href", "").strip()
        description_node = row.select_one("p")
        language_node = row.select_one('[itemprop="programmingLanguage"]')
        stars_match = re.search(r"([\d,]+)\s+stars?\s+today", clean_text(row.get_text(" ", strip=True)), re.IGNORECASE)
        description = description_node.get_text(" ", strip=True) if description_node else "GitHub Trending 项目。"
        if not is_ai_related(title_link.get_text(" ", strip=True), description):
            continue
        projects.append(item(
            title=clean_text(title_link.get_text(" ", strip=True)).replace(" / ", "/"),
            url=urljoin("https://github.com", href),
            description=description,
            source="GitHub Trending", published_at="", fetched_at=iso_now(),
            language=clean_text(language_node.get_text(" ", strip=True) if language_node else "") or "未标注",
            today_stars=int(stars_match.group(1).replace(",", "")) if stars_match else 0,
        ))
    return dedupe(projects)


def fetch_rss(source: str, urls: tuple[str, ...] | str, predicate=None) -> list[dict]:
    """Fetch RSS/Atom, trying fallback endpoints if a publisher changes one."""
    candidates, errors = ((urls,) if isinstance(urls, str) else urls), []
    for feed_url in candidates:
        try:
            feed = feedparser.parse(request(feed_url).content)
            if feed.bozo and not feed.entries:
                raise ValueError(f"无法解析订阅源：{feed.bozo_exception}")
            entries = []
            for entry_data in feed.entries:
                summary = entry_data.get("summary", entry_data.get("description", ""))
                entry = item(
                    title=entry_data.get("title", ""), url=entry_data.get("link", ""),
                    description=BeautifulSoup(summary, "html.parser").get_text(" ", strip=True), source=source,
                    published_at=to_iso(entry_data.get("published", entry_data.get("updated", "")), entry_data.get("published_parsed", entry_data.get("updated_parsed"))),
                )
                if predicate and not predicate(entry):
                    continue
                entries.append(entry)
                if len(entries) >= MAX_ITEMS:
                    break
            if entries:
                return dedupe(entries)
            raise ValueError("订阅源没有可用条目")
        except Exception as error:
            errors.append(f"{feed_url}: {error}")
    raise RuntimeError("; ".join(errors))


def fetch_product_hunt() -> list[dict]:
    return fetch_rss("Product Hunt", PRODUCT_HUNT_FEEDS, lambda entry: is_ai_related(entry["title"], entry["description"]))


def fetch_anthropic() -> list[dict]:
    """Extract the public Anthropic Newsroom, which has no stable RSS endpoint."""
    soup = BeautifulSoup(request(ANTHROPIC_NEWS_URL).text, "html.parser")
    updates = []
    # Publication list links have separate title/date nodes; feature cards do not.
    for link in soup.select('a[class*="listItem"][href^="/news/"]'):
        href = link.get("href", "")
        title_node, date_node = link.select_one('[class*="title"]'), link.select_one("time")
        title = clean_text(title_node.get_text(" ", strip=True) if title_node else link.get_text(" ", strip=True))
        if href.rstrip("/") == "/news" or not title or not date_node:
            continue
        updates.append(item(
            title=title, url=urljoin(ANTHROPIC_NEWS_URL, href), description="Anthropic 官方 Newsroom 更新。",
            source="Anthropic", published_at=to_iso(date_node.get_text(" ", strip=True)),
        ))
    return dedupe(updates)


def fetch_hn_item(item_id: int) -> dict | None:
    try:
        story = request(HN_ITEM_URL.format(item_id=item_id)).json()
        if not story or story.get("type") != "story" or story.get("dead") or story.get("deleted"):
            return None
        title = clean_text(story.get("title", ""))
        text = BeautifulSoup(story.get("text", ""), "html.parser").get_text(" ", strip=True)
        if not AI_PATTERN.search(f"{title} {text}"):
            return None
        published = datetime.fromtimestamp(story.get("time", time()), tz=timezone.utc).isoformat().replace("+00:00", "Z")
        return item(
            title=title, url=story.get("url") or f"https://news.ycombinator.com/item?id={story['id']}",
            description=text or "Hacker News 上的 AI 相关讨论。", source="Hacker News", published_at=published,
            score=story.get("score", 0), comments=story.get("descendants", 0),
        )
    except Exception:
        return None


def fetch_hacker_news() -> list[dict]:
    """Keep only AI, LLM, agents and AI-coding related Hacker News top stories."""
    story_ids = request(HN_TOP_STORIES_URL).json()[:160]
    matches = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_hn_item, story_id) for story_id in story_ids]
        for future in as_completed(futures):
            story = future.result()
            if story:
                matches.append(story)
    matches.sort(key=lambda entry: entry.get("published_at", ""), reverse=True)
    # AI headlines can occasionally be absent from the front page. Search the
    # public HN index as a fallback so this source remains useful every day.
    if len(matches) < MAX_ITEMS:
        for query in ("AI", "LLM", "AI agent", "Claude", "ChatGPT", "Gemini", "coding agent"):
            try:
                response = requests.get(
                    HN_SEARCH_URL,
                    params={"query": query, "tags": "story", "hitsPerPage": 20},
                    headers=HEADERS,
                    timeout=TIMEOUT,
                )
                response.raise_for_status()
                for story in response.json().get("hits", []):
                    title = clean_text(story.get("title", ""))
                    text = BeautifulSoup(story.get("story_text", ""), "html.parser").get_text(" ", strip=True)
                    if not title or not AI_PATTERN.search(f"{title} {text}"):
                        continue
                    matches.append(item(
                        title=title,
                        url=story.get("url") or f"https://news.ycombinator.com/item?id={story['objectID']}",
                        description=text or "Hacker News 上的 AI 相关讨论。",
                        source="Hacker News",
                        published_at=to_iso(story.get("created_at", "")),
                        score=story.get("points", 0) or 0,
                        comments=story.get("num_comments", 0) or 0,
                    ))
            except requests.RequestException:
                continue
    matches.sort(key=lambda entry: entry.get("published_at", ""), reverse=True)
    return dedupe(matches)


SOURCES = (
    ("github_trending", "GitHub Trending", fetch_github_trending),
    ("product_hunt", "Product Hunt", fetch_product_hunt),
    ("openai", "OpenAI", lambda: fetch_rss("OpenAI", OPENAI_RSS_URL)),
    ("anthropic", "Anthropic", fetch_anthropic),
    ("google_deepmind", "Google DeepMind", lambda: fetch_rss("Google DeepMind", DEEPMIND_RSS_URL)),
    ("hacker_news", "Hacker News", fetch_hacker_news),
)


def load_existing() -> dict:
    empty = {"updated_at": None, **{key: [] for key, _, _ in SOURCES}}
    if not OUTPUT_FILE.exists():
        return empty
    try:
        return {**empty, **json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))}
    except (json.JSONDecodeError, OSError):
        return empty


def main() -> int:
    existing = load_existing()
    data, failures, successful_sources = ({key: existing.get(key, []) for key, _, _ in SOURCES}, [], 0)
    for key, label, fetcher in SOURCES:
        try:
            data[key] = fetcher()
            successful_sources += 1
            print(f"{label}: 已获取 {len(data[key])} 条")
        except Exception as error:
            failures.append(label)
            print(f"警告：{label} 抓取失败，将保留上次结果：{error}", file=sys.stderr)
    data["updated_at"] = iso_now() if successful_sources else existing.get("updated_at")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        print(f"已完成，失败来源：{', '.join(failures)}", file=sys.stderr)
    return 1 if not successful_sources else 0


if __name__ == "__main__":
    raise SystemExit(main())
