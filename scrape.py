import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
import anthropic

KEYWORDS = [
    "스타트업 투자", "VC 투자", "벤처캐피탈 투자",
    "시리즈A 투자", "시리즈B 투자", "시리즈C 투자",
    "프리IPO 투자", "시드 투자", "스타트업 인수",
    "벤처 M&A", "스타트업 M&A", "초기 투자 유치"
]

TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"
DISPLAY = 3 if TEST_MODE else 20

def parse_naver_date(pub_date):
    try:
        from email.utils import parsedate
        from time import mktime
        t = parsedate(pub_date)
        if t:
            dt = datetime.fromtimestamp(mktime(t))
            return dt.strftime("%Y.%m.%d")
    except:
        pass
    return datetime.now().strftime("%Y.%m.%d")

def fetch_naver_news(keyword, display=20):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": os.environ.get("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.environ.get("NAVER_CLIENT_SECRET", "")
    }
    params = {"query": keyword, "display": display, "sort": "date"}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        articles = []
        for item in data.get("items", []):
            title = BeautifulSoup(item["title"], "html.parser").get_text()
            desc = BeautifulSoup(item["description"], "html.parser").get_text()
            link = item.get("originallink") or item.get("link", "")
            pub_date = parse_naver_date(item.get("pubDate", ""))
            articles.append({"title": title, "summary": desc, "url": link, "date": pub_date})
        return articles
    except Exception as e:
        print(f"네이버 검색 오류 ({keyword}): {e}")
        return []

def classify_with_claude(articles):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    results = []

    for article in articles:
        prompt = f"""당신은 한국 VC/스타트업 투자 딜 분류 전문가입니다.
아래 기사가 실제 VC/스타트업 투자 딜 기사인지 판단하십시오.

제목: {article['title']}
요약: {article['summary']}

---

[포함 기준 — 아래 3가지를 모두 충족해야 포함]
1. 투자자(investor)가 기사에 명시되어 있음
2. 투자 대상 스타트업/기업(company)이 기사에 명시되어 있음
3. 신규 투자 라운드 또는 M&A 거래임

포함되는 딜 유형:
- 시드 투자 (Seed)
- 시리즈A 투자
- 시리즈B 투자
- 시리즈C 이상 투자
- Pre-IPO 투자
- 스타트업 M&A (인수/합병)

---

[제외 기준 — 하나라도 해당하면 SKIP]
- PE/사모펀드의 성숙 기업 인수 (VC/스타트업 아님)
- 주가·시황·수급 분석 기사
- 주주환원·배당·자사주 소각
- 이사회·임원 인사·조직 개편
- 투자자 또는 투자 대상 기업이 불명확한 기사
- 이미 완료된 과거 딜의 사후 동향 기사

---

판단 후, 포함이면 아래 JSON만 출력 (설명 없이), 제외이면 SKIP만 출력.

포함 시 JSON 형식:
{{
  "title": "{article['title'][:60]}",
  "summary": "딜 핵심 내용 1-2문장. 반드시 투자자, 피투자사, 투자 성격을 포함할 것",
  "company": "투자 대상 스타트업/기업의 공식 법인명 (약칭 금지)",
  "investor": "주요 투자자명 (리드 투자자 우선)",
  "type": "seed | series_a | series_b | series_c | pre_ipo | ma",
  "tags": ["type값"],
  "ev": "투자 금액 (예: 100억원). 불명확하면 null",
  "deal_stage": "소문 | 협상 | 계약 | 완료"
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
                    print(f"✗ company 없음 — 제외: {deal.get('title', '')}")
                    continue
                results.append(deal)
                print(f"✓ [{deal.get('deal_stage','?')}] {deal['company']} ← {deal.get('investor','?')} ({deal['type']})")
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e} | 응답: {response[:80]}")
        except Exception as e:
            print(f"분류 오류: {e}")

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

    print(f"\n{len(added)}개 새 딜 추가됨. 총 {len(merged)}개.")

if __name__ == "__main__":
    print(f"네이버 뉴스 검색 중... ({'테스트모드' if TEST_MODE else '전체모드'})")
    articles = []
    seen = set()

    for keyword in KEYWORDS:
        found = fetch_naver_news(keyword, display=DISPLAY)
        new = [a for a in found if a["title"] not in seen]
        seen.update(a["title"] for a in new)
        articles.extend(new)
        print(f"  '{keyword}': {len(new)}개")

    print(f"\n총 {len(articles)}개 기사 수집됨\n")
    print("Claude 분류 중...")
    deals = classify_with_claude(articles)
    print("\ndeals.json 업데이트 중...")
    update_deals(deals)
