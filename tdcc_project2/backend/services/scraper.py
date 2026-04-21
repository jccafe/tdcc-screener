import pandas as pd
import requests
import re
import yfinance as yf
from io import StringIO
from database import SessionLocal, TDCCData
import datetime
import random
import time

TDCC_URL = "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5"

def _generate_mock_historical_data(db, df, latest_date, weeks=12, progress_callback=None):
    """
    Since actual historical data is not easily available via the simple URL,
    we mock the past `weeks` to demonstrate the 'continuous' feature.
    """
    # Mock date 1 to `weeks`
    mock_dates = []
    for w in range(1, weeks + 1):
        d = (datetime.datetime.strptime(latest_date, "%Y%m%d") - datetime.timedelta(days=7*w)).strftime("%Y%m%d")
        mock_dates.append((d, w))
    
    records_to_insert = []
    total_mock_weeks = len(mock_dates)
    start_time_mock = time.time()
    
    for idx, (date_str, week_idx) in enumerate(mock_dates):
        if progress_callback:
            percent = int((idx / max(1, total_mock_weeks)) * 100)
            
            eta = -1
            if idx > 0:
                elapsed = time.time() - start_time_mock
                avg = elapsed / idx
                eta = int(avg * (total_mock_weeks - idx))
            
            progress_callback(percent, eta, idx, total_mock_weeks)

        df_mock = df.copy()
        df_mock['date'] = date_str
        
        # Add some random variations
        def modify_people(row, w_idx):
            # 只有尾數為 0 或 5 的股票才模擬籌碼集中
            if not (row['stock_id'].endswith('0') or row['stock_id'].endswith('5')):
                return row['people']
            # 散戶人數模擬：每週隨機增加 1%~6%
            if row['level'] <= 9:
                variation = 1 + random.uniform(0.01, 0.06) * w_idx
                return int(row['people'] * variation)
            return row['people']
            
        def modify_percent(row, w_idx):
            if not (row['stock_id'].endswith('0') or row['stock_id'].endswith('5')):
                return row['percent']
            # 大戶持股模擬：每週隨機減少 1%~4% (因為最新的資料在 df 裡，要往回推)
            if row['level'] >= 14:
                variation = 1 - random.uniform(0.01, 0.04) * w_idx
                return max(0.01, row['percent'] * variation)
            return row['percent']
            
        df_mock['people'] = df_mock.apply(lambda r: modify_people(r, week_idx), axis=1)
        df_mock['percent'] = df_mock.apply(lambda r: modify_percent(r, week_idx), axis=1)
        records_to_insert.extend(df_mock.to_dict(orient='records'))
        
    chunk_size = 50000
    for i in range(0, len(records_to_insert), chunk_size):
        db.bulk_insert_mappings(TDCCData, records_to_insert[i:i+chunk_size])
        db.commit()
        
    if progress_callback:
        progress_callback(100, 0, total_mock_weeks, total_mock_weeks)
        
    print("Mock historical data generated for demonstration.")

def download_and_update_tdcc(weeks=12, progress_callback=None):
    print("Downloading TDCC data...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Disable SSL warnings and use verify=False due to TDCC certificate issues
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    res = requests.get(TDCC_URL, headers=headers, verify=False)
    res.encoding = 'utf-8'
    
    try:
        # TDCC CSV data may sometimes contain header info rows that cause parsing errors.
        # We use on_bad_lines='skip' to ignore these rows and focus on the actual table.
        df = pd.read_csv(StringIO(res.text), on_bad_lines='skip', engine='python')
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return {"status": "error", "message": f"CSV parsing failed: {e}"}
    
    if df.empty:
        print("Error: Downloaded TDCC data is empty.")
        return {"status": "error", "message": "Downloaded TDCC data is empty."}
        
    # Check if column count matches
    # TDCC CSV Columns typically: 資料日期, 證券代號, 持股分級, 人數, 股數, 占集保庫存數比例%
    if len(df.columns) == 6:
        df.columns = ["date", "stock_id", "level", "people", "shares", "percent"]
    else:
        # If columns count doesn't match, it might be due to incorrect skip logic.
        # Try to find the actual data row.
        print(f"Warning: CSV columns count {len(df.columns)} != 6. Attempting to fix...")
        # (Additional logic could go here if needed, but for now we stop and report)
        return {"status": "error", "message": f"Data columns mismatch: expected 6, found {len(df.columns)}"}
    df['date'] = df['date'].astype(str)
    df['stock_id'] = df['stock_id'].astype(str)
    
    # Filter only 4-digit stock IDs to drastically reduce DB size and speed up mock generation
    # Also trim any whitespace
    df['stock_id'] = df['stock_id'].str.strip()
    df = df[df['stock_id'].str.len() == 4]
    
    if df.empty:
        print("Error: No 4-digit stock IDs found in the data.")
        # Debug: show some original stock IDs
        return {"status": "error", "message": "No valid stock data found after filtering."}
    
    db = SessionLocal()
    latest_date = df['date'].iloc[0]
    
    count = db.query(TDCCData.date).distinct().count()
    existing = db.query(TDCCData).filter(TDCCData.date == latest_date).first()
    
    if existing:
        # We already have the latest week.
        if count >= weeks + 1:
            print(f"Data for {latest_date} already exists and length is sufficient ({count} >= {weeks + 1}).")
            db.close()
            return {"status": "already_updated", "date": latest_date}
        else:
            print(f"Expanding mock history... User requested {weeks} weeks, but only {count-1} exist.")
            db.query(TDCCData).delete()
            db.bulk_insert_mappings(TDCCData, df.to_dict(orient='records'))
            db.commit()
            _generate_mock_historical_data(db, df, latest_date, weeks=weeks, progress_callback=progress_callback)
            db.close()
            return {"status": "success", "date": latest_date}
            
    else:
        # We don't have the latest week. This is a NEW update!
        print(f"Inserting new TDCC data for {latest_date} into database...")
        # Do NOT delete existing data! Just append the new week.
        db.bulk_insert_mappings(TDCCData, df.to_dict(orient='records'))
        db.commit()
        
        # If the DB was completely empty before this, generate initial mock data.
        if count == 0 and weeks > 0:
            print(f"Initial setup: Generating mock historical data for {weeks} weeks...")
            _generate_mock_historical_data(db, df, latest_date, weeks=weeks, progress_callback=progress_callback)
            
        db.close()
        print("Update complete.")
        return {"status": "success", "date": latest_date}

def _download_ticker_chunk(chunk, period="2y"):
    """
    內部的線程任務：下載一小塊標的
    """
    import yfinance as yf
    try:
        # 使用 threads=True 是 yfinance 內建的併發，但我們外面還有一層
        data = yf.download(chunk, period=period, group_by='ticker', progress=False, threads=False)
        return data
    except Exception as e:
        print(f"下載區塊出錯: {e}")
        return None

def batch_download_prices(stock_ids, period="2y"):
    """
    真正的多線程並行下載器
    """
    if not stock_ids:
        return {}
        
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import logging
    logging.getLogger('yfinance').setLevel(logging.CRITICAL)
    
    # 建立所有可能的 tickers
    all_tickers = []
    for sid in stock_ids:
        all_tickers.append(f"{sid}.TW")
        all_tickers.append(f"{sid}.TWO")
        
    # 將標的分塊，每塊 20 個標的
    chunk_size = 20
    chunks = [all_tickers[i:i + chunk_size] for i in range(0, len(all_tickers), chunk_size)]
    
    all_raw_data = []
    # 樹莓派建議 4-8 線程，PC 可以更多
    max_workers = 8
    
    print(f"啟動多線程下載器: {len(stock_ids)} 隻股票, {max_workers} 併發處理中...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {executor.submit(_download_ticker_chunk, chunk, period): chunk for chunk in chunks}
        
        for future in as_completed(future_to_chunk):
            res = future.result()
            if res is not None and not res.empty:
                all_raw_data.append(res)
    
    # 整合與處理數據
    final_cache = {}
    for data in all_raw_data:
        # 如果是 MultiIndex (多個 Tickers)
        if isinstance(data.columns, pd.MultiIndex):
            for t in data.columns.get_level_values(0).unique():
                ticker_df = data[t].dropna(subset=['Close'])
                if not ticker_df.empty:
                    sid = t.split('.')[0]
                    # 預計算 MA20
                    ticker_df = ticker_df.copy()
                    ticker_df.index = ticker_df.index.tz_localize(None).normalize()
                    ticker_df['MA20'] = ticker_df['Close'].rolling(window=20).mean()
                    final_cache[sid] = ticker_df
        else:
            # 如果是單一 Ticker
            ticker_df = data.dropna(subset=['Close'])
            # 嘗試從數據中找 Ticker 名稱 (yf 有時會存在 metadata)
            # 這裡簡化處理，因為大部分情況下 batch 下載會回傳 MultiIndex
            pass

    print(f"下載完成！成功整合 {len(final_cache)} 隻股票數據。")
    return final_cache


def _contains_chinese(text: str):
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)


def get_tw_yahoo_local_info(stock_id: str):
    """
    從 Yahoo 奇摩股市抓取名稱與產業
    """
    try:
        url = f"https://tw.stock.yahoo.com/quote/{stock_id}.TW"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        if res.status_code == 200:
            # 1. 抓取名稱 (多重保險模式)
            raw_html = res.text
            
            # 模式 A: <title>名稱 (代號) - 股價 ...
            match_a = re.search(r'<title>([^<]+?)\s*\('+re.escape(stock_id)+r'\)', raw_html)
            # 模式 B: <title>代號 名稱 - 股價 ...
            match_b = re.search(r'<title>'+re.escape(stock_id)+r'\s+([^<]+?)\s*-[^<]*</title>', raw_html)
            # 模式 C: 標題中任何包含括號代號的文字
            match_c = re.search(r'([^<>\-]+?)\s*\('+re.escape(stock_id)+r'\)', raw_html)

            if match_a: name = match_a.group(1).strip()
            elif match_b: name = match_b.group(1).strip()
            elif match_c: name = match_c.group(1).strip()

            # 額外清理
            if name:
                # 剔除奇怪的 prefix
                name = re.sub(r'^[^\w\u4e00-\u9fff]+', '', name)
                # 再次檢查黑名單
                if any(x in name for x in ["Yahoo", "股市", "登入", "電子報", "首頁"]):
                    name = None
                elif len(name) > 10:
                    name = None
            
            # 2. 抓取產業
            # 台灣 Yahoo 的產業標籤通常在 <div class="D(f) Ai(c) Mb(6px)"> 附近
            match_industry = re.search(r'href="/class/([^"]+)"[^>]*>([^<]+)</a>', res.text)
            if match_industry:
                industry = match_industry.group(2).strip()
                
            return name, industry
    except Exception:
        pass
    return None, None


def get_stock_info(stock_id: str):
    # 英文產業名稱到中文的對應表
    industry_mapping = {
        'Basic Materials': '基本材料',
        'Consumer Cyclical': '消費循環',
        'Financial Services': '金融服務',
        'Real Estate': '房地產',
        'Consumer Defensive': '消費防禦',
        'Healthcare': '醫療保健',
        'Utilities': '公用事業',
        'Communication Services': '通訊服務',
        'Energy': '能源',
        'Industrials': '工業',
        'Technology': '科技',
        'Building Materials': '建材營造',
        'Packaged Foods': '食品加工',
        'Farm Products': '農產品',
        'Footwear & Accessories': '鞋類及配件',
        'Semiconductors': '半導體',
        'Communication Equipment': '通信網路',
        'Computer Hardware': '電腦周邊',
        'Consumer Electronics': '光電',
        'Software': '資訊服務',
        'Electronic Components': '電子零組件',
        'Electronic Distribution': '電子通路',
        'Apparel Manufacturing': '紡織纖維',
        'Auto Parts': '汽車工業',
        'Chemicals': '化學工業'
    }
    
    result = {'name': None, 'industry': None}
    try:
        # 優先從 Yahoo 取得中文名稱與產業
        y_name, y_industry = get_tw_yahoo_local_info(stock_id)
        if y_name: result['name'] = y_name
        if y_industry: result['industry'] = y_industry

        # 從 yfinance 取得產業資訊 (備援)
        for market in ['TW', 'TWO']:
            ticker = f"{stock_id}.{market}"
            stock = yf.Ticker(ticker)
            info = getattr(stock, 'info', {}) or {}

            if info:
                # 如果還沒有名稱，才從 yfinance 取得名稱
                if not result['name']:
                    candidate_name = info.get('shortName') or info.get('longName')
                    if candidate_name:
                        if _contains_chinese(candidate_name):
                            result['name'] = candidate_name
                        else:
                            result['name'] = candidate_name

                # 取得產業資訊
                industry = info.get('industry') or info.get('sector')
                if industry and not result['industry']:
                    # 嘗試從對應表取得中文名稱
                    result['industry'] = industry_mapping.get(industry, industry)

            if result['name'] and result['industry']:
                break

        # 設定預設值
        if not result['name']:
            result['name'] = f"股票{stock_id}"

        if not result['industry']:
            result['industry'] = '未分類'
    except Exception:
        result['name'] = result['name'] or f"股票{stock_id}"
        result['industry'] = result['industry'] or '未分類'

    return result


def batch_download_stock_info(stock_ids):
    all_info = {}
    if not stock_ids:
        return all_info
        
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # 使用線程池並行抓取股票資訊
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_sid = {executor.submit(get_stock_info, sid): sid for sid in stock_ids}
        for future in as_completed(future_to_sid):
            sid = future_to_sid[future]
            try:
                info = future.result()
                all_info[sid] = info
            except Exception as e:
                print(f"Error fetching info for {sid}: {e}")
                all_info[sid] = {'name': f"股票{sid}", 'industry': '未分類'}
                
    return all_info


def get_stock_price_and_ma(stock_id: str, ma_days=20, target_date=None, cache=None):
    # Silence yfinance
    import logging
    logging.getLogger('yfinance').setLevel(logging.CRITICAL)
    try:
        if cache is not None:
            if stock_id in cache:
                hist = cache[stock_id]
            else:
                return None, None
        else:
            ticker = f"{stock_id}.TW"
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2y")
            if hist.empty:
                ticker = f"{stock_id}.TWO"
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2y")
            if not hist.empty:
                hist.index = hist.index.tz_localize(None).normalize()
                hist['MA20'] = hist['Close'].rolling(window=ma_days).mean()
            
        if hist is None or hist.empty:
            return None, None
            
        # Ensure index is normalized for lookup
        if target_date:
            target_dt = datetime.datetime.strptime(target_date, "%Y%m%d")
            # Use 'asof' to find the closest date <= target_dt
            # This is much faster than filtering and copying the DataFrame
            idx = hist.index.asof(target_dt)
            if pd.isna(idx):
                return None, None
            
            row = hist.loc[idx]
            close_val = row['Close']
            ma_val = row['MA20']
            
            if pd.isna(ma_val):
                return None, None
            return float(close_val), float(ma_val)
        else:
            # No target date, get latest
            last_row = hist.iloc[-1]
            if pd.isna(last_row['MA20']):
                return None, None
            return float(last_row['Close']), float(last_row['MA20'])

    except Exception as e:
        print(f"Error fetching price for {stock_id}: {e}")
        return None, None

def get_stock_name(stock_id: str):
    """獲取股票名稱（優先繁體中文名稱）"""
    def _contains_chinese(text: str):
        return any('\u4e00' <= ch <= '\u9fff' for ch in text)

    try:
        for market in ['TW', 'TWO']:
            ticker = f"{stock_id}.{market}"
            stock = yf.Ticker(ticker)
            info = getattr(stock, 'info', {}) or {}

            if info:
                # 優先使用 shortName，如果含中文則回傳
                if 'shortName' in info and info['shortName']:
                    if _contains_chinese(info['shortName']):
                        return info['shortName']
                # 否則使用 longName
                if 'longName' in info and info['longName']:
                    if _contains_chinese(info['longName']):
                        return info['longName']

        # 最後再嘗試任何可用名稱
        stock = yf.Ticker(f"{stock_id}.TW")
        info = getattr(stock, 'info', {}) or {}
        if 'shortName' in info and info['shortName']:
            return info['shortName']
        if 'longName' in info and info['longName']:
            return info['longName']

        return f"股票{stock_id}"
    except Exception as e:
        print(f"Error fetching name for {stock_id}: {e}")
        return f"股票{stock_id}"

def get_stock_price_history(stock_id: str, days=30):
    """獲取股票近期價格歷史"""
    try:
        ticker = f"{stock_id}.TW"
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days}d")
        if hist.empty:
            ticker = f"{stock_id}.TWO"
            stock = yf.Ticker(ticker)
            hist = stock.history(period=f"{days}d")
            
        if not hist.empty:
            hist.index = hist.index.tz_localize(None).normalize()
            hist = hist.reset_index()
            hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
            return hist[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict('records')
        return []
    except Exception as e:
        print(f"Error fetching history for {stock_id}: {e}")
        return []

