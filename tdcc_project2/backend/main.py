from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from services.scraper import download_and_update_tdcc, get_stock_name, get_stock_price_history
from services.screener import run_screener
from pydantic import BaseModel, Field
import os
import json
from database import SessionLocal, TDCCData
from sqlalchemy import func
import yfinance as yf
from services.email_service import send_screener_report
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
from datetime import timedelta
import plotly.graph_objects as go
import pandas as pd
from typing import Optional
import asyncio


app = FastAPI()

current_progress = {"percent": 0, "eta": -1, "current": 0, "total": 0}
global_results = None

def update_progress(percent, eta=-1, current=0, total=0):
    global current_progress
    current_progress["percent"] = percent
    current_progress["eta"] = eta
    current_progress["current"] = current
    current_progress["total"] = total

# 股價快取設置
CACHE_DIR = "stock_price_cache"
CACHE_EXPIRY = 3600  # 快取過期時間（秒）：1小時

# 確保快取目錄存在
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/.well-known/{full_path:path}")
async def well_known(full_path: str):
    from fastapi import Response
    return Response(status_code=204)

class ScreenParams(BaseModel):
    retail_level: int = Field(9, description="散戶持股定義等級 (1-5:≤10張, 1-9:≤50張, 1-11:≤100張)")
    large_level: int = Field(14, description="大戶持股定義等級 (14-15:≥400張, 15:≥1000張)")
    weeks: int = Field(3, description="連續觀察週數")
    ma_diff_percent: float = Field(5.0, description="允許的股價與20MA偏離百分比")
    start_date: Optional[str] = Field(None, description="篩選開始日期 (YYYYMMDD)")
    end_date: Optional[str] = Field(None, description="篩選結束日期 (YYYYMMDD)")
    industry_filter: Optional[str] = Field(None, description="產業過濾")
    verify: bool = Field(False, description="是否驗證篩選後的股票價格表現")
    verify_weeks: int = Field(1, description="驗證的週數 (預設為1週)")
    verify_percent: float = Field(20.0, description="驗證的漲幅百分比 (預設為20%)")
    vol_ratio: float = Field(1.0, description="要求的成交量相對於MA5的倍數")

class UpdateParams(BaseModel):
    weeks: int = Field(12, description="要更新的歷史資料週數")

# 快取相關函數
def get_cache_path(stock_id):
    """獲取快取檔案的路徑"""
    return os.path.join(CACHE_DIR, f"{stock_id}_price.json")

def is_cache_valid(stock_id):
    """檢查快取是否有效（存在且未過期）"""
    cache_path = get_cache_path(stock_id)
    if not os.path.exists(cache_path):
        return False
    
    # 檢查檔案修改時間
    mod_time = os.path.getmtime(cache_path)
    current_time = datetime.now().timestamp()
    return (current_time - mod_time) < CACHE_EXPIRY

def read_price_cache(stock_id):
    """從快取讀取股價數據"""
    cache_path = get_cache_path(stock_id)
    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        # 直接返還快取字典，不再轉換為 DataFrame 避免列名混亂
        return cache_data['price_data'], cache_data['chart']
    except Exception as e:
        print(f"Error reading cache for {stock_id}: {e}")
        return None, None

def write_price_cache(stock_id, hist, chart_json):
    """將股價數據寫入快取"""
    cache_path = get_cache_path(stock_id)
    
    # 確保列名清理 (如果傳入的是原始 yf DataFrame)
    if isinstance(hist, pd.DataFrame) and isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)

    # 將 DataFrame 轉換為可序列化的字典
    hist_dict = {
        "dates": hist['Date'].tolist() if 'Date' in hist.columns else [],
        "close": hist['Close'].tolist() if 'Close' in hist.columns else [],
        "open": hist['Open'].tolist() if 'Open' in hist.columns else [],
        "high": hist['High'].tolist() if 'High' in hist.columns else [],
        "low": hist['Low'].tolist() if 'Low' in hist.columns else [],
        "volume": hist['Volume'].tolist() if 'Volume' in hist.columns else []
    }
    
    cache_data = {
        "timestamp": datetime.now().timestamp(),
        "price_data": hist_dict,
        "chart": chart_json
    }
    
    try:
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, default=str)
        return True
    except Exception as e:
        print(f"Error writing cache for {stock_id}: {e}")
        return False

@app.post("/api/update_data")
async def update_data(params: UpdateParams, background_tasks: BackgroundTasks):
    global current_progress
    current_progress = {"percent": 0, "eta": -1}
    
    def run_update():
        global current_progress
        def update_progress_callback(p, e=-1, c=0, t=0):
            global current_progress
            current_progress = {"percent": p, "eta": e, "current": c, "total": t}
        
        try:
            download_and_update_tdcc(weeks=params.weeks, progress_callback=update_progress_callback)
        finally:
            current_progress = {"percent": 100, "eta": 0}
            
    background_tasks.add_task(run_update)
    return {"status": "success", "message": "已開始背景更新任務"}

@app.get("/api/dates")
def get_dates():
    with SessionLocal() as db:
        dates_counts = db.query(TDCCData.date, func.count(TDCCData.id)).group_by(TDCCData.date).all()
    
    if not dates_counts:
        return {"status": "success", "dates": []}
        
    date_list = sorted([{"date": d[0], "count": d[1]} for d in dates_counts], key=lambda x: x["date"], reverse=True)
    return {"status": "success", "dates": date_list}

@app.get("/api/progress")
async def get_progress():
    return current_progress

@app.post("/api/reset")
async def reset_progress():
    """強制重置進度與背景任務狀態"""
    global current_progress
    current_progress = {"percent": 0, "eta": -1, "current": 0, "total": 0}
    return {"status": "success", "message": "已重置背景任務狀態"}

@app.get("/api/stock_name/{stock_id}")
def get_stock_name_endpoint(stock_id: str):
    name = get_stock_name(stock_id)
    return {"status": "success", "name": name}

@app.get("/api/stock_history/{stock_id}")
def get_stock_history_endpoint(stock_id: str, days: int = 30):
    history = get_stock_price_history(stock_id, days)
    return {"status": "success", "history": history}

# 獲取股價數據並生成 Plotly 圖表 - 帶快取機制
@app.get("/api/stock_price/{stock_id}")
def get_stock_price(stock_id: str, force_refresh: bool = False):
    try:
        # 檢查快取是否有效且未要求強制刷新
        if not force_refresh and is_cache_valid(stock_id):
            hist_data, chart_json = read_price_cache(stock_id)
            if hist_data is not None and chart_json is not None:
                return {
                    "status": "success",
                    "data": hist_data,
                    "chart": chart_json,
                    "cached": True
                }
        
        # 獲取近兩個月的股價數據（為了計算 MA20 需要更多歷史數據）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        # 格式化為 yfinance 所需的日期格式
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # 添加 .TW 後綴 (台灣股票)
        ticker = f"{stock_id}.TW"
        
        print(f"Fetching price data for {ticker} from {start_str} to {end_str}")
        # 獲取歷史數據
        hist = yf.download(ticker, start=start_str, end=end_str, progress=False, auto_adjust=False)
        
        # 如果失敗 (長度為0)，嘗試另一個台灣股市後綴 (.TWO 為上櫃)
        if len(hist) == 0:
            alt_ticker = f"{stock_id}.TWO" if ".TW" in ticker else f"{stock_id}.TW"
            print(f"Retrying with alternative ticker: {alt_ticker}")
            hist = yf.download(alt_ticker, start=start_str, end=end_str, progress=False, auto_adjust=False)

        if len(hist) == 0:
            return {"status": "error", "message": "無法獲取股價數據"}
        
        # 再次確保清理索引
        if hasattr(hist.columns, 'levels'):
            hist.columns = hist.columns.get_level_values(0)
        
        # 移除任何空的或重複的 column (yf 有時會重複返回)
        hist = hist.loc[:, ~hist.columns.duplicated()]
        
        # 轉換日期
        if 'Date' not in hist.columns:
            hist = hist.reset_index()
        
        # 重要：強制轉為 numpy array 再轉 tolist，以徹底斷開 pandas 索引的干擾
        try:
            # yf 下載後可能是多重索引，或者是 DataFrame。顯式選取 Close 欄位。
            # 如果是 DataFrame，確保選取 Close
            target_col = 'Close'
            if target_col not in hist.columns:
                # 嘗試在多重索引中找
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
            
            dates = hist['Date'].dt.strftime('%Y-%m-%d').tolist()
            closes = pd.to_numeric(hist['Close'], errors='coerce').astype(float).tolist()
            opens = pd.to_numeric(hist['Open'], errors='coerce').astype(float).tolist()
            highs = pd.to_numeric(hist['High'], errors='coerce').astype(float).tolist()
            lows = pd.to_numeric(hist['Low'], errors='coerce').astype(float).tolist()
            volumes = (pd.to_numeric(hist['Volume'], errors='coerce') / 1000).astype(float).tolist()
            
            # Debug：如果價格出現序列化規律 (0, 1, 2...)，警告可能是索引問題
            if len(closes) > 5 and closes[1] == closes[0] + 1 and closes[2] == closes[1] + 1:
                print(f"CRITICAL WARNING: {stock_id} data looks like index numbers, not prices!")
            
            price_data = {
                "dates": dates,
                "close": closes,
                "open": opens,
                "high": highs,
                "low": lows,
                "volume": volumes
            }
        except Exception as conv_err:
            print(f"Conversion Error for {stock_id}: {conv_err}")
            return {"status": "error", "message": f"數據格式化失敗: {conv_err}"}
        
        # 獲取股票名稱
        stock_name = get_stock_name(stock_id)
        
        # 準備圖表數據 (使用 plotly)
        fig = go.Figure(data=[go.Candlestick(
            x=dates,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name="價格"
        )])
        
        fig.add_trace(go.Bar(
            x=dates,
            y=volumes,
            name="成交量 (張)",
            yaxis="y2",
            marker_color='rgba(100, 150, 255, 0.4)',
            orientation='v'
        ))
        
        # 添加簡單的移動平均線 (5日、20日)
        # 使用 numpy array 進行計算，確保與 index 脫鉤
        close_np = pd.to_numeric(hist['Close'], errors='coerce').to_numpy().flatten()
        ma5_vals = pd.Series(close_np).rolling(window=5).mean().tolist()
        ma20_vals = pd.Series(close_np).rolling(window=20).mean().tolist()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=ma5_vals,
            name="MA5",
            line=dict(color='#ff9f43', width=2),
            opacity=0.9
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=ma20_vals,
            name="MA20",
            line=dict(color='#10ac84', width=2),
            opacity=0.9
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(13, 17, 23, 0.95)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#cfd8dc'),
            title=f"{stock_id} {stock_name} - 近一個月股價走勢",
            yaxis=dict(
                title="價格 (NTD)",
                domain=[0.3, 1],
                gridcolor='rgba(255,255,255,0.1)',
                zerolinecolor='rgba(255,255,255,0.1)',
                fixedrange=False
            ),
            yaxis2=dict(
                title="成交量 (張)",
                domain=[0, 0.25],
                anchor="x",
                gridcolor='rgba(255,255,255,0.05)',
                side="right",
                fixedrange=False
            ),
            xaxis=dict(
                title="日期",
                gridcolor='rgba(255,255,255,0.1)',
                rangeslider_visible=False
            ),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=60, r=60, b=50, t=80)
        )
        
        # 轉換為 JSON
        chart_json = fig.to_json()
        
        # 儲存到快取
        write_price_cache(stock_id, hist, chart_json)
        
        return {
            "status": "success", 
            "data": price_data,
            "chart": chart_json,
            "cached": False
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 新增 API 端點 - 驗證股價上漲指定百分比的股票
@app.get("/api/verify_price_increase")
def verify_price_increase(
    stock_id: str = Query(..., description="股票代號"),
    weeks: int = Query(1, description="驗證的週數"),
    percent: float = Query(20.0, description="漲幅百分比要求")
):
    try:
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)
        
        # 格式化日期
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # 獲取股票數據
        ticker = f"{stock_id}.TW"
        hist = yf.download(ticker, start=start_str, end=end_str)
        
        if hist.empty:
            return {
                "status": "error",
                "message": "無法獲取股價數據"
            }
            
        # 計算漲幅
        first_price = hist['Close'].iloc[0]
        last_price = hist['Close'].iloc[-1]
        price_change = ((last_price - first_price) / first_price) * 100
        
        # 獲取股票名稱
        stock_name = get_stock_name(stock_id)
        
        # 檢查是否符合漲幅要求
        meets_criteria = price_change >= percent
        
        return {
            "status": "success",
            "data": {
                "stock_id": stock_id,
                "stock_name": stock_name,
                "start_date": start_str,
                "end_date": end_str,
                "start_price": round(first_price, 2),
                "end_price": round(last_price, 2),
                "price_change_percent": round(price_change, 2),
                "meets_criteria": meets_criteria,
                "required_percent": percent
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/api/screener")
async def screener(params: ScreenParams, background_tasks: BackgroundTasks):
    global current_progress, global_results
    current_progress = {"percent": 0, "eta": -1}
    global_results = None
    
    def run_screener_task():
        global current_progress, global_results
        def update_progress_callback(p, e=-1, c=0, t=0):
            global current_progress
            current_progress = {"percent": p, "eta": e, "current": c, "total": t}
        
        try:
            # 確保驗證參數有效
            verify = params.verify
            verify_weeks = max(1, params.verify_weeks)
            verify_percent = max(0.1, params.verify_percent)
            
            results = run_screener(
                retail_level=params.retail_level,
                large_level=params.large_level,
                weeks=params.weeks,
                ma_diff_percent=params.ma_diff_percent,
                vol_ratio=params.vol_ratio,
                start_date=params.start_date,
                end_date=params.end_date,
                industry_filter=params.industry_filter,
                verify=verify,
                verify_weeks=verify_weeks,
                verify_percent=verify_percent,
                progress_callback=update_progress_callback
            )
            global_results = results
        except Exception as e:
            print(f"Screener Error: {e}")
            global_results = {"error": str(e)}
        finally:
            current_progress = {"percent": 100, "eta": 0}
            
    background_tasks.add_task(run_screener_task)
    return {"status": "success", "message": "篩選任務已在背景啟動"}

@app.get("/api/results")
def get_results():
    global global_results
    if global_results is None:
        return {"status": "processing"}
    if isinstance(global_results, dict) and "error" in global_results:
        return {"status": "error", "message": global_results["error"]}
    return {"status": "success", "data": global_results}


# Mount frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# 修改最後的 uvicorn.run 調用
# 記錄最後寄信時間
EMAIL_LOG_FILE = "email_sent_log.json"

def check_and_send_weekly_report():
    """
    檢查並發送每週報告：
    1. 判斷現在是否為週六 07:00 之後。
    2. 檢查本週是否已寄送過。
    """
    try:
        import os, json
        print(f"[{datetime.datetime.now()}] 啟動定時任務檢查...")
        now = datetime.datetime.now()
        
        # 判斷是否為週六 (5 為週六)
        if now.weekday() != 5:
            print(f"[{now.strftime('%Y-%m-%d %H:%M')}] 今天不是週六，跳過發信。")
            return
            
        # 如果還沒到 7 點
        if now.hour < 7:
            print(f"[{now.strftime('%Y-%m-%d %H:%M')}] 還沒到早上 7 點，跳過發信。")
            return
            
        # 檢查紀錄檔案
        this_week_id = now.strftime("%Y_week_%U")
        if os.path.exists(EMAIL_LOG_FILE):
            with open(EMAIL_LOG_FILE, "r") as f:
                log = json.load(f)
                if log.get("last_week") == this_week_id:
                    print(f"[{now.strftime('%Y-%m-%d %H:%M')}] 本週報告已發送過。")
                    return

        print("符合發信條件！正在執行篩選...")
        from services.screener import run_screener
        db = SessionLocal()
        latest_date_row = db.query(TDCCData.date).distinct().order_by(TDCCData.date.desc()).first()
        db.close()
        
        if latest_date_row:
            results = run_screener(weeks=3, retail_level=9, large_level=14)
            if results and not isinstance(results, dict):
                success = send_screener_report(latest_date_row[0], results)
                if success:
                    with open(EMAIL_LOG_FILE, "w") as f:
                        json.dump({"last_week": this_week_id, "sent_at": str(now)}, f)
                    print("自動郵件報告發送成功。")
    except Exception as e:
        print(f"【排程任務錯誤】: {e}")

# 啟動排程器
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_weekly_report, 'interval', hours=1)
# 啟動 5 秒後執行第一次檢查 (稍微縮短等待時間)
scheduler.add_job(check_and_send_weekly_report, 'date', run_date=datetime.datetime.now() + datetime.timedelta(seconds=5))
scheduler.start()
print(">>> 背景自動報告排程器已啟動。")

if __name__ == "__main__":
    import uvicorn
    try:
        # 使用 workers=1 確保訊號處理簡單化
        # 增加 timeout_keep_alive 以便更快釋放連線
        uvicorn.run(app, host="0.0.0.0", port=8001, timeout_keep_alive=5)
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        print("\n正在停止伺服器...")
    except Exception as e:
        print(f"Server Exit Error: {e}")