# test_zhitong_time.py
import re
from datetime import datetime, timezone, timedelta
from scrapling.fetchers import DynamicSession

HKT = timezone(timedelta(hours=8))

def parse_time_str(text: str) -> tuple[int, str]:
    now = datetime.now(HKT)
    text = str(text).strip()
    if not text:
        return 0, ""

    # 1. 剛剛 / 刚刚
    if any(k in text for k in ["剛", "刚"]):
        ts = int(now.timestamp())
        return ts, now.strftime('%Y-%m-%d %H:%M:%S')

    # 2. 相對時間：分鐘前 / 小時前 (支援繁簡)
    m_min = re.search(r'(\d+)\s*(?:分鐘|分钟|分)\s*前', text)
    if m_min:
        ts = int(now.timestamp()) - int(m_min.group(1)) * 60
        return ts, datetime.fromtimestamp(ts, HKT).strftime('%Y-%m-%d %H:%M:%S')

    m_hr = re.search(r'(\d+)\s*(?:小時|小时|h)\s*前', text)
    if m_hr:
        ts = int(now.timestamp()) - int(m_hr.group(1)) * 3600
        return ts, datetime.fromtimestamp(ts, HKT).strftime('%Y-%m-%d %H:%M:%S')

    # 3. 昨天 / 前天
    m_yest = re.search(r'(?:昨[天日]|前[天日])\s*(\d{1,2}):(\d{1,2})', text)
    if m_yest:
        days_ago = 2 if "前" in m_yest.group(0) else 1
        target_day = now - timedelta(days=days_ago)
        h, m = int(m_yest.group(1)), int(m_yest.group(2))
        dt = target_day.replace(hour=h, minute=m, second=0, microsecond=0)
        return int(dt.timestamp()), dt.strftime('%Y-%m-%d %H:%M:%S')

    # 4. YYYY-MM-DD HH:MM 或 MM-DD HH:MM
    m_date_time = re.search(r'(?:(\d{4})[-/])?(\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?', text)
    if m_date_time:
        year = int(m_date_time.group(1)) if m_date_time.group(1) else now.year
        month = int(m_date_time.group(2))
        day = int(m_date_time.group(3))
        hour = int(m_date_time.group(4))
        minute = int(m_date_time.group(5))
        second = int(m_date_time.group(6)) if m_date_time.group(6) else 0
        dt = datetime(year, month, day, hour, minute, second, tzinfo=HKT)
        return int(dt.timestamp()), dt.strftime('%Y-%m-%d %H:%M:%S')

    # 5. 純當日時間 18:30 或 今天 18:30 (注意排除前面有日期的情況)
    m_today = re.search(r'(?:(?:今[天日])\s*)?(\b\d{1,2}):(\d{1,2})(?::(\d{1,2}))?\b', text)
    if m_today and not re.search(r'\d{1,2}[-/月]\d{1,2}', text):
        h, m = int(m_today.group(1)), int(m_today.group(2))
        s = int(m_today.group(3)) if m_today.group(3) else 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
            return int(dt.timestamp()), dt.strftime('%Y-%m-%d %H:%M:%S')

    # 6. 中文日期 10月9日 18:30 或 10月9日
    m_cn = re.search(r'(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{1,2}))?', text)
    if m_cn:
        year = now.year
        month = int(m_cn.group(1))
        day = int(m_cn.group(2))
        hour = int(m_cn.group(3)) if m_cn.group(3) else 16
        minute = int(m_cn.group(4)) if m_cn.group(4) else 0
        dt = datetime(year, month, day, hour, minute, 0, tzinfo=HKT)
        return int(dt.timestamp()), dt.strftime('%Y-%m-%d %H:%M:%S')

    return 0, ""

def test_fetch_page(page, page_num):
    url = f"https://m.zhitongcaijing.com/market.html?page={page_num}"
    print(f"\n🚀 正在測試加載第 {page_num} 頁: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=25000)
    
    try:
        page.wait_for_selector('a[href*="detail"], a[href*="content_id"]', timeout=8000)
    except Exception:
        print("  ⚠️ 等待新聞列表超時，嘗試直接提取...")

    items = page.evaluate("""() => {
        const results = [];
        const seenHrefs = new Set();
        const aTags = Array.from(document.querySelectorAll('a[href*="detail"], a[href*="content_id"], a[href*="/content/"]'));
        
        for (const a of aTags) {
            const title = (a.innerText || a.textContent || '').trim();
            const href = a.getAttribute('href') || '';
            if (title.length < 8 || !href || seenHrefs.has(href)) continue;
            seenHrefs.add(href);

            // 向上找到整個新聞卡片的容器
            let card = a.closest('li') || a.closest('div.item') || a.closest('div.list-item') || a.closest('section');
            if (!card) {
                let p = a.parentElement;
                while (p && p !== document.body) {
                    if (p.innerText && p.innerText.length > title.length + 3) {
                        card = p;
                        break;
                    }
                    p = p.parentElement;
                }
            }

            // 1. 優先嘗試從專門的時間標籤抽取
            let rawTime = '';
            if (card) {
                const timeEl = card.querySelector('.time, .date, [class*="time"], [class*="date"], span.time, .pubtime');
                if (timeEl) {
                    rawTime = (timeEl.innerText || timeEl.textContent || '').trim();
                }
            }

            // 2. 若無專屬標籤，從卡片文字做正則提煉
            const cardText = card ? (card.innerText || card.textContent || '') : title;
            if (!rawTime) {
                const match = cardText.match(/(?:\\d{4}[-/])?\\d{1,2}[-/]\\d{1,2}\\s+\\d{1,2}:\\d{1,2}(?::\\d{1,2})?|(?:今[天日]|昨[天日]|前[天日])\\s*\\d{1,2}:\\d{1,2}|\\b\\d{1,2}:\\d{1,2}(?::\\d{1,2})?\\b|\\d{1,2}月\\d{1,2}日(?:\\s*\\d{1,2}:\\d{1,2})?|\\d+\\s*(?:分鐘|分钟|小時|小时|分|h)\\s*前|剛剛|刚刚/);
                if (match) {
                    rawTime = match[0];
                }
            }

            results.push({
                title: title.replace(/\\s+/g, ' '),
                href: href,
                raw_time: rawTime,
                card_snippet: cardText.slice(0, 100).replace(/\\s+/g, ' ')
            });
            if (results.length >= 5) break; // 取前 5 條檢驗
        }
        return results;
    }""")

    print(f"📦 第 {page_num} 頁成功解析到 {len(items)} 則新聞，檢驗時間提取：")
    for idx, it in enumerate(items, 1):
        ts, parsed_str = parse_time_str(it['raw_time'])
        status = "✅ 成功" if ts > 0 else "❌ 失敗"
        print(f"  [{idx}] {status} | 原文時間: '{it['raw_time']}' -> 解析時間: {parsed_str} (ts: {ts})")
        print(f"      標題: {it['title'][:35]}...")

def main():
    with DynamicSession(headless=True, stealth=True, timeout=30000) as sess:
        def handler(page):
            page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ico}", lambda r: r.abort())
            test_fetch_page(page, 1)
            test_fetch_page(page, 2)

        # 加入 wait_until="domcontentloaded" 確保秒級啟動
        sess.fetch("https://m.zhitongcaijing.com/market.html", wait_until="domcontentloaded", page_action=handler)

if __name__ == "__main__":
    main()
