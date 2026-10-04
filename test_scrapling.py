# test_rthk_finance.py
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch(
    "https://news.rthk.hk/rthk/ch/latest-news.htm",
    headless=True, network_idle=True,
)
print("狀態碼:", page.status)

seen = set()
for a in page.css("a"):
    href = a.attrib.get("href", "")
    text = (a.text or "").strip()
    if not href or not text or href in seen:
        continue
    seen.add(href)
    if "財經" in text or "finance" in href.lower():
        print("  財經入口:", text, "->", href)

# 兜底：把所有含 /ch/ 的分類頁都打出來
print("\n全部 /ch/ 分類頁:")
for h in sorted(seen):
    if "/ch/" in h and not h.startswith("http"):
        print(" ", "https://news.rthk.hk" + h)
