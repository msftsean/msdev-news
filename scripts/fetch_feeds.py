#!/usr/bin/env python3
"""
Microsoft Dev News Feed - RSS Feed Aggregator
Fetches, deduplicates, and aggregates RSS feeds from across the Microsoft developer ecosystem.
Generates a unified JSON data file and RSS feed for the static frontend.
"""

import feedparser
import json
import os
import re
import time
import html
from datetime import datetime, timedelta, timezone
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from email.utils import parsedate_to_datetime, format_datetime


# ─── Feed Configuration ───────────────────────────────────────────────────────

# Microsoft Tech Community blogs (board ID → display name)
TC_RSS_URL = "https://techcommunity.microsoft.com/t5/s/gxcuf89792/rss/board?board.id={board}"
TC_BLOGS = {
    "AzureAI":                       "Azure AI",
    "azure-ai-services":             "Azure AI Services",
    "analyticsonazure":              "Analytics on Azure",
    "appsonazureblog":               "Apps on Azure",
    "azurearcblog":                  "Azure Arc",
    "azurearchitectureblog":         "Azure Architecture",
    "azurecompute":                  "Azure Compute",
    "azureconfidentialcomputingblog": "Confidential Computing",
    "azure-databricks":              "Azure Databricks",
    "azuregovernanceandmanagementblog": "Governance & Management",
    "azure-customer-innovation-blog":  "Customer Innovation",
    "azureinfrastructureblog":       "Azure Infrastructure",
    "integrationsonazureblog":       "Integrations on Azure",
    "azuremigrationblog":            "Azure Migration",
    "azurenetworkingblog":           "Azure Networking",
    "azureobservabilityblog":        "Azure Observability",
    "azurepaasklog":                 "Azure PaaS",
    "azurestackblog":                "Azure Stack",
    "azurestorageblog":              "Azure Storage",
    "finopsblog":                    "FinOps",
    "azuretoolsblog":                "Azure Tools",
    "azurevirtualdesktopblog":       "Azure Virtual Desktop",
    "linuxandopensourceblog":        "Linux & Open Source",
    "azuredevcommunity":             "Azure Dev Community",
    "fasttrackforazureblog":         "FastTrack for Azure",
    "windowsitproblog":              "Windows IT Pro",
    "microsoft-security-and-compliance": "Security & Compliance",
}

# Microsoft DevBlogs (slug → (display name, feed URL))
DEVBLOGS = {
    "dotnet":           (".NET Blog",               "https://devblogs.microsoft.com/dotnet/feed/"),
    "typescript":       ("TypeScript Blog",          "https://devblogs.microsoft.com/typescript/feed/"),
    "visualstudio":     ("Visual Studio Blog",       "https://devblogs.microsoft.com/visualstudio/feed/"),
    "vscode":           ("VS Code Blog",             "https://code.visualstudio.com/feed.xml"),
    "commandline":      ("Windows Command Line",     "https://devblogs.microsoft.com/commandline/feed/"),
    "devops":           ("Azure DevOps Blog",        "https://devblogs.microsoft.com/devops/feed/"),
    "powershell":       ("PowerShell Blog",          "https://devblogs.microsoft.com/powershell/feed/"),
    "microsoft365dev":  ("Microsoft 365 Dev",        "https://devblogs.microsoft.com/microsoft365dev/feed/"),
    "azuresdk":         ("Azure SDK Blog",           "https://devblogs.microsoft.com/azure-sdk/feed/"),
    "cppblog":          ("C++ Blog",                 "https://devblogs.microsoft.com/cppblog/feed/"),
    "python":           ("Python at Microsoft",      "https://devblogs.microsoft.com/python/feed/"),
    "cosmosdb":         ("Azure Cosmos DB Blog",     "https://devblogs.microsoft.com/cosmosdb/feed/"),
    "azuresql":         ("Azure SQL Blog",           "https://devblogs.microsoft.com/azure-sql/feed/"),
    "aspire":           (".NET Aspire Blog",         "https://devblogs.microsoft.com/aspire/feed/"),
    "foundry":          ("Microsoft Foundry Blog",   "https://devblogs.microsoft.com/foundry/feed/"),
    "allthingsazure":   ("All Things Azure",         "https://devblogs.microsoft.com/all-things-azure/feed/"),
    "agentframework":   ("Agent Framework Blog",     "https://devblogs.microsoft.com/agent-framework/feed/"),
    "identity":         ("Identity Blog",            "https://devblogs.microsoft.com/identity/feed/"),
    "java":             ("Java at Microsoft",        "https://devblogs.microsoft.com/java/feed/"),
    "ise":              ("Microsoft ISE Blog",       "https://devblogs.microsoft.com/ise/feed/"),
    "engineering":      ("Engineering at Microsoft",  "https://devblogs.microsoft.com/engineering-at-microsoft/feed/"),
    "autogen":          ("AutoGen Blog",             "https://devblogs.microsoft.com/autogen/feed/"),
}

# Other Microsoft blog sources (slug → (display name, feed URL))
OTHER_BLOGS = {
    "github":           ("GitHub Blog",              "https://github.blog/feed/"),
    "ghchangelog":      ("GitHub Changelog",         "https://github.blog/changelog/feed/"),
    "azureblog":        ("Microsoft Azure Blog",     "https://azure.microsoft.com/en-us/blog/feed/"),
    "msblog":           ("Microsoft Official Blog",  "https://blogs.microsoft.com/feed/"),
    "windowsblog":      ("Windows Blog",             "https://blogs.windows.com/feed/"),
}

# AKS Blog
AKS_BLOG_FEED = "https://blog.aks.azure.com/rss.xml"

# Microsoft-friendly bloggers & developer advocates (slug → (display name, feed URL))
BLOGGERS = {
    "hanselman":    ("Scott Hanselman",      "https://www.hanselman.com/blog/feed/rss"),
    "burkeholland": ("Burke Holland",         "https://burkeholland.github.io/feed.xml"),
    "kedashakerr":  ("Kedasha Kerr",          "https://github.blog/author/ladykerr/feed/"),
}

# Blogs without RSS feeds (scraped from HTML)
HTML_BLOGS = {
    "squadblog": {
        "name": "Squad Blog",
        "author": "Brady Gaster",
        "index_url": "https://bradygaster.github.io/squad/blog/",
        "base_url": "https://bradygaster.github.io",
        "link_pattern": r'href="(/squad/blog/\d{3}[^"]+)"',
    },
}


# ─── Category Mapping ─────────────────────────────────────────────────────────
# Maps blog slugs to categories for frontend filtering

CATEGORIES = {
    "Azure & Cloud": [
        "azurecompute", "azurevirtualdesktopblog", "azureinfrastructureblog",
        "azurearchitectureblog", "azure-customer-innovation-blog", "azurenetworkingblog",
        "azurestackblog", "azurestorageblog", "azurearcblog", "azuremigrationblog",
        "allthingsazure", "azureblog", "fasttrackforazureblog", "azurepaasklog",
        "appsonazureblog", "integrationsonazureblog", "aksblog",
    ],
    "AI & Machine Learning": [
        "AzureAI", "azure-ai-services", "analyticsonazure", "azure-databricks",
        "foundry", "agentframework", "autogen", "cosmosdb", "azuresql",
    ],
    "Developer Tools": [
        "visualstudio", "vscode", "commandline", "devops", "azuresdk",
        "azuretoolsblog", "azuredevcommunity", "ise", "engineering",
    ],
    "Languages & Frameworks": [
        "dotnet", "typescript", "cppblog", "python", "java", "powershell",
        "aspire",
    ],
    "GitHub": [
        "github", "ghchangelog",
    ],
    "Platform & Identity": [
        "microsoft365dev", "identity", "microsoft-security-and-compliance",
    ],
    "Operations & Management": [
        "azuregovernanceandmanagementblog", "azureobservabilityblog", "finopsblog",
        "windowsitproblog",
    ],
    "Community & News": [
        "linuxandopensourceblog", "msblog", "windowsblog",
        "azureconfidentialcomputingblog",
    ],
    "Voices & Advocates": [
        "hanselman", "burkeholland", "kedashakerr", "squadblog",
    ],
}


# ─── User-Agent for requests ──────────────────────────────────────────────────
USER_AGENT = "MSDevNewsFeed/1.0 (+https://github.com/msdev-news-feed)"


# ─── Helper Functions ─────────────────────────────────────────────────────────

def clean_html(raw_html):
    """Remove HTML tags and clean up text."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", "", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300] if len(text) > 300 else text


def parse_date(date_str):
    """Parse date string to ISO format, handling multiple formats."""
    if not date_str:
        return ""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    # Try ISO format
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
    ]:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    return date_str


def get_entry_date(entry):
    """Extract and parse date from a feed entry."""
    for field in ["published", "updated", "created"]:
        val = entry.get(field, "")
        if val:
            return parse_date(val)
    return ""


def get_entry_author(entry):
    """Extract author from a feed entry."""
    if "author_detail" in entry and entry.author_detail.get("name"):
        return entry.author_detail["name"]
    if "author" in entry and entry.author:
        return entry.author
    if "authors" in entry and entry.authors:
        names = [a.get("name", "") for a in entry.authors if a.get("name")]
        if names:
            return ", ".join(names)
    return "Microsoft"


# ─── Feed Fetchers ────────────────────────────────────────────────────────────

def fetch_tech_community_feeds():
    """Fetch articles from Microsoft Tech Community blogs."""
    articles = []
    for board_id, display_name in TC_BLOGS.items():
        url = TC_RSS_URL.format(board=board_id)
        try:
            feed = feedparser.parse(url, agent=USER_AGENT)
            for entry in feed.entries:
                summary = clean_html(
                    entry.get("summary", "") or entry.get("description", "")
                )
                articles.append({
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "published": get_entry_date(entry),
                    "summary": summary,
                    "blog": display_name,
                    "blogid": board_id,
                    "author": get_entry_author(entry),
                })
            print(f"  ✓ Tech Community: {display_name} ({len(feed.entries)} articles)")
        except Exception as e:
            print(f"  ✗ Tech Community: {display_name} - Error: {e}")
        time.sleep(0.3)
    return articles


def fetch_devblogs_feeds():
    """Fetch articles from Microsoft DevBlogs."""
    articles = []
    for slug, (display_name, feed_url) in DEVBLOGS.items():
        try:
            feed = feedparser.parse(feed_url, agent=USER_AGENT)
            for entry in feed.entries:
                summary = clean_html(
                    entry.get("summary", "") or entry.get("description", "")
                )
                articles.append({
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "published": get_entry_date(entry),
                    "summary": summary,
                    "blog": display_name,
                    "blogid": slug,
                    "author": get_entry_author(entry),
                })
            print(f"  ✓ DevBlogs: {display_name} ({len(feed.entries)} articles)")
        except Exception as e:
            print(f"  ✗ DevBlogs: {display_name} - Error: {e}")
        time.sleep(0.5)
    return articles


def fetch_other_blogs():
    """Fetch articles from other Microsoft blog sources."""
    articles = []
    for slug, (display_name, feed_url) in OTHER_BLOGS.items():
        try:
            feed = feedparser.parse(feed_url, agent=USER_AGENT)
            for entry in feed.entries:
                summary = clean_html(
                    entry.get("summary", "") or entry.get("description", "")
                )
                articles.append({
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "published": get_entry_date(entry),
                    "summary": summary,
                    "blog": display_name,
                    "blogid": slug,
                    "author": get_entry_author(entry),
                })
            print(f"  ✓ Other: {display_name} ({len(feed.entries)} articles)")
        except Exception as e:
            print(f"  ✗ Other: {display_name} - Error: {e}")
        time.sleep(0.5)
    return articles


def fetch_aks_blog():
    """Fetch articles from the AKS blog."""
    articles = []
    try:
        feed = feedparser.parse(AKS_BLOG_FEED, agent=USER_AGENT)
        for entry in feed.entries:
            summary = clean_html(
                entry.get("summary", "") or entry.get("description", "")
            )
            articles.append({
                "title": entry.get("title", "Untitled"),
                "link": entry.get("link", ""),
                "published": get_entry_date(entry),
                "summary": summary,
                "blog": "AKS Blog",
                "blogid": "aksblog",
                "author": get_entry_author(entry),
            })
        print(f"  ✓ AKS Blog ({len(feed.entries)} articles)")
    except Exception as e:
        print(f"  ✗ AKS Blog - Error: {e}")
    return articles


def fetch_html_blogs():
    """Fetch articles from blogs that don't have RSS feeds (HTML scraping)."""
    import urllib.request

    articles = []
    for slug, config in HTML_BLOGS.items():
        try:
            req = urllib.request.Request(
                config["index_url"],
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                page_html = resp.read().decode("utf-8", errors="replace")

            # Extract post links
            links = re.findall(config["link_pattern"], page_html)
            # Deduplicate while preserving order
            seen = set()
            unique_links = []
            for link in links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)

            # Take the most recent posts (highest number = newest)
            unique_links = unique_links[:15]

            for i, path in enumerate(unique_links):
                full_url = config["base_url"] + path
                # Extract title from the path slug
                # e.g. /squad/blog/028-new-docs-site/ -> "New Docs Site"
                slug_part = path.rstrip("/").split("/")[-1]
                # Remove leading number prefix like "028-"
                title_slug = re.sub(r"^\d+-", "", slug_part)
                title = title_slug.replace("-", " ").title()

                # Try to fetch the actual page title
                try:
                    req2 = urllib.request.Request(
                        full_url,
                        headers={"User-Agent": USER_AGENT},
                    )
                    with urllib.request.urlopen(req2, timeout=10) as resp2:
                        post_html = resp2.read().decode("utf-8", errors="replace")
                    title_match = re.search(r"<title>([^<]+)", post_html)
                    if title_match:
                        # Strip " — Squad Docs" suffix and clean HTML entities
                        title = html.unescape(re.sub(r"\s*[—\-|]\s*Squad Docs$", "", title_match.group(1)).strip())
                    # Try to get description from meta
                    desc_match = re.search(
                        r'<meta\s+(?:name="description"\s+content="|property="og:description"\s+content=")([^"]*)',
                        post_html,
                    )
                    summary = desc_match.group(1) if desc_match else ""
                except Exception:
                    summary = ""

                # Use position-based pseudo-date (newest first, spaced 2 days apart)
                from datetime import datetime, timedelta, timezone as tz
                pseudo_date = datetime.now(tz.utc) - timedelta(days=i * 2)

                articles.append({
                    "title": title,
                    "link": full_url,
                    "published": pseudo_date.isoformat(),
                    "summary": clean_html(summary),
                    "blog": config["name"],
                    "blogid": slug,
                    "author": config["author"],
                })
                time.sleep(0.3)

            print(f"  ✓ HTML Blog: {config['name']} ({len(unique_links)} articles)")
        except Exception as e:
            print(f"  ✗ HTML Blog: {config['name']} - Error: {e}")
    return articles


def fetch_bloggers():
    """Fetch articles from Microsoft-friendly bloggers and developer advocates."""
    articles = []
    for slug, (display_name, feed_url) in BLOGGERS.items():
        try:
            feed = feedparser.parse(feed_url, agent=USER_AGENT)
            for entry in feed.entries:
                summary = clean_html(
                    entry.get("summary", "") or entry.get("description", "")
                )
                articles.append({
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "published": get_entry_date(entry),
                    "summary": summary,
                    "blog": display_name,
                    "blogid": slug,
                    "author": display_name,
                })
            print(f"  ✓ Blogger: {display_name} ({len(feed.entries)} articles)")
        except Exception as e:
            print(f"  ✗ Blogger: {display_name} - Error: {e}")
        time.sleep(0.5)
    return articles


# ─── AI Client Setup ──────────────────────────────────────────────────────────

def get_ai_client():
    """
    Create an OpenAI-compatible client.
    Supports both OpenAI directly and Azure AI Foundry.

    For OpenAI:       set OPENAI_API_KEY
    For AI Foundry:   set AZURE_AI_ENDPOINT and AZURE_AI_KEY
                      (endpoint looks like: https://<name>.services.ai.azure.com)
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("\n⚠ OpenAI package not installed, skipping AI features")
        return None, None

    # Option 1: Azure AI Foundry
    azure_endpoint = os.environ.get("AZURE_AI_ENDPOINT", "")
    azure_key = os.environ.get("AZURE_AI_KEY", "")
    if azure_endpoint and azure_key:
        base_url = azure_endpoint.rstrip("/") + "/openai"
        client = OpenAI(base_url=base_url, api_key=azure_key)
        model = os.environ.get("AZURE_AI_MODEL", "gpt-4o-mini")
        print(f"\n✓ Using Azure AI Foundry ({azure_endpoint})")
        return client, model

    # Option 2: OpenAI directly
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        client = OpenAI(api_key=api_key)
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        print(f"\n✓ Using OpenAI API")
        return client, model

    print("\n⚠ No AI credentials set (AZURE_AI_ENDPOINT+AZURE_AI_KEY or OPENAI_API_KEY), skipping AI features")
    return None, None


# ─── AI Summary Generation ────────────────────────────────────────────────────

def generate_ai_summaries(articles):
    """Generate AI summaries for articles that lack good descriptions."""
    client, model = get_ai_client()
    if not client:
        return articles

    count = 0
    for article in articles:
        if len(article.get("summary", "")) < 50:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a concise tech news summarizer. Generate a 1-2 sentence summary of the article based on its title. Keep it factual and informative. Maximum 200 characters.",
                        },
                        {
                            "role": "user",
                            "content": f"Summarize this article: \"{article['title']}\" from {article['blog']}",
                        },
                    ],
                    max_tokens=100,
                    temperature=0.3,
                )
                article["summary"] = response.choices[0].message.content.strip()
                article["ai_summary"] = True
                count += 1
                time.sleep(0.2)
            except Exception as e:
                print(f"  ⚠ AI summary failed for: {article['title'][:50]}... - {e}")

    if count:
        print(f"\n✓ Generated {count} AI summaries")
    return articles


# ─── Daily Digest Summary ─────────────────────────────────────────────────────

def generate_daily_digest(articles):
    """Generate a brief AI-powered daily digest of the top stories."""
    client, model = get_ai_client()
    if not client:
        return None

    # Get today's articles
    today = datetime.now(timezone.utc).date()
    today_articles = []
    for a in articles[:30]:
        try:
            pub_date = datetime.fromisoformat(a["published"]).date()
            if pub_date == today:
                today_articles.append(a)
        except (ValueError, KeyError):
            continue

    if not today_articles:
        today_articles = articles[:15]

    titles = "\n".join(
        f"- {a['title']} ({a['blog']})" for a in today_articles[:20]
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a Microsoft developer news editor. Write a brief 2-3 sentence daily digest summarizing the key themes and most noteworthy updates. Be specific about technologies mentioned. No hype, just facts.",
                },
                {
                    "role": "user",
                    "content": f"Today's Microsoft dev articles:\n{titles}",
                },
            ],
            max_tokens=200,
            temperature=0.4,
        )
        digest = response.choices[0].message.content.strip()
        print(f"\n✓ Generated daily digest")
        return digest
    except Exception as e:
        print(f"\n⚠ Daily digest failed: {e}")
        return None


# ─── RSS Feed Generator ───────────────────────────────────────────────────────

def generate_rss_feed(articles, output_path="data/feed.xml"):
    """Generate an RSS 2.0 feed from articles."""
    rss = Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "Microsoft Dev News Feed"
    SubElement(channel, "link").text = "https://msdevfeed.news"
    SubElement(channel, "description").text = (
        "Aggregated daily news from across the Microsoft developer ecosystem"
    )
    SubElement(channel, "language").text = "en-us"
    SubElement(channel, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )

    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", "https://msdevfeed.news/data/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    for article in articles[:100]:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = article.get("title", "")
        SubElement(item, "link").text = article.get("link", "")
        SubElement(item, "description").text = article.get("summary", "")
        if article.get("published"):
            try:
                dt = datetime.fromisoformat(article["published"])
                SubElement(item, "pubDate").text = format_datetime(dt)
            except (ValueError, TypeError):
                pass
        SubElement(item, "author").text = article.get("author", "Microsoft")
        SubElement(item, "category").text = article.get("blog", "")

    tree = ElementTree(rss)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tree.write(output_path, encoding="unicode", xml_declaration=True)
    print(f"\n✓ Generated RSS feed: {output_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Microsoft Dev News Feed - Aggregator")
    print("=" * 60)
    print(f"\nStarted: {datetime.now(timezone.utc).isoformat()}")

    # Fetch from all sources
    print("\n── Fetching Tech Community feeds ──")
    tc_articles = fetch_tech_community_feeds()

    print("\n── Fetching DevBlogs feeds ──")
    db_articles = fetch_devblogs_feeds()

    print("\n── Fetching other blog feeds ──")
    other_articles = fetch_other_blogs()

    print("\n── Fetching AKS Blog ──")
    aks_articles = fetch_aks_blog()

    print("\n── Fetching blogger feeds ──")
    blogger_articles = fetch_bloggers()

    print("\n── Fetching HTML blogs (no RSS) ──")
    html_articles = fetch_html_blogs()

    # Combine all articles
    all_articles = tc_articles + db_articles + other_articles + aks_articles + blogger_articles + html_articles
    print(f"\n── Processing ──")
    print(f"Total raw articles: {len(all_articles)}")

    # Sort by date (newest first)
    all_articles.sort(key=lambda x: x.get("published", ""), reverse=True)

    # Deduplicate by link and filter to last 30 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    seen_links = set()
    unique_articles = []

    for article in all_articles:
        link = article.get("link", "")
        if link and link not in seen_links:
            pub = article.get("published", "")
            if pub >= cutoff:
                seen_links.add(link)
                unique_articles.append(article)

    filtered = len(all_articles) - len(unique_articles)
    if filtered:
        print(f"Filtered out {filtered} duplicate/older-than-30-days articles")
    print(f"Unique articles (last 30 days): {len(unique_articles)}")

    # Generate AI summaries for articles missing descriptions
    unique_articles = generate_ai_summaries(unique_articles)

    # Generate daily digest
    digest = generate_daily_digest(unique_articles)

    # Build output data
    data = {
        "lastupdated": datetime.now(timezone.utc).isoformat(),
        "totalarticles": len(unique_articles),
        "articles": unique_articles,
        "categories": CATEGORIES,
    }
    if digest:
        data["digest"] = digest

    # Write JSON
    os.makedirs("data", exist_ok=True)
    with open("data/feeds.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved {len(unique_articles)} articles to data/feeds.json")

    # Generate RSS feed
    generate_rss_feed(unique_articles)

    # Stats
    print(f"\n── Statistics ──")
    print(f"Tech Community: {len(tc_articles)} articles from {len(TC_BLOGS)} blogs")
    print(f"DevBlogs:       {len(db_articles)} articles from {len(DEVBLOGS)} blogs")
    print(f"Other Blogs:    {len(other_articles)} articles from {len(OTHER_BLOGS)} blogs")
    print(f"AKS Blog:       {len(aks_articles)} articles")
    print(f"Bloggers:       {len(blogger_articles)} articles from {len(BLOGGERS)} bloggers")
    print(f"HTML Blogs:     {len(html_articles)} articles from {len(HTML_BLOGS)} blogs")
    print(f"Total unique:   {len(unique_articles)} articles")
    print(f"\nCompleted: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
