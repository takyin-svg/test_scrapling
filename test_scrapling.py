# test_scrapling.py  (Scrapling 0.4.15 修正版)
import json, re, time
from urllib.parse import urljoin

import scrapling
from scrapling.fetchers import Fetcher, StealthyFetcher

SEP = "=" * 60
YAHOO_STOCKS = ["0700.HK", "1810.HK", "1211.HK", "0388.HK", "0005.HK", "3690.HK"]

# ---------- 防禦式工具 ----------
def get_status(page):
    return getattr(page, "status", None)

def get_body(page):
    b = getattr(page, "body", b"")
    if isinstance(b, bytes):
        return b.decode("utf-8", "ignore")
    return b or ""

def get_page_url(page):
    return getattr(page, "url", "") or ""

def all_css(el, sel):
    try:
        return list(el.css(sel))
    except Exception:
        return []

def first_css(el, sel):
    nodes = all_css(el, sel)
    return nodes[0] if nodes else None

def text_of(el):
    if el is None:
        return ""
    try:
        return (el.text or "").strip()
    except Exception:
        return ""

def href_of(el):
    if el is None:
        return ""
    try:
        return (el.attrib.get("href", "") or "").strip()
    except Exception:
        return ""

# ---------- 解析器 ----------
def parse_eastmoney(page):
    items = []
    body = get_body(page).strip()
    if not body:
        print("  [东财] 正文為空")
        return items
    if not (body.startswith("{") or body.startswith("[")):
        m = re.search(r"\{.*\}", body, re.DOTALL)
        body = m.group(0) if m else body
    try:
        data = json.loads(body)
    except Exception as e:
        print(f"  [东财] JSON 失敗 {type(e).__name__} 前120字: {body[:120]!r}")
        return items

    records = (
        (data.get("data") or {}).get("diff")
        or data.get("result")
        or data.get("data")
        or []
    )
    if isinstance(records, dict):
        records = records.get("data") or []

    for r in records:
        t = r.get("title") or r.get("news_title") or ""
        u = r.get("url") or r.get("news_url") or r.get("link") or ""
        if t and u:
            items.append({
                "title": t,
                "url": u,
                "pub_date": str(r.get("show_time") or r.get("publish_time") or ""),
                "source": "东方财富",
                "snippet": r.get("digest") or "",
            })
    return items

def parse_by_href(page, name, *href_substrings, clean_prefix=False):
    items, seen = [], set()
    page_url = get_page_url(page)
    for a in all_css(page, "a"):
        href = href_of(a)
        if not href or not any(s in href for s in href_substrings):
            continue
        t = text_of(a)
        if not t or len(t) < 8:
            continue
        if href in seen:
            continue
        seen.add(href)
        if clean_prefix:
            t = re.sub(r"^\s*格隆汇\d+月\d+日[|｜:：]\s*", "", t)
        full = urljoin(page_url, href) if not href.startswith("http") else href
        items.append({
            "title": t,
            "url": full,
            "pub_date": "",
            "source": name,
            "snippet": "",
        })
    return items

def parse_sina(page):
    items = parse_by_href(page, "新浪港股", "sina.com.cn", "/hkstock", "/doc-")
    if not items:
        items = parse_by_href(page, "新浪港股", "finance.sina.com.cn")
    return items

# ---------- 抓取 ----------
def fetch(cfg, url):
    timeout_sec = cfg.get("timeout_sec", 30)
    for attempt in (1, 2):
        try:
            if cfg.get("fetcher") == "fetcher":
                page = Fetcher.get(url, timeout=timeout_sec)
            else:
                page = StealthyFetcher.fetch(
                    url,
                    headless=True,
                    network_idle=True,
                    timeout=timeout_sec * 1000,
                )
            if page and get_status(page) == 200:
                return page
            print(f"    非200: status={get_status(page)}")
        except Exception as e:
            print(f"    第{attempt}次失敗 {type(e).__name__}: {str(e)[:120]}")
            if attempt < 2:
                time.sleep(2)
    return None

def run():
    total = []

    # 东方财富
    p = fetch(
        {"fetcher": "fetcher", "timeout_sec": 20},
        "https://api.eastmoney.com/dataapi/xinwen/list?"
        "type=100&pageIndex=1&pageSize=50&keyword=%E6%B8%AF%E8%82%A1",
    )
    if p:
        r = parse_eastmoney(p)
        total += r
        print(f"✅ 东方财富: {len(r)}")

    # Yahoo RSS（先保留計數驗證；確認不要後再刪）
    rss = []
    for s in YAHOO_STOCKS:
        p = fetch(
            {"fetcher": "fetcher", "timeout_sec": 15},
            f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={s}&region=HK&lang=zh-Hant-HK",
        )
        if p:
            rss += parse_by_href(p, "Yahoo-RSS", "finance.yahoo.com", "news.yahoo.com")
        time.sleep(0.3)
    print(f"✅ Yahoo-RSS: {len(rss)}")
    total += rss

    # 新浪港股
    p = fetch({"fetcher": "stealth", "timeout_sec": 45}, "https://finance.sina.com.cn/stock/hkstock/")
    if p:
        r = parse_sina(p)
        total += r
        print(f"✅ 新浪港股: {len(r)}")

    # 智通財經
    p = fetch({"fetcher": "stealth", "timeout_sec": 60}, "https://www.zhitongcaijing.com/")
    if p:
        r = parse_by_href(p, "智通財經", "/content/detail/")
        total += r
        print(f"✅ 智通財經: {len(r)}")

    # 格隆匯
    p = fetch({"fetcher": "stealth", "timeout_sec": 45}, "https://www.gelonghui.com/")
    if p:
        r = parse_by_href(p, "格隆匯", "/live/", "/p/", clean_prefix=True)
        total += r
        print(f"✅ 格隆匯: {len(r)}")

    # 金十數據
    p = fetch({"fetcher": "stealth", "timeout_sec": 45}, "https://www.jin10.com/")
    if p:
        r = parse_by_href(p, "金十數據", "/flash/", "/detail/", "jin10.com/flash")
        total += r
        print(f"✅ 金十數據: {len(r)}")

    print(f"\n📥 總計: {len(total)} 條")
    return total

if __name__ == "__main__":
    print(SEP)
    print("Scrapling 版本:", getattr(scrapling, "__version__", "未知"))
    print(SEP)
    run()
