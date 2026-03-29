import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
import anthropic

KEYWORDS = [
    "Korean startup funding",
    "Korea venture capital investment",
    "Korea series A funding",
    "Korea series B funding",
    "Korea startup acquisition",
    "Korea pre-IPO investment",
    "Korean startup seed round",
    "Korea VC deal",
]

TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

def fetch_google_news(keyword):
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(keyword)}&hl=en-US&gl=US&ceid=US:en"
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.content, "xml")
        articles = []
        items = soup.find_all("item")[:3 if TEST_MODE else 10]
        for item in items:
            title = item.find("title").get_text() if item.find("title") else ""
            desc = item.find("description").get_text() if item.find("description") else ""
            link = item.find("link").get_text() if item.find("link") else ""
            pub_date = item.find("pubDate").get_text() if item.find("pubDate") else ""
            # 날짜 파싱
            try:
                from email.utils import parsedate
                from time import mktime
                t = parsedate(pub_date)
                date_str = datetime.fromtimestamp(mktime(t)).strftime("%Y.%m.%d") if t else datetime.now().strftime("%Y.%m.%d")
            except:
                date_str = datetime.now().strftime("%Y.%m.%d")
            # desc에서 HTML 태그 제거
            desc_clean = BeautifulSoup(desc, "html.parser").get_text()
            articles.append({"title": title, "summary": desc_clean, "url": link, "date": date_str})
        return articles
    except Exception as e:
        print(f"Google News RSS 오류 ({keyword}): {e}")
        return []

def classify_with_claude(articles):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    results = []

    for article in articles:
        prompt = f"""You are an expert in classifying Korean VC and startup investment deal news.
Determine if the article below is about an actual VC/startup investment deal.

Title: {article['title']}
Summary: {article['summary']}

---

[INCLUDE criteria — must meet ALL 3]
1. Investor is clearly named in the article
2. Target startup/company is clearly named
3. This is a new investment round or M&A transaction

Include deal types:
- Seed investment
- Series A
- Series B
- Series C or later
- Pre-IPO investment
- Startup M&A (acquisition/merger)

---

[EXCLUDE — skip if ANY applies]
- PE/private equity buyout of mature non-startup companies
- Stock price or market analysis articles
- Executive appointments or org restructuring
- Investor or target company is unclear
- Post-deal follow-up articles with no new transaction

---

If INCLUDE, output ONLY the JSON below (no explanation). If EXCLUDE, output only: SKIP

JSON format:
{{
  "title": "{article['title'][:60]}",
  "summary": "1-2 sentence deal summary. Must include investor, target company, and deal nature.",
  "company": "Official legal name of the target startup/company (no abbreviations)",
  "investor": "Primary/lead investor name",
  "type": "seed | series_a | series_b | series_c | pre_ipo | ma",
  "tags": ["type value"],
  "ev": "Investment amount (e.g. $50M). null if unclear",
  "deal_stage": "rumor | negotiation | signed | closed"
}}"""

        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            response = message.content[0].text.strip()
            response = response.replace("```json", "").replace("```", "").strip()
            if response.upper() == "SKIP":
                continue
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != 0:
                deal = json.loads(response[start:end])
                deal["url"] = article["url"]
                deal["date"] = article["date"]
                if not deal.get("company"):
                    print(f"✗ no company — skip: {deal.get('title', '')}")
                    continue
                results.append(deal)
                print(f"✓ [{deal.get('deal_stage','?')}] {deal['company']} ← {deal.get('investor','?')} ({deal['type']})")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e} | response: {response[:80]}")
        except Exception as e:
            print(f"Classification error: {e}")

    return results

def update_deals(new_deals):
    deals_path = "_data/deals.json"
    try:
        with open(deals_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except:
        existing = []

    existing_titles = {d["title"] for d in existing}
    added = [d for d in new_deals if d["title"] not in existing_titles]
    merged = added + existing
    merged = merged[:100]

    with open(deals_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n{len(added)} new deals added. Total: {len(merged)}.")

if __name__ == "__main__":
    print(f"Fetching Google News RSS... ({'test mode' if TEST_MODE else 'full mode'})")
    articles = []
    seen = set()

    for keyword in KEYWORDS:
        found = fetch_google_news(keyword)
        new = [a for a in found if a["title"] not in seen]
        seen.update(a["title"] for a in new)
        articles.extend(new)
        print(f"  '{keyword}': {len(new)} articles")

    print(f"\nTotal {len(articles)} articles collected\n")
    print("Classifying with Claude...")
    deals = classify_with_claude(articles)
    print("\nUpdating deals.json...")
    update_deals(deals)
