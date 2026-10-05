#!/usr/bin/env python3
"""
港股量化新聞源探路腳本 (Probe Sources)
使用 Scrapling StealthyFetcher (基於 Patchright) 探測海外 IP 下的存活性。
"""

import re
import sys
import time
import random
from typing import Dict, List, Any
from scrapling.fetchers import StealthyFetcher

# 20 個待探測的候選源頭
SOURCES = [
    # 1. 已知存活基準
    {"name": "新浪港股", "url": "https://finance.sina.com.cn/stock/hkstock/", "category": "存活基準"},
    {"name": "智通財經", "url": "https://www.zhitongcaijing.com/", "category": "存活基準"},
    {"name": "格隆匯", "url": "https://www.gelonghui.com/", "category": "存活基準"},
    
    # 2. 香港本地財經
    {"name": "AASTOCKS (阿斯達克)", "url": "http://www.aastocks.com/tc/stocks/news/aafn/latest-news", "category": "本地財經"},
    {"name": "ETNet (經濟通)", "url": "https://www.etnet.com.hk/www/tc/stocks/ci_news.php", "category": "本地財經"},
    {"name": "HKET (香港經濟日報)", "url": "https://inews.hket.com/sdir/investment", "category": "本地財經"},
    {"name": "Quamnet (華富財經)", "url": "https://www.quamnet.com/news", "category": "本地財經"},
    {"name": "信報財經即時新聞", "url": "https://www.hkej.com/instantnews/hongkong", "category": "本地財經"},
    {"name": "明報即時財經", "url": "https://finance.mingpao.com/fin/instantf1.php", "category": "本地財經"},
    
    # 3. 國際財經 (海外友善)
    {"name": "Yahoo Finance (香港)", "url": "https://hk.finance.yahoo.com/topic/hong-kong/", "category": "國際財經"},
    {"name": "Investing.com HK", "url": "https://hk.investing.com/news/stock-market-news", "category": "國際財經"},
    {"name": "Reuters Asia", "url": "https://www.reuters.com/markets/asia/", "category": "國際財經"},
    {"name": "CNBC Asia-Pacific", "url": "https://www.cnbc.com/asia-markets/", "category": "國際財經"},
    {"name": "MarketWatch Asia", "url": "https://www.marketwatch.com/markets/asia", "category": "國際財經"},
    {"name": "Nikkei Asia Markets", "url": "https://asia.nikkei.com/Business/Markets", "category": "國際財經"},
    {"name": "Bloomberg Asia", "url": "https://www.bloomberg.com/asia", "category": "國際財經"},
    
    # 4. 券商與交易所官方
    {"name": "HKEX 披露易", "url": "https://www.hkexnews.hk/index_c.htm", "category": "券商與官方"},
    {"name": "富途牛牛網頁版", "url": "https://news.futunn.com/hk", "category": "券商與官方"},
    {"name": "長橋資訊 (Longbridge)", "url": "https://longbridgehk.com/news", "category": "券商與官方"},
    {"name": "華盛通資訊", "url": "https://www.hstong.com/news", "category": "券商與官方"},
]

WAF_PATTERNS = [
    "just a moment",
    "attention required",
    "cloudflare",
    "access denied",
    "security check",
    "ddos-guard",
    "human verification",
    "robot or human",
    "verify you are human",
    "ip blocked",
    "403 forbidden",
    "429 too many requests",
]

def extract_title(html: str) -> str:
    """提取網頁 Title 標籤文字"""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        return re.sub(r"\s+", " ", title)
    return ""

def check_waf_block(status_code: int, title: str, snippet: str) -> (bool, str):
    """判斷是否遭遇 WAF 或狀態碼異常"""
    if status_code in (403, 429, 503):
        return True, f"HTTP {status_code} 異常狀態碼"
    
    combined = (title + " " + snippet).lower()
    for pattern in WAF_PATTERNS:
        if pattern in combined:
            return True, f"命中 WAF/防護特徵詞: '{pattern}'"
            
    if not title and len(snippet.strip()) < 50:
        return True, "頁面內容過少或無 Title"
        
    return False, ""

def test_source(item: Dict[str, str], timeout_ms: int = 45000) -> Dict[str, Any]:
    url = item["url"]
    start_time = time.time()
    result = {
        "name": item["name"],
        "category": item["category"],
        "url": url,
        "status_code": 0,
        "latency_sec": 0.0,
        "title": "",
        "is_alive": False,
        "reason": "",
    }
    
    try:
        # 使用 Scrapling StealthyFetcher 抓取
        response = StealthyFetcher.fetch(url, timeout=timeout_ms, headless=True)
        elapsed = round(time.time() - start_time, 2)
        result["latency_sec"] = elapsed
        
        status = getattr(response, "status", 200)
        html_text = getattr(response, "text", "") or ""
        result["status_code"] = status
        
        title = extract_title(html_text)
        snippet = html_text[:300]
        result["title"] = title[:80] if title else "無標題"
        
        is_blocked, reason = check_waf_block(status, title, snippet)
        if is_blocked:
            result["is_alive"] = False
            result["reason"] = reason
        else:
            result["is_alive"] = True
            result["reason"] = "正常回應"
            
    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        result["latency_sec"] = elapsed
        result["is_alive"] = False
        err_msg = str(e).split("\n")[0]
        result["reason"] = f"例外錯誤: {err_msg[:60]}"
        
    return result

def main():
    print("=" * 70)
    print("🚀 港股量化爬蟲環境探測 (Probe Sources)")
    print(f"總計探測源頭數量: {len(SOURCES)} | 逾時門檻: 45000ms")
    print("遵行友善爬取原則：各請求間隨機延遲 3.0 ~ 7.0 秒")
    print("=" * 70)
    
    results = []
    
    for i, item in enumerate(SOURCES, 1):
        print(f"\n[{i}/{len(SOURCES)}] 正在探測: {item['name']} ({item['url']})...")
        res = test_source(item)
        results.append(res)
        
        status_icon = "✅ 存活" if res["is_alive"] else "❌ 阻擋/失敗"
        print(f" -> 結果: {status_icon} | Code: {res['status_code']} | 耗時: {res['latency_sec']}s")
        print(f" -> Title/備註: {res['title']} | 原因: {res['reason']}")
        
        # 友善爬取隨機延遲 (最後一個站點不需延遲)
        if i < len(SOURCES):
            delay = round(random.uniform(3.0, 7.0), 2)
            print(f" -> [友善延遲] 等待 {delay} 秒後繼續下一個目標...")
            time.sleep(delay)
            
    # 印出最終報表
    print("\n" + "=" * 90)
    print("📊 港股新聞源探測存活報告 (GitHub Actions 美國機房 IP)")
    print("=" * 90)
    
    success_count = sum(1 for r in results if r["is_alive"])
    print(f"測試總數: {len(results)} | 成功存活: {success_count} | 失敗/受阻: {len(results) - success_count}\n")
    
    report_lines = [
        "| 分類 | 源頭名稱 | 存活狀態 | HTTP | 耗時(s) | 網頁 Title / 失敗原因 |",
        "| :--- | :--- | :---: | :---: | :---: | :--- |"
    ]
    
    for r in results:
        status_tag = "✅ 成功" if r["is_alive"] else "❌ 失敗"
        desc = r["title"] if r["is_alive"] else r["reason"]
        # 清理管線符號避免 Markdown 表格錯位
        clean_desc = desc.replace("|", "-")
        report_lines.append(f"| {r['category']} | {r['name']} | {status_tag} | {r['status_code']} | {r['latency_sec']}s | {clean_desc} |")
        
    markdown_report = "\n".join(report_lines)
    print(markdown_report)
    print("=" * 90)
    
    # 寫入 probe_report.md 供 CI Summary 或下載
    with open("probe_report.md", "w", encoding="utf-8") as f:
        f.write("# 港股新聞源探測存活報告\n\n")
        f.write(f"- 探測時間: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
        f.write(f"- 存活率: {success_count}/{len(results)}\n\n")
        f.write(markdown_report)
        f.write("\n")

if __name__ == "__main__":
    main()
