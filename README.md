Amazon Competitor Analysis (Streamlit)
=====================================

Simple Streamlit app that:
- Scrapes Amazon product details and search results using Oxylabs Web Scraper API
- Stores products and competitors in local JSON via TinyDB
- Runs a concise LLM competitor analysis using LangChain + OpenAI

Quick start
-----------

1) Python
- Requires Python 3.13+

2) Install

```

pip install -U pip
pip install -e .

```

3) Environment variables
Create a `.env` or set in your shell:
- `OXYLABS_USERNAME` – your Oxylabs realtime username
- `OXYLABS_PASSWORD` – your Oxylabs realtime password
- `OPENAI_API_KEY` – your OpenAI key (optional; only for LLM analysis)

On Windows PowerShell:

```

$env:OXYLABS_USERNAME="your_user"
$env:OXYLABS_PASSWORD="your_pass"
$env:OPENAI_API_KEY="sk-..."

```

4) Run the app

```

streamlit run main.py

```

Usage
-----
1. Enter ASIN, Zip/Postal code, and select an Amazon domain
2. Click "Scrape product" to fetch PDP details
3. In "Scraped products", click "Start competitor analysis"
4. After competitors are loaded, press "Analyze with LLM" to get a short write-up

Notes
-----
- Data is stored in `data.json` (TinyDB) in the project directory.
- This app keeps the UI intentionally minimal.
- Oxylabs API reference: `https://developers.oxylabs.io/scraping-solutions/web-scraper-api/targets/amazon`

```
