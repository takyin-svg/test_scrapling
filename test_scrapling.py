# test_scrapling.py
from scrapling.fetchers import StealthyFetcher

SOURCES = [
    {
        "name": "東方財富-港股新聞",
        # 原 chksc.html 已 404，改用下方候选，逐个试出可用的
        "url": "https:cgsdd.html",
    },
    {
        "name": "東方財富-港股(备用)",
        "url": "https:hk.html",
    },
    {
        "name": "新浪財經-港股新聞",
        "url": "https://finance.sina.com.cn/stock/hkstock/",
    },
]

def run_test():
    print("開始測試 Scrapling StealthyFetcher 爬取能力...")

    for source in SOURCES:
        print(f"\n正在抓取: {source['name']} ({source['url']})")
        try:
            page = StealthyFetcher.fetch(
                source['url'],
                headless=True,
                network_idle=True,
            )

            # 修正1：状态码是 .status 不是 .status_code
            print(f"請求狀態碼: {page.status}")

            # 修正2：Scrapling 选择器返回的是列表，取第一个
            titles = page.css('title::text')
            title = str(titles[0]).strip() if titles else '未找到標題'
            print(f"頁面標題: {title}")

            texts = page.css('body::text').getall()
            print(f"內容預覽: {''.join(t for t in texts if t.strip())[:200]}...")

        except Exception as e:
            print(f"抓取失敗: {type(e).__name__}: {e}")

if __name__ == "__main__":
    run_test()
