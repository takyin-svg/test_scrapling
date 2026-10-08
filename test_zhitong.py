import requests
import re
import hashlib
import json

def test_zhitong_api():
    url = "https://www.zhitongcaijing.com/immediately/content-list.html?type=ganggu&roll=gt"
    
    # 🚨 升級偽裝：加入 X-Requested-With 告訴伺服器這是一個 AJAX 請求
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.zhitongcaijing.com/immediately.html?type=ganggu"
    }

    print("🚀 開始測試抓取智通財經 7x24 快訊 API...")
    print(f"🔗 目標網址: {url}")
    print("=" * 60)

    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"📡 HTTP 狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            try:
                # 嘗試解析 JSON
                data = response.json()
            except json.JSONDecodeError:
                # 🚨 如果不是 JSON，直接印出伺服器到底回傳了什麼文字！
                print("❌ 伺服器回傳的不是 JSON！以下是前 1000 個字元的原始內容：")
                print("-" * 40)
                print(response.text[:1000])
                print("-" * 40)
                return
            
            # 解析智通財經特有的 JSON 結構
            items = []
            if isinstance(data, list) and len(data) > 1 and "list" in data[1]:
                items = data[1]["list"]
            elif isinstance(data, dict) and "list" in data:
                items = data["list"]
            else:
                print("⚠️ 無法識別的 JSON 結構，原始回傳內容前 500 字元：")
                print(json.dumps(data, ensure_ascii=False)[:500])
                return

            print(f"✅ 成功獲取 {len(items)} 條原始快訊！\n")
            
            # 測試過濾與清理邏輯
            valid_count = 0
            for idx, item in enumerate(items[:5], 1):
                raw_content = item.get("content", "")
                
                # 清除 HTML 標籤
                clean_text = re.sub(r'<[^>]+>', '', raw_content).strip()
                
                if len(clean_text) > 15:
                    valid_count += 1
                    content_hash = hashlib.md5(clean_text.encode('utf-8')).hexdigest()[:10]
                    virtual_url = f"https://www.zhitongcaijing.com/immediately.html#flash_{content_hash}"
                    
                    print(f"【第 {idx} 條】")
                    print(f"📝 內容: {clean_text}")
                    print(f"🔗 虛擬網址: {virtual_url}")
                    print("-" * 60)
            
            print(f"🎉 測試成功！")
        else:
            print(f"❌ 請求失敗，伺服器回應: {response.text}")
            
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    test_zhitong_api()
