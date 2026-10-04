# test_scrapling.py  (覆盖)
import json
from scrapling.fetchers import StealthyFetcher, Fetcher

def test_sina():
    print("\n[新浪-港股] 用 StealthyFetcher (浏览器)")
    page = StealthyFetcher.fetch(
        "https://finance.sina.com.cn/stock/hkstock/",
        headless=True, network_idle=True,
    )
    print("状态码:", page.status)
    titles = page.css('title::text')
    print("标题:", str(titles[0]).strip() if titles else "无")

def test_eastmoney():
    print("\n[东方财富-新闻列表] 用 Fetcher (HTTP) 打官方 JSON 接口")
    # 实测可用：column=350 为财经滚动；换成港股专栏见下方说明
    url = (
        "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        "?client=web&biz=web_news_col&column=350&order=1"
        "&needInteractData=0&page_index=1&page_size=20"
        "&req_trace=1700000000000"   # 必填，随便给个时间戳
    )
    page = Fetcher.get(url)          # JSON 接口不需要浏览器，普通抓取即可
    print("状态码:", page.status)
    data = json.loads(page.body)     # 原始响应体解析成 dict
    print("code:", data.get("code"), data.get("message"))
    for it in data["data"]["list"][:5]:
        print(" -", it["showTime"], it["title"])

if __name__ == "__main__":
    test_eastmoney()
    test_sina()
