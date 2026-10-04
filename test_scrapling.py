# test_scrapling.py
import json
import xml.etree.ElementTree as ET
from scrapling.fetchers import StealthyFetcher, Fetcher

# ============ 21财经：抓首页，提取快讯 ============
def test_21jingji():
    print("\n[21财经] Fetcher 抓首页快讯")
    try:
        page = Fetcher.get("https://www.21jingji.com/")
        print("状态码:", page.status)
        title = page.css('title::text')
        print("标题:", str(title[0]).strip() if title else "无")
        # 首页快讯条目兜底选择器：含 .HK 或带时间的快讯链接
        count = 0
        for a in page.css('a'):
            t = (a.text or "").strip()
            href = a.attrib.get("href", "")
            if len(t) >= 10 and (".HK" in t or "回购" in t or "港股" in t):
                print(" -", t[:40], "|", href[:60])
                count += 1
            if count >= 8:
                break
        print(f"命中港股相关快讯 {count} 条")
    except Exception as e:
        print("抓取失败:", type(e).__name__, e)

# ============ RTHK：官方 RSS 优先，逐个候选试 ============
def test_rthk_rss():
    print("\n[RTHK] 官方 RSS 候选逐个试（Fetcher）")
    feeds = [
        "https://rthk.hk/rthk2/rss/rthk_news_ch.xml",
        "https://rthk.hk/rthk2/rss/rthk_tc_news.xml",
        "https://news.rthk.hk/rthk/ch/rss.xml",
    ]
    for u in feeds:
        try:
            page = Fetcher.get(u)
            body = page.body.decode("utf-8", "ignore") if isinstance(page.body, bytes) else str(page.body)
            root = ET.fromstring(body)
            items = root.findall(".//item")
            print(f"[OK] {page.status} 条目数={len(items)}  <- {u}")
            for it in items[:3]:
                ttl = it.findtext("title", "").strip()
                print("   -", ttl[:40])
            return  # 第一个成功就停
        except Exception as e:
            print(f"[fail] {type(e).__name__}: {e}  <- {u}")

# ============ RTHK：RSS 不中则浏览器渲染探测真实分类链接 ============
def test_rthk_render():
    print("\n[RTHK] StealthyFetcher 渲染最新新闻页，探测财经分类真实链接")
    try:
        page = StealthyFetcher.fetch(
            "https://news.rthk.hk/rthk/ch/latest-news.htm",
            headless=True, network_idle=True,
        )
        print("状态码:", page.status)
        for a in page.css('a'):
            t = (a.text or "").strip()
            href = a.attrib.get("href", "")
            if any(k in t for k in ("財經", "财经", "finance")) and href:
                print("  财经分类链接:", t, "->", href)
    except Exception as e:
        print("渲染失败:", type(e).__name__, e)

if __name__ == "__main__":
    test_21jingji()
    test_rthk_rss()
    test_rthk_render()
