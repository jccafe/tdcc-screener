import pandas as pd
from database import SessionLocal, TDCCData
from services.scraper import get_stock_price_and_ma, batch_download_prices, batch_download_stock_info

import time
import os
import json
import hashlib
import datetime

CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def run_screener(retail_level=9, large_level=14, weeks=3, ma_diff_percent=5.0, vol_ratio=1.0, start_date=None, end_date=None, industry_filter=None, verify=False, verify_weeks=1, verify_percent=20.0, progress_callback=None):
    db = SessionLocal()
    
    try:
        # Get all distinct dates ordered by desc
        all_dates = db.query(TDCCData.date).distinct().order_by(TDCCData.date.desc()).all()
        all_dates = [d[0] for d in all_dates]
        
        if not all_dates:
            return {"error": "No historical data found in database."}
            
        # Create cache key based on inputs and the latest available date
        latest_db_date = all_dates[0]
        cache_key_raw = f"{retail_level}_{large_level}_{weeks}_{ma_diff_percent}_{vol_ratio}_{start_date}_{end_date}_{industry_filter}_{verify}_{verify_weeks}_{verify_percent}_{latest_db_date}"
        cache_hash = hashlib.md5(cache_key_raw.encode()).hexdigest()
        cache_file = os.path.join(CACHE_DIR, f"screener_cache_{cache_hash}.json")
        
        # ... (中間快取邏輯略)
        
        # Check if cache exists
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_results = json.load(f)
                if progress_callback:
                    progress_callback(100, 0)
                return cached_results
            except Exception as e:
                print(f"Error reading cache: {e}")
                # Fallback to recalculate if cache is corrupted
            
        target_dates = all_dates.copy()
        if start_date:
            target_dates = [d for d in target_dates if d >= start_date]
        if end_date:
            target_dates = [d for d in target_dates if d <= end_date]
        
        if len(all_dates) < weeks:
            return {"error": f"Not enough historical data. Require {weeks} weeks, but only have {len(all_dates)} weeks."}
            
        all_candidates_by_date = {}
        unique_stock_ids = set()
        total_dates = len(target_dates)
        if total_dates == 0:
            return {"error": "No data matches the selected date range."}
        
        # Phase 1: Screen by TDCC data (Local DB)
        # 優化點：一次性下載所有可能用到的日期，不再循環 query
        all_needed_dates = []
        for t_date in target_dates:
            t_idx = all_dates.index(t_date)
            if t_idx + weeks <= len(all_dates):
                all_needed_dates.extend(all_dates[t_idx:t_idx+weeks])
        all_needed_dates = list(set(all_needed_dates))
        
        print(f"Pre-loading data for {len(all_needed_dates)} dates...")
        query = db.query(TDCCData).filter(TDCCData.date.in_(all_needed_dates)).statement
        full_df = pd.read_sql(query, db.bind)
        full_df = full_df[full_df['stock_id'].str.len() == 4]
        
        for idx, t_date in enumerate(target_dates):
            if progress_callback:
                percent = int((idx / total_dates) * 60)
                progress_callback(percent, -1, idx, total_dates)

            t_idx = all_dates.index(t_date)
            if t_idx + weeks > len(all_dates):
                continue
                
            dates_for_target = all_dates[t_idx:t_idx+weeks]
            # 從記憶體中過濾
            df = full_df[full_df['date'].get(dates_for_target)] if False else full_df[full_df['date'].isin(dates_for_target)]
            
            df_retail = df[df['level'] <= retail_level].groupby(['stock_id', 'date'])['people'].sum().reset_index()
            df_large = df[df['level'] >= large_level].groupby(['stock_id', 'date'])['percent'].sum().reset_index()
            
            # 使用更快的 pivot 方式
            retail_pivot = df_retail.pivot(index='stock_id', columns='date', values='people')
            large_pivot = df_large.pivot(index='stock_id', columns='date', values='percent')
            
            candidates = []
            for stock_id in retail_pivot.index:
                if stock_id not in large_pivot.index:
                    continue
                r_vals = retail_pivot.loc[stock_id].values
                l_vals = large_pivot.loc[stock_id].values
                if len(r_vals) < weeks or len(l_vals) < weeks:
                    continue
                
                retail_decreasing = all(r_vals[i] > r_vals[i+1] for i in range(len(r_vals)-1))
                large_increasing = all(l_vals[i] < l_vals[i+1] for i in range(len(l_vals)-1))
                
                if retail_decreasing and large_increasing:
                    # 計算評分 (Score)
                    # 1. 大戶增持分數 (40%) - 累計增持達到 5% 才是滿分
                    large_inc_pct = l_vals[-1] - l_vals[0]
                    score_large = min(40, (large_inc_pct / 5.0) * 40)
                    
                    # 2. 散戶減持分數 (40%) - 人數累計減持超過 8% 才是滿分
                    retail_dec_pct = (r_vals[0] - r_vals[-1]) / r_vals[0] if r_vals[0] > 0 else 0
                    score_retail = min(40, (retail_dec_pct / 0.08) * 40)
                    
                    # 3. 基礎分與一致性 (20%)
                    score_base = 20
                    
                    total_score = round(score_base + score_large + score_retail, 0)
                    total_score = int(min(100, max(0, total_score)))

                    candidates.append({
                        "trigger_date": f"{t_date[:4]}-{t_date[4:6]}-{t_date[6:]}",
                        "stock_id": stock_id,
                        "retail_current": int(r_vals[-1]),
                        "retail_change": int(r_vals[-1] - r_vals[0]),
                        "large_current_pct": round(l_vals[-1], 2),
                        "large_change_pct": round(large_inc_pct, 2),
                        "score": total_score
                    })
                    unique_stock_ids.add(stock_id)
            
            all_candidates_by_date[t_date] = candidates

        # Phase 2: Batch Download from yfinance
        if progress_callback:
            progress_callback(75, -1) # Stage: Downloading
            
        price_cache = batch_download_prices(list(unique_stock_ids))
        info_cache = batch_download_stock_info(list(unique_stock_ids))
        
        # Phase 3: Final Filtering by MA (Local Calculation)
        all_final_results = []
        total_candidates = sum(len(c) for c in all_candidates_by_date.values())
        processed_count = 0
        start_time_p3 = time.time()
        
        for t_date in target_dates:
            candidates = all_candidates_by_date.get(t_date, [])
            for stock in candidates:
                processed_count += 1
                
                # 計算 ETA
                eta = -1
                if processed_count > 5:
                    elapsed = time.time() - start_time_p3
                    avg_time = elapsed / processed_count
                    eta = int(avg_time * (total_candidates - processed_count))

                if progress_callback:
                    # Move from 70% to 100%
                    p3_percent = 70 + int((processed_count / max(1, total_candidates)) * 30)
                    progress_callback(min(99, p3_percent), eta, processed_count, total_candidates)

                stock_id = stock['stock_id']
                close_price, ma20 = get_stock_price_and_ma(stock_id, target_date=t_date, cache=price_cache)
                
                if close_price and ma20 and ma20 != 0:
                    # 1. 價格偏離率檢查
                    diff_pct = abs(close_price - ma20) / ma20 * 100
                    if diff_pct > ma_diff_percent:
                        continue
                        
                    # 2. 成交量爆量檢查 (與前5日均量比)
                    current_vol_ratio = 1.0
                    if stock_id in price_cache:
                        df_hist = price_cache[stock_id]
                        # 找到目標日期的索引
                        try:
                            # 確保日期格式匹配
                            t_dt = pd.to_datetime(t_date)
                            idx_list = df_hist.index[df_hist.index <= t_dt]
                            if len(idx_list) >= 6:
                                vol_series = df_hist.loc[idx_list, 'Volume']
                                current_vol = vol_series.iloc[-1]
                                ma5_vol = vol_series.iloc[-6:-1].mean()
                                if ma5_vol > 0:
                                    current_vol_ratio = current_vol / ma5_vol
                        except:
                            pass
                    
                    if current_vol_ratio < vol_ratio:
                        continue

                    # 符合所有條件
                    stock['close'] = round(close_price, 2)
                    stock['ma20'] = round(ma20, 2)
                    stock['ma_diff_pct'] = round((close_price - ma20) / ma20 * 100, 2)
                    stock['vol_ratio'] = round(current_vol_ratio, 2)
                    
                    stock_info = info_cache.get(stock_id, {})
                    stock['stock_name'] = stock_info.get('name', f"股票{stock_id}")
                    stock['industry'] = stock_info.get('industry', '未分類')
                    # 檢查產業過濾
                    if industry_filter and industry_filter != 'all' and stock['industry'] != industry_filter:
                        continue
                            
                        # 驗證後續漲幅
                    # 驗證後續漲幅
                    if verify:
                        verify_success = False
                        if stock_id in price_cache:
                            hist = price_cache[stock_id]
                            target_dt = pd.to_datetime(t_date)
                            end_dt = target_dt + datetime.timedelta(days=verify_weeks * 7)
                            
                            # 進行時間範圍切片
                            mask = (hist.index > target_dt) & (hist.index <= end_dt)
                            window = hist.loc[mask]
                            
                            if not window.empty:
                                max_p = float(window['High'].max())
                                change = (max_p - close_price) / close_price * 100
                                stock['verify_price_change_pct'] = round(change, 2)
                                if change >= verify_percent:
                                    verify_success = True
                        
                        stock['verify_meets_criteria'] = verify_success
                    
                    all_final_results.append(stock)
                        
        if progress_callback:
            progress_callback(100, 0)
            
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(all_final_results, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving cache: {e}")
            
        return all_final_results
    finally:
        db.close()
