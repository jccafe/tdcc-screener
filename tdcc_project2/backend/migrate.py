"""
日期摘要表遷移腳本 - 用於建立和填充 TDCC 日期摘要表
這是 TDCC 股票系統效能優化方案的一部分
"""
from sqlalchemy import func
import logging
import sys

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 從專案中導入必要的模組
from database import SessionLocal, TDCCData, TDCCDateSummary, Base, engine

def create_date_summary_table():
    """建立日期摘要表"""
    logger.info("建立日期摘要表...")
    # 僅建立 TDCCDateSummary 表，不影響其他表
    Base.metadata.create_all(engine, tables=[TDCCDateSummary.__table__])
    logger.info("日期摘要表已建立")

def migrate_date_summary():
    """將現有 TDCC 資料遷移到日期摘要表"""
    logger.info("開始遷移日期資料到摘要表...")
    
    db = SessionLocal()
    try:
        # 先清空現有的摘要表資料，避免重複
        db.query(TDCCDateSummary).delete()
        db.commit()
        
        # 查詢所有不重複的日期
        dates_query = db.query(TDCCData.date).distinct().order_by(TDCCData.date)
        total_dates = dates_query.count()
        logger.info(f"找到 {total_dates} 個不同的日期需要遷移")
        
        # 批次處理日期數據
        batch_size = 20
        processed = 0
        
        for i in range(0, total_dates, batch_size):
            batch_dates = dates_query.offset(i).limit(batch_size).all()
            for date_row in batch_dates:
                date = date_row[0]
                
                # 計算該日期的記錄數
                record_count = db.query(func.count(TDCCData.id)).filter(TDCCData.date == date).scalar()
                
                # 獲取該日期的股票代碼範圍
                min_stock = db.query(func.min(TDCCData.stock_id)).filter(TDCCData.date == date).scalar()
                max_stock = db.query(func.max(TDCCData.stock_id)).filter(TDCCData.date == date).scalar()
                
                # 建立摘要記錄
                summary = TDCCDateSummary(
                    date=date,
                    record_count=record_count,
                    min_stock_id=min_stock,
                    max_stock_id=max_stock
                )
                
                db.add(summary)
                processed += 1
                
            # 每一批次提交一次
            db.commit()
            logger.info(f"已遷移 {min(processed, total_dates)}/{total_dates} 個日期")
        
        logger.info("日期資料遷移完成!")
    
    except Exception as e:
        db.rollback()
        logger.error(f"遷移過程中發生錯誤: {str(e)}")
        raise
    finally:
        db.close()

def main():
    try:
        create_date_summary_table()
        migrate_date_summary()
        logger.info("遷移腳本執行成功!")
        return 0
    except Exception as e:
        logger.error(f"遷移腳本執行失敗: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())