# Microsoft Dev News Feed

A daily-updated aggregator that pulls from **55+ official Microsoft developer blogs** across Azure, .NET, GitHub, VS Code, and the broader Microsoft dev ecosystem. One clean, searchable interface. No accounts, no tracking.

## What it does

- Aggregates RSS feeds from 55+ Microsoft developer blogs daily
- Deduplicates content and filters to the last 30 days
- Presents articles in a polished, searchable interface
- Generates its own RSS feed so you can subscribe
- Optional AI-generated summaries via OpenAI

## Sources

| Category | Blogs |
|----------|-------|
| Azure & Cloud | Azure Compute, Azure Infrastructure, Azure Architecture, Azure Arc, Azure Storage, Azure Networking, AKS, and more |
| AI & Machine Learning | Azure AI, Azure Databricks, Cosmos DB, Microsoft Foundry, Agent Framework, AutoGen |
| Developer Tools | Visual Studio, VS Code, Azure DevOps, Azure SDK, Command Line, ISE |
| Languages & Frameworks | .NET, TypeScript, C++, Python, Java, PowerShell, .NET Aspire |
| GitHub | GitHub Blog, GitHub Changelog |
| Platform & Identity | Microsoft 365 Dev, Identity Blog, Security & Compliance |
| Operations | Governance & Management, Observability, FinOps |
| Community | Linux & Open Source, Official Microsoft Blog, Windows Blog |

## Tech Stack

- **Backend**: Python script fetching and cleaning RSS feeds
- **Frontend**: Vanilla JS (no frameworks), responsive design, dark/light mode
- **Hosting**: GitHub Pages (free)
- **Automation**: GitHub Actions (daily cron)
- **PWA**: Install on phone, works offline
- **AI Summaries**: Optional OpenAI integration for article descriptions

## Setup

### 1. Fork this repo

### 2. Enable GitHub Pages
Go to Settings → Pages → Source: `main` branch, root `/`

### 3. (Optional) Add AI Summaries
Go to Settings → Secrets → Actions → New secret:
- Name: `OPENAI_API_KEY`
- Value: Your OpenAI API key

### 4. Run the first fetch
Go to Actions → "Fetch Microsoft Dev Blog Feeds" → Run workflow

That's it. The feed auto-updates daily at 7 AM EST.

## Run Locally

```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Fetch feeds
python scripts/fetch_feeds.py

# Serve the site
python -m http.server 8000
# Open http://localhost:8000
```

## Project Structure

```
msdev-news-feed/
├── index.html              # Main page
├── manifest.json           # PWA manifest
├── sw.js                   # Service worker for offline support
├── css/
│   └── styles.css          # All styles (dark/light themes)
├── js/
│   └── app.js              # Frontend logic (filtering, search, bookmarks)
├── data/
│   ├── feeds.json          # Article data (auto-generated)
│   └── feed.xml            # RSS output feed (auto-generated)
├── icons/
│   ├── icon-192.png        # PWA icon
│   └── icon-512.png        # PWA icon
├── scripts/
│   ├── fetch_feeds.py      # RSS aggregator script
│   └── requirements.txt    # Python dependencies
└── .github/
    └── workflows/
        └── fetch-feeds.yml # GitHub Actions daily workflow
```

## License

MIT - Built for the community. Fork it, improve it, or just use it.
