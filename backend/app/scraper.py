# scrape_remotelock_all.py
import json
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

CATEGORIES = {
    "General": [
        "https://support.remotelock.com/s/article/Device-Registration-Issues-Troubleshooting-and-Self-Help",
        "https://support.remotelock.com/s/article/Need-Help",
        "https://support.remotelock.com/s/article/Help-with-my-Vacation-Rental-Property-Management-Integration",
        "https://support.remotelock.com/s/article/Will-not-lock-unlock",
        "https://support.remotelock.com/s/article/Unable-to-Register-Lock-TS",
        "https://support.remotelock.com/s/article/Troubleshooting-and-Best-Practices",
        "https://support.remotelock.com/s/article/Lock-Flashing-Lights-and-Beeps-Meanings",
        "https://support.remotelock.com/s/article/Spindle-Test",
    ],
    "Legacy Product Troubleshooting": [
        "https://support.remotelock.com/s/article/Lock-Grease",
        "https://support.remotelock.com/s/article/Mortise-Latch-Installation-for-lock-models-RL4000-LS6i-LS6000i",
        "https://support.remotelock.com/s/article/ResortLock-RL-4000-LS-6i-LS1500-Keypad-Replacement",
        "https://support.remotelock.com/s/article/RemoteLock-V0-to-V1-Migration-Guide",
    ],
    "WiFi Connectivity Troubleshooting": [
        "https://support.remotelock.com/s/article/Lock-Offline-ts",
        "https://support.remotelock.com/s/article/Legacy-Device-Wi-Fi-Setup-Provisioning-Guide",
        "https://support.remotelock.com/s/article/WiFi-Troubleshooting-Connectivity-Issues-Reprogramming-and-other-Network-information",
        "https://support.remotelock.com/s/article/RouteThis-Overview",
        "https://support.remotelock.com/s/article/WiFi-Connectivity-Best-Practices",
        "https://support.remotelock.com/s/article/Using-the-Mobile-App-to-Connect-your-Lock-to-Wi-Fi",
        "https://support.remotelock.com/s/article/OpenEdge-Troubleshooting-Codes",
    ],
    "600 Series Troubleshooting": [
        "https://support.remotelock.com/s/article/Tailpiece-Driven-Hub-Troubleshooting-KIC-4000-5000-Series",
        "https://support.remotelock.com/s/article/600-Series-Motor-Replacement-openEDGE-Light-Duty-Commercial-Levers-3i-BG",
        "https://support.remotelock.com/s/article/Battery-Drain-Issues",
    ],
    "500 Series Troubleshooting": [
        "https://support.remotelock.com/s/article/Snapback-Issues",
        "https://support.remotelock.com/s/article/500-Series-OpenEdge-Deadbolt-5i-RG-Replace-Motor",
        "https://support.remotelock.com/s/article/500-Series-OpenEdge-Deadbolt-5i-RG-Tailpiece-Orientation",
        "https://support.remotelock.com/s/article/500-Series-OpenEdge-5i-RG-Replace-Keypad",
    ],
}

def strip_protocol(url: str) -> str:
    """Remove http/https prefix from URL"""
    parsed = urlparse(url)
    return parsed.netloc + parsed.path

def extract_content(page):
    """Extract title, text, html, markdown-like text from a page"""
    title = ""
    for sel in ["h1", "header h1", "article h1", "div.article-header h1", "h1.title"]:
        el = page.query_selector(sel)
        if el:
            title = el.inner_text().strip()
            break

    article_body = page.query_selector('[itemprop="articleBody"], .article-body, .knowledgeArticleBody, article')
    text, html = "", ""
    if article_body:
        text = article_body.inner_text().strip()
        html = article_body.inner_html()
    else:
        # fallback: longest block
        candidates = page.query_selector_all("main, article, div")
        best, best_score = None, 0
        for c in candidates:
            try:
                t = c.inner_text()
                if len(t) > best_score:
                    best_score, best = len(t), c
            except Exception:
                pass
        if best:
            text = best.inner_text().strip()
            html = best.inner_html()

    markdown = "\n\n".join(line.strip() for line in text.splitlines() if line.strip())

    return title, text, html, markdown

def scrape_url(play, url, category, headless=True):
    browser = play.chromium.launch(headless=headless)
    context = browser.new_context(user_agent=DEFAULT_USER_AGENT, locale="en-US")
    page = context.new_page()
    page.goto(url, wait_until="networkidle", timeout=60000)

    # try dismiss banners
    for sel in [
        'button:has-text("Accept")',
        'button:has-text("Agree")',
        'button:has-text("Got it")',
        'button:has-text("Close")',
    ]:
        try:
            btn = page.query_selector(sel)
            if btn:
                btn.click()
        except Exception:
            pass

    page.wait_for_timeout(3000)

    title, text, html, markdown = extract_content(page)
    data = {
        "url": strip_protocol(url),
        "title": title,
        "category": category,
        "content_text": text,
        "content_html": html,
        "content_markdown": markdown,
        "source": "support.remotelock.com",
        "extracted_at": int(time.time()),
        "vector": None,
        "keywords": [],
    }

    browser.close()
    return data

if __name__ == "__main__":
    all_results = []
    with sync_playwright() as p:
        for category, urls in CATEGORIES.items():
            for url in urls:
                try:
                    print(f"Scraping: {url}")
                    record = scrape_url(p, url, category, headless=True)
                    all_results.append(record)
                except Exception as e:
                    print(f"❌ Failed to scrape {url}: {e}")

    with open("troubleshooting.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print("✅ Saved all results to troubleshooting.json")
