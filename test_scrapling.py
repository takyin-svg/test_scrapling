# test_scrapling.py  (Scrapling 0.4.15 對齊版)
import json, re, time
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import scrapling
from scrapling.fetchers import Fetcher, StealthyFetcher

SEP = "=" * 60
YAHOO_STOCKS = ["0700.HK", "1810.HK", "1211.HK", "0388.HK", "0005.HK", "3690.HK"]

# ---------- 防禦式工具（嚴格對齊 0.4.15）----------
def get_status(page):
    return getattr(page, "status", None)

def get_body(page):
    b = getattr(page, "body", b"")
    if isinstance(b, bytes):
        return b.decode("utf-8", "ignore")
    return b or ""

def first(el, sel):
    try:
        found = el.css(sel)
    except Exception:
        return None
    if not found:
        return None
    return getattr(found, "first", None) or found[0]

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
        return el.attrib.get("href", "") or ""
    except Exception:
        return ""

def list_css(el, sel):
    try:
        return list(el.css(sel))
    except Exception:
        return []

# ---------- 東財：JSONP 解包 ----------
def parse_eastmoney(page):
    items = []
    body = get_body(page).strip()
    if body and not (body.startswith("{") or body.startswith("[")):
        m = re.search(r"\{.*\}", body, re.DOTALL)
        body = m.group(0) if m else body
    try:
        data = json.loads(body)
    except Exception as e:
        print(f"  [东财] JSON失败 {type(e).__name__} 前120字: {body[:120]!r}")
        return items
    records = (data.get("data") or {}).get("diff") or data.get("result") or data.get("data") or []
    if isinstance(records, dict):
        records = records.get("data") or []
    for r in records:
        t = r.get("title") or r.get("news_title") or ""
        u = r.get("url") or r.get("news_url") or r.get("link") or ""
        if t and u:
            items.append({"title": t, "url": u,
                          "pub_date": str(r.get("show_time") or r.get("publish_time") or ""),
                          "source": "东方财富", "snippet": r.get("digest") or ""})
    return items

def parse_yahoo_rss(page):
    items = []
    body = get_body(page)
    try:
        root = ET.fromstring(body.encode("utf-8", "ignore"))
    except Exception:
        return items
    for it in root.iter("item"):
        t = (it.findtext("title") or "").strip()
        l = (it.findtext("link") or "").strip()
        if t and l:
            items.append({"title": t, "url": l, "pub_date": (it.findtext("pubDate") or "").strip(),
                          "source": "Yahoo-RSS", "snippet": ""})
    return items

def parse_by_href(page, name, *href_substrings, clean_prefix=False):
    items, seen = [], set()
    for a in list_css(page, "a"):
        href = href_of(a)
        if not href or not any(s in href for s in href_substrings):
            continue
        t = text_of(a)
        if not t or len(t) < 8 or href in seen:
            continue
        seen.add(href)
        if clean_prefix:
            t = re.sub(r"^\s*格隆汇\d+月\d+日[|｜:：]\s*", "", t)
        full = urljoin(page.url, href) if not href.startswith("http") else href
        items.append({"title": t, "url": full, "pub_date": "", "source": name, "snippet": ""})
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
                page = StealthyFetcher.fetch(url, headless=True, network_idle=True,
                                             timeout=timeout_sec * 1000)
            if page and get_status(page) == 200:
                return page
            print(f"    非200: status={get_status(page)}")
        except Exception as e:
            print(f"    第{attempt}次失败 {type(e).__name__}: {str(e)[:120]}")
            if attempt < 2:
                time.sleep(2)
    return None

def run():
    total = []

    p = fetch({"fetcher": "fetcher", "timeout_sec": 20},
              "https://api.eastmoney.com/dataapi/xinwen/list?"
              "type=100&pageIndex=1&pageSize=50&keyword=%E6%B8%AF%E8%82%A1")
    if p:
        r = parse_eastmoney(p); total += r; print(f"✅ 东方财富: {len(r)}")

    rss = []
    for s in YAHOO_STOCKS:
        p = fetch({"fetcher": "fetcher", "timeout_sec": 15},
                  f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={s}&region=HK&lang=zh-Hant-HK")
        if p:
            rss += parse_yahoo_rss(p)
        time.sleep(0.3)
    print(f"✅ Yahoo-RSS: {len(rss)}")
    total += rss

    p = fetch({"fetcher": "stealth", "timeout_sec": 45}, "https://finance.sina.com.cn/stock/hkstock/")
    if p:
        r = parse_sina(p); total += r; print(f"✅ 新浪港股: {len(r)}")

    p = fetch({"fetcher": "stealth", "timeout_sec": 60}, "https://www.zhitongcaijing.com/")
    if p:
        r = parse_by_href(p, "智通财经", "/content/detail/"); total += r; print(f"✅ 智通财经: {len(r)}")

    p = fetch({"fetcher": "stealth", "timeout_sec": 45}, "https://www.gelonghui.com/")
    if p:
        r = parse_by_href(p, "格隆汇", "/live/", "/p/", clean_prefix=True)
        total += r; print(f"✅ 格隆汇: {len(r)}")

    p = fetch({"fetcher": "stealth", "timeout_sec": 45}, "https://www.jin10.com/")
    if p:
        r = parse_by_href(p, "金十数据", "/flash/", "/detail/", "jin10.com/flash")
        total += r; print(f"✅ 金十数据: {len(r)}")

    print(f"\n📥 总计: {len(total)} 条")
    return total

if __name__ == "__main__":
    print(SEP, "\nScrapling 版本:", getattr(scrapling, "__version__", "未知"), "\n", SEP, sep="")
    run()
