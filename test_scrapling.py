# test_scrapling_v2.py
import json
import re
import time
import hashlib
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import scrapling
from scrapling.fetchers import Fetcher, StealthyFetcher

SEP = "=" * 64

# ============ 源配置 ============
YAHOO_STOCKS = ["0700.HK", "1810.HK", "1211.HK", "0388.HK", "0005.HK", "3690.HK"]

SOURCES = [
    {
        "name": "东方财富",
        "kind": "json",
        "fetcher": "fetcher",
        "timeout_sec": 20,
        "url": (
            "https://api.eastmoney.com/dataapi/xinwen/list?"
            "type=100&pageIndex=1&pageSize=50&keyword=%E6%B8%AF%E8%82%A1"
        ),
    },
    {"name": "Yahoo-RSS", "kind": "yahoo_rss", "fetcher": "fetcher", "timeout_sec": 15},
    {
        "name": "新浪港股",
        "kind": "html",
        "fetcher": "stealth",
        "timeout_sec": 40,
        "url": "https://finance.sina.com.cn/stock/hkstock/",
    },
    {
        "name": "智通財經",
        "kind": "html",
        "fetcher": "stealth",
        "timeout_sec": 60,
        "url": "https://www.zhitongcaijing.com/",
    },
    {
        "name": "格隆匯",
        "kind": "html",
        "fetcher": "stealth",
        "timeout_sec": 40,
        "url": "https://www.gelonghui.com/",
    },
    {
        "name": "金十數據",
        "kind": "html",
        "fetcher": "stealth",
        "timeout_sec": 40,
        "url": "https://www.jin10.com/",
    },
]

# ============ 自省層 ============
def self_check():
    print(SEP)
    print("Scrapling 自省")
    print(SEP)
    print("scrapling 版本:", getattr(scrapling, "__version__", "未知"))

    probe_url = "https://httpbin.org/html"
    try:
        page = Fetcher.get(probe_url, timeout=20)
    except Exception as e:
        print("[自省] 抓取 httpbin 失敗:", type(e).__name__, str(e)[:120])
        return

    print("Response 類型:", type(page).__name__)
    for attr in ("status", "status_code", "body", "text", "reason", "url"):
        has = hasattr(page, attr)
        val = ""
        if has:
            v = getattr(page, attr)
            if isinstance(v, (bytes, str)):
                val = f"<len={len(v)}>"
            else:
                val = repr(v)
        print(f"  屬性 {attr:12s}: 存在={has}  值={val}")

    for meth in ("css_first", "css", "xpath"):
        print(f"  方法 {meth:10s}: 可用={hasattr(page, meth)}")


# ============ 防禦式工具 ============
def get_status(page):
    for a in ("status_code", "status"):
        if hasattr(page, a):
            try:
                return int(getattr(page, a))
            except Exception:
                pass
    return None


def get_body(page):
    if hasattr(page, "text") and getattr(page, "text"):
        t = page.text
        return t.decode("utf-8", "ignore") if isinstance(t, bytes) else str(t)
    if hasattr(page, "body") and getattr(page, "body"):
        b = page.body
        return b.decode("utf-8", "ignore") if isinstance(b, bytes) else str(b)
    return ""


def css_first(el, sel):
    try:
        found = el.css(sel)
    except Exception:
        return None
    if not found:
        return None
    f = getattr(found, "first", None)
    if f is not None:
        return f
    try:
        return found[0]
    except Exception:
        return None


def get_text(el):
    if el is None:
        return ""
    try:
        t = el.text
        return (t or "").strip()
    except Exception:
        return ""


def get_href(el):
    if el is None:
        return ""
    try:
        return el.attrib.get("href", "") or ""
    except Exception:
        return ""


# ============ 診斷器 ============
def diagnose(page, name):
    body = get_body(page)
    print(f"  [診斷] 正文長度: {len(body)}")
    title = css_first(page, "title")
    print(f"  [診斷] 頁面標題: {get_text(title)[:50]}")
    for sel in ("article", "li", "a", "h2", "h3", "time"):
        try:
            n = len(page.css(sel))
        except Exception:
            n = -1
        print(f"  [診斷] 命中 <{sel}>: {n}")
    print("  [診斷] 候選連結樣本(文字>=10):")
    n = 0
    seen = set()
    for a in page.css("a"):
        t = get_text(a)
        href = get_href(a)
        if not t or len(t) < 10 or href in seen:
            continue
        seen.add(href)
        pcls = ""
        try:
            if a.parent is not None:
                pcls = " ".join(a.parent.attrib.get("class", "").split())[:24]
        except Exception:
            pass
        print(f"    [{pcls}] {t[:34]} | {href[:64]}")
        n += 1
        if n >= 12:
            break
    if n == 0:
        print("    (無任何含文字連結 -> SPA 空殼，HTML 路徑無解，需改走後端接口)")


# ============ 解析器 ============
def parse_eastmoney_json(page):
    items = []
    body = get_body(page)
    if not body:
        return items
    body = body.strip()
    if not (body.startswith("{") or body.startswith("[")):
        m = re.search(r"\{.*\}", body, re.DOTALL)
        body = m.group(0) if m else body
    try:
        data = json.loads(body)
    except Exception as e:
        print(f"  [東財] JSON解析失敗: {type(e).__name__} | 前120字: {body[:120]!r}")
        return items

    records = []
    if isinstance(data, dict):
        records = (data.get("data") or {}).get("diff") or []
        if not records:
            records = data.get("result") or data.get("data") or []
            if isinstance(records, dict):
                records = records.get("data") or []

    for rec in records:
        title = rec.get("title") or rec.get("news_title") or ""
        url = rec.get("url") or rec.get("news_url") or rec.get("link") or ""
        pub_date = rec.get("show_time") or rec.get("publish_time") or rec.get("date") or ""
        snippet = rec.get("digest") or rec.get("summary") or ""
        if title and url:
            items.append(
                {
                    "title": title,
                    "url": url,
                    "pub_date": str(pub_date),
                    "source": "东方财富",
                    "snippet": snippet,
                }
            )
    return items


def parse_yahoo_rss(page):
    items = []
    body = get_body(page)
    if not body:
        return items
    try:
        root = ET.fromstring(body.encode("utf-8", "ignore"))
    except Exception as e:
        print(f"  [Yahoo-RSS] XML解析失敗: {type(e).__name__}")
        return items
    for item_el in root.iter("item"):
        t = item_el.findtext("title") or ""
        l = item_el.findtext("link") or ""
        p = item_el.findtext("pubDate") or ""
        if t and l:
            items.append(
                {
                    "title": t.strip(),
                    "url": l.strip(),
                    "pub_date": p.strip(),
                    "source": "Yahoo-RSS",
                    "snippet": "",
                }
            )
    return items


def _generic_list_parse(page, source_name, card_selector, link_selector="a", time_selector="time, .time, .date, .publish-time"):
    items = []
    seen_local = set()
    cards = []
    try:
        cards = page.css(card_selector)
    except Exception:
        cards = []
    for card in cards:
        a = css_first(card, link_selector)
        if not a:
            continue
        title = get_text(a)
        href = get_href(a)
        if not title or not href or len(title) < 8:
            continue
        if href in seen_local:
            continue
        seen_local.add(href)
        skip = any(k in href for k in ("login", "register", "about", "contact", "download", "app", "search", "tag", "javascript:"))
        if skip:
            continue
        pub_date = ""
        t_el = css_first(card, time_selector) if time_selector else None
        if t_el:
            pub_date = get_text(t_el)
        full_url = urljoin(page.url, href) if not href.startswith("http") else href
        items.append(
            {
                "title": title,
                "url": full_url,
                "pub_date": pub_date,
                "source": source_name,
                "snippet": "",
            }
        )
    return items


def parse_sina_hk(page):
    items = _generic_list_parse(page, "新浪港股", "ul.list li, .newslist li, .blk01 li")
    if not items:
        items = _generic_list_parse(page, "新浪港股", "li")
    return items


def parse_zhitong(page):
    items = _generic_list_parse(page, "智通財經", "article, .news-item, .feed-item, .article-item")
    if not items:
        items = _generic_list_parse(page, "智通財經", "a[href*='/news/']")
    return items


def parse_gelonghui(page):
    items = _generic_list_parse(page, "格隆匯", "article, .article-item, .news-item, .feed-card, .home-feed-item")
    if not items:
        items = _generic_list_parse(page, "格隆匯", "a[href*='/news/']")
    return items


def parse_jin10(page):
    items = _generic_list_parse(page, "金十數據", ".jin-flash, .flash-item, .news-flash, .jin10-item, article", link_selector=".title, .content, .text, p, a")
    if not items:
        items = _generic_list_parse(page, "金十數據", "a")
    return items


PARSERS = {
    "东方财富": parse_eastmoney_json,
    "Yahoo-RSS": parse_yahoo_rss,
    "新浪港股": parse_sina_hk,
    "智通財經": parse_zhitong,
    "格隆匯": parse_gelonghui,
    "金十數據": parse_jin10,
}

# ============ Yahoo 股票詳情 ============
def fetch_yahoo_stock_detail(stock_code):
    url = f"https://finance.yahoo.com/quote/{stock_code}/"
    try:
        page = Fetcher.get(url, timeout=20)
    except Exception as e:
        print(f"  ⚠️ Yahoo詳情 {stock_code} 抓取失敗: {type(e).__name__}: {str(e)[:120]}")
        return None

    st = get_status(page)
    if st != 200:
        print(f"  ⚠️ Yahoo詳情 {stock_code} 狀態碼={st}")
        return None

    detail = {
        "stock_code": stock_code,
        "name": "",
        "price": "",
        "change": "",
        "change_percent": "",
        "currency": "",
        "market_status": "",
        "as_of": "",
    }

    selectors = {
        "name": "h1, .yf-1qfmdm4 h1, .D\\(ib\\) h1, .Fz\\(l\\)",
        "price": ".Fw\\(b\\), .Trsdu\\(0\\.3s\\), .Fz\\(36px\\), .Mb\\(-4px\\)",
        "change": ".Fw\\(500\\), .Pstart\\(8px\\), .Fz\\(24px\\)",
        "change_percent": ".Fw\\(500\\), .Pstart\\(8px\\), .Fz\\(24px\\)",
        "currency": ".Fz\\(14px\\), .C\\(\\$c-fuji-grey-c\\)",
        "market_status": ".C\\(\\$c-fuji-grey-c\\), .Fz\\(14px\\)",
    }

    for key, sel in selectors.items():
        try:
            els = page.css(sel)
            if els:
                val = get_text(els[0]).strip()
                if val:
                    detail[key] = val
        except Exception:
            pass

    if detail["price"]:
        print(f"  ✅ Yahoo詳情 {stock_code}: {detail['name']} | {detail['price']} {detail['currency']}")
        return detail

    # 兜底：抓所有數字節點
    print(f"  ⚠️ Yahoo詳情 {stock_code} 精確選擇器未命中，嘗試兜底")
    try:
        for el in page.css("span, div, h1, h2"):
            t = get_text(el)
            if t and len(t) < 30 and re.search(r"\d", t):
                print(f"    兜底候選: {t[:40]}")
    except Exception:
        pass
    return detail


# ============ 抓取核心 ============
def fetch_page(source_cfg, url):
    fetcher_type = source_cfg.get("fetcher", "stealth")
    timeout_sec = source_cfg.get("timeout_sec", 30)
    max_retries = 2
    name = source_cfg.get("name", "unknown")

    for attempt in range(1, max_retries + 1):
        try:
            if fetcher_type == "fetcher":
                page = Fetcher.get(url, timeout=timeout_sec)
            else:
                page = StealthyFetcher.fetch(url, headless=True, network_idle=True, timeout=timeout_sec * 1000)

            st = get_status(page)
            if page and st == 200:
                return page
            print(f"    ⚠️ 第 {attempt} 次狀態非200: {name} status={st}")
        except Exception as e:
            print(f"    ⚠️ 第 {attempt} 次失敗: {type(e).__name__}: {str(e)[:150]}")
            if attempt < max_retries:
                time.sleep(2)

    print(f"  ❌ [{name}] 抓取失敗，跳過")
    return None


def fetch_source(source_cfg):
    name = source_cfg["name"]
    url = source_cfg.get("url")
    kind = source_cfg.get("kind", "html")

    if kind == "yahoo_rss":
        urls = []
        for stock in YAHOO_STOCKS:
            urls.append(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={stock}&region=HK&lang=zh-Hant-HK")
    elif url:
        urls = [url]
    else:
        print(f"  ⚠️ [{name}] 缺少 url，跳過")
        return []

    all_items = []
    for u in urls:
        page = fetch_page(source_cfg, u)
        if not page:
            continue

        if kind == "json":
            items = parse_eastmoney_json(page)
        elif kind == "yahoo_rss":
            items = parse_yahoo_rss(page)
        else:
            parser = PARSERS.get(name)
            if not parser:
                print(f"  ⚠️ 找不到 [{name}] 的解析器")
                continue
            items = parser(page)

        if not items:
            print(f"  ⚠️ [{name}] 解析為 0，啟動診斷")
            diagnose(page, name)
            if kind == "yahoo_rss":
                continue
        else:
            print(f"  ✅ [{name}] 成功抓取 {len(items)} 條")

        all_items.extend(items)
    return all_items


# ============ 去重與清洗 ============
def normalize_url(url):
    if not url:
        return url
    url = url.strip().rstrip("/")
    url = re.sub(r"[?&](utm_source|utm_medium|utm_campaign|ref|fbclid)=[^&]*", "", url)
    url = re.sub(r"[?&]+$", "", url)
    return url


def make_item_id(item):
    raw = (item.get("url") or item.get("title") or "") + "|" + (item.get("source") or "")
    return hashlib.md5(raw.encode("utf-8", "ignore")).hexdigest()


def clean_title(title):
    if not title:
        return title
    t = re.sub(r"\s*[-–—|／]\s*(新浪|智通|格隆匯|金十|東財|Yahoo|Reuters|Bloomberg).*", "", title, flags=re.IGNORECASE)
    t = re.sub(r"\s*【[^】]*】\s*", "", t)
    t = re.sub(r"\s*\([^)]*廣告[^)]*\)\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()


def deduplicate(items):
    seen_ids = set()
    seen_urls = set()
    seen_titles = set()
    deduped = []
    for item in items:
        item["url"] = normalize_url(item.get("url", ""))
        item["title"] = clean_title(item.get("title", ""))
        if not item["title"] or len(item["title"]) < 5:
            continue
        item_id = make_item_id(item)
        if item_id in seen_ids:
            continue
        url = item.get("url", "")
        if url and url in seen_urls:
            continue
        title_key = item["title"][:40]
        if title_key in seen_titles:
            continue
        seen_ids.add(item_id)
        if url:
            seen_urls.add(url)
        seen_titles.add(title_key)
        deduped.append(item)
    return deduped


# ============ 主流程 ============
def run_scraper():
    all_raw = []
    for src in SOURCES:
        items = fetch_source(src)
        all_raw.extend(items)

    print(f"\n📥 總計：全網共抓取到 {len(all_raw)} 條未處理原始資訊")

    deduped = deduplicate(all_raw)
    print(f"✅ 去重後：{len(deduped)} 條有效新聞")

    # Yahoo 股票詳情
    print("\n📊 開始抓取 Yahoo 股票詳情...")
    stock_details = []
    for code in YAHOO_STOCKS:
        detail = fetch_yahoo_stock_detail(code)
        if detail:
            stock_details.append(detail)

    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stock_details": stock_details,
        "news": deduped,
        "stats": {
            "raw_count": len(all_raw),
            "deduped_count": len(deduped),
            "stock_count": len(stock_details),
        },
    }

    output = json.dumps(result, ensure_ascii=False, indent=2)
    print("\n" + SEP)
    print("JSON 輸出（前3000字）:")
    print(SEP)
    print(output[:3000])
    if len(output) > 3000:
        print(f"\n... 共 {len(output)} 字，完整內容已寫入 output.json")
        with open("output.json", "w", encoding="utf-8") as f:
            f.write(output)

    return result


if __name__ == "__main__":
    self_check()
    print()
