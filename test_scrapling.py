# test_scrapling.py
# Scrapling 全源自省 + 诊断测试版
# 目标：钉死 API(status/status_code/body/text)、暴露每个源真实 DOM、验证 timeout 单位
import json
import re
import time
import inspect
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

import scrapling
from scrapling.fetchers import Fetcher, StealthyFetcher

SEP = "=" * 64

# ============ 源配置 ============
YAHOO_STOCKS = ["0700.HK", "1810.HK", "1211.HK", "0388.HK", "0005.HK", "3690.HK"]

SOURCES = [
    {"name": "东方财富", "kind": "json",   "fetcher": "fetcher",
     "timeout_sec": 20,
     "url": "https://api.eastmoney.com/dataapi/xinwen/list?"
            "type=100&pageIndex=1&pageSize=50&keyword=%E6%B8%AF%E8%82%A1"},
    {"name": "Yahoo-RSS", "kind": "yahoo_rss", "fetcher": "fetcher", "timeout_sec": 15},
    {"name": "新浪港股", "kind": "html", "fetcher": "stealth", "timeout_sec": 40,
     "url": "https://finance.sina.com.cn/stock/hkstock/"},
    {"name": "智通财经", "kind": "html", "fetcher": "stealth", "timeout_sec": 60,
     "url": "https://www.zhitongcaijing.com/"},
    {"name": "格隆汇", "kind": "html", "fetcher": "stealth", "timeout_sec": 40,
     "url": "https://www.gelonghui.com/"},
    {"name": "金十数据", "kind": "html", "fetcher": "stealth", "timeout_sec": 40,
     "url": "https://www.jin10.com/"},
]

# ============ 自省层 ============
def self_check():
    print(SEP)
    print("Scrapling 自省")
    print(SEP)
    print("scrapling 版本:", getattr(scrapling, "__version__", "未知"))

    # 试抓一个确定能返回的小页面，检查 Response 真实属性
    probe_url = "https://httpbin.org/html"
    try:
        page = Fetcher.get(probe_url, timeout=20)
    except Exception as e:
        print("[自省] 抓取 httpbin 失败:", type(e).__name__, str(e)[:120])
        return

    print("Response 类型:", type(page).__name__)
    for attr in ("status", "status_code", "body", "text", "reason", "url"):
        has = hasattr(page, attr)
        val = ""
        if has:
            v = getattr(page, attr)
            if isinstance(v, (bytes, str)):
                val = f"<len={len(v)}>"
            else:
                val = repr(v)
        print(f"  属性 {attr:12s}: 存在={has}  值={val}")

    # 探测 css_first 是否真的可用
    for meth in ("css_first", "css", "xpath"):
        print(f"  方法 {meth:10s}: 可用={hasattr(page, meth)}")

# ============ 防御式工具 ============
def get_status(page):
    for a in ("status_code", "status"):
        if hasattr(page, a):
            try:
                return int(getattr(page, a))
            except Exception:
                pass
    return None

def get_body(page):
    # 统一返回 str
    if hasattr(page, "text") and getattr(page, "text"):
        t = page.text
        return t.decode("utf-8", "ignore") if isinstance(t, bytes) else str(t)
    if hasattr(page, "body") and getattr(page, "body"):
        b = page.body
        return b.decode("utf-8", "ignore") if isinstance(b, bytes) else str(b)
    return ""

def css_first(el, sel):
    """兼容取第一个元素，绝不用 css_first()"""
    try:
        found = el.css(sel)
    except Exception:
        return None
    if not found:
        return None
    # .first 优先
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

# ============ 诊断器 ============
def diagnose(page, name):
    """解析 0 条时，把真实结构打印出来"""
    body = get_body(page)
    print(f"  [诊断] 正文长度: {len(body)}")
    title = css_first(page, "title")
    print(f"  [诊断] 页面标题: {get_text(title)[:50]}")
    for sel in ("article", "li", "a", "h2", "h3", "time"):
        try:
            n = len(page.css(sel))
        except Exception:
            n = -1
        print(f"  [诊断] 命中 <{sel}>: {n}")
    print("  [诊断] 候选链接样本(文字>=10):")
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
        print("    (无任何含文字链接 -> SPA 空壳，HTML 路
