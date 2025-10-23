# remotelock_content_scraper.py
import json
import time
from urllib.parse import urlparse, unquote
from playwright.sync_api import sync_playwright

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

def load_sitemap(filepath="remotelock_sitemap.json"):
    """Load the sitemap JSON structure"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_slug_from_url(url):
    """Extract the article slug from URL"""
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if 'article' in path_parts:
        idx = path_parts.index('article')
        if idx + 1 < len(path_parts):
            return unquote(path_parts[idx + 1])
    return unquote(path_parts[-1]) if path_parts else ""

def extract_content(page):
    """Extract title and clean content from page"""
    # Extract title
    title = ""
    for sel in [
        "h1", 
        "header h1", 
        "article h1", 
        ".slds-page-header__title", 
        "h1.title",
        ".article-title"
    ]:
        el = page.query_selector(sel)
        if el:
            title = el.inner_text().strip()
            break
    
    # Extract main content
    article_body = page.query_selector(
        '[itemprop="articleBody"], .article-body, .knowledgeArticleBody, article, .slds-rich-text-editor__output'
    )
    
    text = ""
    if article_body:
        text = article_body.inner_text().strip()
    else:
        # Fallback to largest text block
        candidates = page.query_selector_all("main, article, div")
        best_text, best_len = "", 0
        for c in candidates:
            try:
                t = c.inner_text().strip()
                if len(t) > best_len and len(t) > 100:  # Minimum content length
                    best_len, best_text = len(t), t
            except:
                pass
        text = best_text
    
    # Clean and format content
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    content = "\n\n".join(lines)
    
    return title, content

def scrape_page(playwright, url):
    """Scrape a single page and return structured data"""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(user_agent=DEFAULT_USER_AGENT, locale="en-US")
    page = context.new_page()
    
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Dismiss any cookie/banner popups
        for selector in [
            'button:has-text("Accept")', 
            'button:has-text("Close")', 
            'button:has-text("Got it")',
            'button:has-text("Agree")'
        ]:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(500)
            except:
                pass
        
        page.wait_for_timeout(2000)
        
        title, content = extract_content(page)
        
        return {
            "title": title,
            "content": content,
            "slug": extract_slug_from_url(url),
            "success": True,
            "error": None
        }
    
    except Exception as e:
        print(f"    ❌ Error: {str(e)[:100]}")
        return {
            "title": "",
            "content": "",
            "slug": extract_slug_from_url(url),
            "success": False,
            "error": str(e)
        }
    finally:
        browser.close()

def create_node(url, title, content, slug, category, subcategory=None):
    """Create a standardized node structure"""
    return {
        "id": slug or extract_slug_from_url(url),
        "url": url,
        "title": title,
        "content": content,
        "slug": slug,
        "category": category,
        "subcategory": subcategory,
        "content_length": len(content),
        "word_count": len(content.split()) if content else 0,
        "embedding": None,  # To be filled by embedder script
        "scraped_at": int(time.time()),
        "source": "support.remotelock.com"
    }

def main():
    # Load sitemap
    print("📂 Loading sitemap...")
    sitemap = load_sitemap()
    
    all_nodes = []
    total_pages = 0
    successful_scrapes = 0
    
    # Count total pages
    for category in sitemap["categories"]:
        if "pages" in category:
            total_pages += len(category["pages"])
        if "subcategories" in category:
            for subcategory in category["subcategories"]:
                total_pages += len(subcategory["pages"])
    
    print(f"📊 Found {total_pages} pages to scrape\n")
    
    # Start scraping
    with sync_playwright() as playwright:
        for category in sitemap["categories"]:
            category_name = category["name"]
            print(f"\n{'='*70}")
            print(f"📁 CATEGORY: {category_name}")
            print(f"{'='*70}")
            
            # Process direct pages (no subcategory)
            if "pages" in category:
                print(f"\n  Processing {len(category['pages'])} pages...")
                for idx, page_url in enumerate(category["pages"], 1):
                    print(f"  [{idx}/{len(category['pages'])}] Scraping: {page_url}")
                    
                    page_data = scrape_page(playwright, page_url)
                    
                    if page_data["success"]:
                        node = create_node(
                            url=page_url,
                            title=page_data["title"],
                            content=page_data["content"],
                            slug=page_data["slug"],
                            category=category_name,
                            subcategory=None
                        )
                        all_nodes.append(node)
                        successful_scrapes += 1
                        print(f"    ✅ {page_data['title'][:60]}")
                        print(f"    📝 Content: {node['word_count']} words")
                    else:
                        # Still create node but with empty content
                        node = create_node(
                            url=page_url,
                            title="",
                            content="",
                            slug=page_data["slug"],
                            category=category_name,
                            subcategory=None
                        )
                        node["error"] = page_data["error"]
                        all_nodes.append(node)
                        print(f"    ⚠️  Failed to scrape")
                    
                    time.sleep(1)  # Rate limiting
            
            # Process subcategories
            if "subcategories" in category:
                for subcategory in category["subcategories"]:
                    subcategory_name = subcategory["name"]
                    print(f"\n  📂 SUBCATEGORY: {subcategory_name}")
                    print(f"     Processing {len(subcategory['pages'])} pages...")
                    
                    for idx, page_url in enumerate(subcategory["pages"], 1):
                        print(f"     [{idx}/{len(subcategory['pages'])}] Scraping: {page_url}")
                        
                        page_data = scrape_page(playwright, page_url)
                        
                        if page_data["success"]:
                            node = create_node(
                                url=page_url,
                                title=page_data["title"],
                                content=page_data["content"],
                                slug=page_data["slug"],
                                category=category_name,
                                subcategory=subcategory_name
                            )
                            all_nodes.append(node)
                            successful_scrapes += 1
                            print(f"       ✅ {page_data['title'][:60]}")
                            print(f"       📝 Content: {node['word_count']} words")
                        else:
                            # Still create node but with empty content
                            node = create_node(
                                url=page_url,
                                title="",
                                content="",
                                slug=page_data["slug"],
                                category=category_name,
                                subcategory=subcategory_name
                            )
                            node["error"] = page_data["error"]
                            all_nodes.append(node)
                            print(f"       ⚠️  Failed to scrape")
                        
                        time.sleep(1)  # Rate limiting
    
    # Save to JSON
    output_file = "remotelock_nodes.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_nodes, f, indent=2, ensure_ascii=False)
    
    # Print summary statistics
    print("\n" + "="*70)
    print("📊 SCRAPING SUMMARY")
    print("="*70)
    print(f"Total pages found:        {total_pages}")
    print(f"Successfully scraped:     {successful_scrapes}")
    print(f"Failed:                   {total_pages - successful_scrapes}")
    print(f"Total nodes created:      {len(all_nodes)}")
    
    # Category breakdown
    category_counts = {}
    for node in all_nodes:
        cat = node["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print(f"\n📁 Nodes per category:")
    for cat, count in sorted(category_counts.items()):
        print(f"   {cat:40s} {count:3d} nodes")
    
    # Content statistics
    nodes_with_content = [n for n in all_nodes if n["content"]]
    avg_words = sum(n["word_count"] for n in nodes_with_content) / len(nodes_with_content) if nodes_with_content else 0
    
    print(f"\n📝 Content statistics:")
    print(f"   Nodes with content:      {len(nodes_with_content)}")
    print(f"   Average word count:      {avg_words:.0f} words")
    print(f"   Total words scraped:     {sum(n['word_count'] for n in all_nodes):,} words")
    
    print(f"\n💾 Saved to: {output_file}")
    print("="*70)
    print("\n✅ Scraping complete! Ready for embedding generation.")

if __name__ == "__main__":
    main()