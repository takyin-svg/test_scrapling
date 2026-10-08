from scrapling.fetchers import StealthyFetcher
import hashlib

def test_zhitong_html():
    url = "https://www.zhitongcaijing.com/immediately.html?type=ganggu"
    print("🚀 開始測試抓取智通財經 7x24 快訊 (HTML + XPath 穿透版)...")
    
    try:
        # 1. 使用 StealthyFetcher 抓取網頁 (完美模擬 scraper.py 的行為)
        print("⏳ 正在啟動無頭瀏覽器加載網頁，請稍候...")
        response = StealthyFetcher.fetch(url, timeout=30000, headless=True)
        print(f"📡 HTTP 狀態碼: {getattr(response, 'status', 200)}")
        
        # 2. 測試我們找出的精準選擇器
        selectors = ["div.allday-item-content", "div.allday-item"]
        elements = None
        for sel in selectors:
            elements = response.css(sel)
            if elements:
                print(f"🎯 成功命中選擇器: {sel}")
                break
        
        if not elements:
            print("❌ 找不到任何快訊區塊！")
            return

        print(f"✅ 成功找到 {len(elements)} 條原始快訊區塊！\n")
        
        # 3. 測試文字提取與過濾 (測試前 5 條)
        valid_count = 0
        for idx, el in enumerate(elements[:5], 1):
            # 🚨 核心測試：使用 xpath 穿透所有子標籤 (b, div, span) 提取深層文字
            raw_text = "".join(el.xpath(".//text()").getall())
            clean_text = raw_text.strip()
            
            # 過濾網頁按鈕雜訊
            skip_words = ["编辑解读", "添加解读", "查看解读"]
            for w in skip_words:
                clean_text = clean_text.replace(w, "")
            clean_text = clean_text.strip()
            
            if len(clean_text) > 15:
                valid_count += 1
                content_hash = hashlib.md5(clean_text.encode('utf-8')).hexdigest()[:10]
                virtual_url = f"{url}#flash_{content_hash}"
                
                print(f"【第 {idx} 條】")
                print(f"📝 穿透抓取內容: {clean_text}")
                print(f"🔗 虛擬網址 (Hash): {virtual_url}")
                print("-" * 60)
        
        if valid_count > 0:
            print("🎉 HTML + XPath 穿透測試大成功！這證明網頁裡確實驗藏著資料，只是之前沒被挖出來。")
            print("👉 現在你可以安心
