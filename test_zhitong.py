import json
import re
from scrapling.fetchers import StealthySession

def test_stealthy_json_api():
    print("🚀 啟動 Scrapling StealthySession 終極測試 (API 刺客模式)...")
    
    # 首頁網址 (用來拿 Cookie 和解開防護)
    base_url = "https://www.zhitongcaijing.com/immediately.html?type=ganggu"
    # API 網址 (真正要打的 JSON 接口)
    api_url = "https://www.zhitongcaijing.com/immediately/content-list.html?type=ganggu&roll=gt"
    
    try:
        # 啟動 StealthySession (自動處理反爬與 Cookie)
        with StealthySession(headless=True) as session:
            print(f"⏳ 1. 正在拜訪首頁，建立合法身分與 Cookie...")
            session.fetch(base_url)
            print("✅ 成功獲取首頁憑證！")
            
            print(f"📡 2. 憑證掛載完成，突襲底層 JSON API...")
            # 必須加上 AJAX 偽裝標頭，否則伺服器會拒絕回傳 JSON
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": base_url,
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
            
            # 使用同一個 session 發送請求
            response = session.fetch(api_url, headers=headers)
            print(f"HTTP 狀態碼: {response.status}")
            
            # 嘗試解析純 JSON 資料
            try:
                data = json.loads(response.text)
                print("🎉 成功繞過 WAF 防火牆，取得純淨 JSON 資料！\n")
                
                # 尋找 JSON 裡的快訊列表
                items = []
                if isinstance(data, list) and len(data) > 1 and "list" in data[1]:
                    items = data[1]["list"]
                elif isinstance(data, dict) and "list" in data:
                    items = data["list"]
                else:
                    print("⚠️ JSON 結構不符預期，請檢查原始資料：")
                    print(response.text[:500])
                    return
                    
                print(f"✅ 成功萃取 {len(items)} 條 API 快訊，印出前 3 條：")
                for idx, item in enumerate(items[:3], 1):
                    raw_content = item.get("content", "")
                    
                    # 即使是 JSON，智通的內文還是包了一點 HTML，所以用正則清乾淨
                    clean_text = re.sub(r'<[^>]+>', '', raw_content).strip()
                    # 順便清掉 UI 按鈕文字
                    noise_words = ["编辑解读", "添加解读", "查看解读", "\n", "\r"]
                    for nw in noise_words:
                        clean_text = clean_text.replace(nw, "")
                        
                    time_str = item.get("create_time", "未知時間")
                    
                    print(f"【第 {idx} 條】發布時間: {time_str}")
                    print(f"📝 內容: {clean_text.strip()}")
                    print("-" * 60)
                    
            except json.JSONDecodeError:
                print("❌ 挑戰失敗，伺服器依然擋下了我們並回傳非 JSON 內容：")
                print(response.text[:500])

    except Exception as e:
        print(f"❌ 發生致命錯誤: {e}")

if __name__ == "__main__":
    test_stealthy_json_api()
