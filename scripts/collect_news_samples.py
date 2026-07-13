#!/usr/bin/env python3
"""Collect demo news text samples from a URL list.

Input CSV columns:
  url,category

Output CSV columns:
  category,title,content,url

The script intentionally uses a URL list instead of crawling fixed portal pages,
so classroom demos do not depend on one website's current layout.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_article(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = clean_text(
        (soup.find("meta", attrs={"property": "og:title"}) or {}).get("content", "")
    )
    if not title and soup.title:
        title = clean_text(soup.title.get_text(" "))
    if not title:
        h1 = soup.find("h1")
        title = clean_text(h1.get_text(" ")) if h1 else ""

    candidates = []
    for selector in ("article", "main", ".article", ".content", "#article", "#content"):
        found = soup.select(selector)
        candidates.extend(found)
    if not candidates:
        candidates = [soup.body] if soup.body else [soup]

    best = ""
    for node in candidates:
        paragraphs = [clean_text(p.get_text(" ")) for p in node.find_all("p")]
        text = "\n".join(p for p in paragraphs if len(p) >= 12)
        if len(text) > len(best):
            best = text
    if not best:
        best = clean_text(soup.get_text(" "))
    return title[:300], best[:3000]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV with url,category columns")
    parser.add_argument("--output", default="resources/news_text_classify/collected_demo.csv")
    parser.add_argument("--timeout", type=int, default=12)
    args = parser.parse_args()

    rows = []
    with open(args.input, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            url = (row.get("url") or "").strip()
            category = (row.get("category") or "").strip()
            if not url:
                continue
            try:
                res = requests.get(
                    url,
                    timeout=args.timeout,
                    headers={"User-Agent": "Mozilla/5.0 AIGI-Holmes Classroom Demo"},
                )
                res.raise_for_status()
                title, content = extract_article(res.text)
                rows.append({"category": category, "title": title, "content": content, "url": url})
                print(f"[OK] {category} {title[:40]}")
            except Exception as exc:
                print(f"[WARN] {url}: {exc}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["category", "title", "content", "url"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()

