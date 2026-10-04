# test_scrapling.py
from scrapling.fetchers import StealthyFetcher

# 目標網站列表
SOURCES = [
    {
        "name": "東方財富-港股新聞",
        "url": "https://stock.eastmoney.com/a/chksc.html"
    },
    {
        "name": "新浪財經-港股新聞",
        "url": "https://finance.sina.com.cn/stock/hkstock/"
    }
]

def run_test():
    print("🚀 開始測試 Scrapling StealthyFetcher 爬取能力...")
    
    for source in SOURCES:
        print(f"\n📡 正在抓取: {source['name']} ({source['url']})")
        try:
            # 使用隱身模式抓取，自動繞過常見反爬與驗證
            page = StealthyFetcher.fetch(
                source['url'],
                headless=True,         # 無頭瀏覽器模式
                network_idle=True,     # 等待網絡空閒（確保 JS 渲染完成）
                auto_retry=True        # 失敗自動重試
            )
            
            # 檢查請求狀態
            print(f"✅ 請求狀態碼: {page.status_code}")
            
            # 提取並打印頁面標題（驗證是否拿到真實內容而非驗證頁面）
            title = page.css('title::text').get()
            print(f"📄 頁面標題: {title.strip() if title else '未找到標題'}")
            
            # 簡單打印前 200 個字符驗證內容
            body_text = page.css('body::text').getall()
            print(f"📝 內容預覽: {''.join(body_text)[:200].strip()}...")

        except Exception as e:
            print(f"❌ 抓取失敗: {str(e)}")

if __name__ == "__main__":
    run_test()
