import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

ALL_GAMES_URL = "https://steamunlocked.net/all-games/"
OUTPUT_FILE = "steamunlocked.json"
MAX_WORKERS = 8       # concurrent requests to individual game pages
REQUEST_DELAY = 0.3   # seconds between each request per thread


def get_all_game_links():
    """Fetch the full game list from the all-games page."""
    print(f"[*] Fetching game list from {ALL_GAMES_URL} ...")
    resp = requests.get(ALL_GAMES_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    game_list = soup.find("ul", id="game-list")
    if not game_list:
        print("[!] Could not find #game-list on the page. Site structure may have changed.")
        sys.exit(1)

    links = []
    for a in game_list.find_all("a", class_="game-link"):
        title = a.get_text(strip=True)
        url = a.get("href", "").strip()
        if title and url:
            links.append({"title": title, "url": url})

    print(f"[*] Found {len(links)} games.")
    return links


def parse_game_page(title, url):
    """Fetch an individual game page and extract size, date, and download URI."""
    try:
        time.sleep(REQUEST_DELAY)
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # --- File size ---
        file_size = ""
        # Look for text patterns like "Size: 1.23 GB" or "1.23 GB"
        size_pattern = re.compile(r"(\d+[\.,]\d+\s*(?:GB|MB|TB|KB))", re.IGNORECASE)
        for tag in soup.find_all(string=size_pattern):
            match = size_pattern.search(tag)
            if match:
                file_size = match.group(1).strip()
                break
        # Fallback: check inside download button text
        if not file_size:
            btn = soup.find("a", class_="btn-download")
            if btn:
                match = size_pattern.search(btn.get_text())
                if match:
                    file_size = match.group(1).strip()

        # --- Upload date ---
        upload_date = ""
        date_pattern = re.compile(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+\d{1,2},\s+\d{4}",
            re.IGNORECASE,
        )
        for tag in soup.find_all(string=date_pattern):
            match = date_pattern.search(tag)
            if match:
                raw_date = match.group(0).strip()
                try:
                    dt = datetime.strptime(raw_date, "%B %d, %Y")
                    upload_date = dt.replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    upload_date = raw_date
                break

        # Fallback: meta date
        if not upload_date:
            meta_date = soup.find("meta", {"property": "article:published_time"})
            if meta_date and meta_date.get("content"):
                upload_date = meta_date["content"]

        # --- Download URI ---
        uris = []
        # Prefer magnet links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("magnet:"):
                uris.append(href)

        # Fall back to btn-download link (UploadHaven)
        if not uris:
            btn = soup.find("a", class_="btn-download")
            if btn and btn.get("href"):
                uris.append(btn["href"])

        # Last resort: any link containing "upload" or "download"
        if not uris:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if any(kw in href.lower() for kw in ["upload", "download", "mediafire", "gofile"]):
                    uris.append(href)
                    break

        return {
            "title": title,
            "uris": uris,
            "fileSize": file_size,
            "uploadDate": upload_date,
        }

    except Exception as e:
        print(f"  [!] Failed to parse {url}: {e}")
        return {
            "title": title,
            "uris": [],
            "fileSize": "",
            "uploadDate": "",
        }


def build_json(games):
    return {
        "name": "SteamUnlocked",
        "downloads": games,
    }


def main():
    start = time.time()

    # Step 1: get all game links
    game_links = get_all_game_links()

    # Step 2: fetch each game page concurrently
    downloads = []
    total = len(game_links)
    completed = 0

    print(f"[*] Fetching {total} game pages with {MAX_WORKERS} workers ...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(parse_game_page, g["title"], g["url"]): g
            for g in game_links
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                downloads.append(result)
            completed += 1
            if completed % 500 == 0 or completed == total:
                elapsed = time.time() - start
                print(f"  [{completed}/{total}] — {elapsed:.0f}s elapsed")

    # Step 3: sort alphabetically
    downloads.sort(key=lambda x: x["title"].lower())

    # Step 4: write JSON
    output = build_json(downloads)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start
    print(f"[✓] Done! {len(downloads)} games written to {OUTPUT_FILE} in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
