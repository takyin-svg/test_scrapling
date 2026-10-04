# test_extra_sources.py
from scrapling.fetchers import StealthyFetcher, Fetcher

SOURCES = [
    {
        "name": "Yahoo 財經",
        "url": "https://hk.finance.yahoo.com/",
        "fetcher": "stealth",
        "note": "已停運財經內容，預期無港股新聞",
    },
    {
        "name": "21世紀經濟報道",
        "url": "https://www.21jingji.com/channel/hkstock.html",
        "fetcher": "stealth",
    },
    {
        "name": "金吾財訊",
        "url": "https://www.jinwucaixun.com/",
        "fetcher": "fetcher",
    },
    {
        "name": "Reuters 路透社",
        "url": "https://www.reuters.com/markets/asia/",
        "fetcher": "fetcher",
    },
    {
        "name": "RTHK 財經",
        "url": "https://news.rthk.hk/rthk/ch/component/k2/?categories=116,120,121",
        "fetcher": "stealth",
    },
    {
        "name": "智通財經",
        "url": "https://www.zhitongcaijing.com/",
        "fetcher": "stealth",
    },
    {
        "name": "格隆匯",
        "url": "https://www.gelonghui.com/",
        "fetcher": "stealth",
    },
    {
        "name": "金十數據",
        "url": "https://www.jin10.com/",
        "fetcher": "stealth",
    },
]


def run_test():
    print("開始測試額外新聞源...")

    for source in SOURCES:
        print(f"\n正在抓取: {source['name']} ({source['url']})")
        if source.get("note"):
            print(f"備註: {source['note']}")

        try:
            if source["fetcher"] == "stealth":
                page = StealthyFetcher.fetch(
                    source["url"],
                    headless=True,
                    network_idle=True,
                )
            else:
                page = Fetcher.get(source["url"])

            print(f"狀態碼: {page.status}")

            titles = page.css("title::text")
            title = str(titles[0]).strip() if titles else "未找到標題"
            print(f"頁面標題: {title}")

            texts = page.css("body::text").getall()
            preview = "".join(t for t in texts if t.strip())[:200]
            print(f"內容預覽: {preview}...")

        except Exception as e:
            print(f"抓取失敗: {type(e).__name__}: {e}")


if __name__ == "__main__":
    run_test()
