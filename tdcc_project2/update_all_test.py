import os
import glob
import sys
sys.path.append('k:/jc/desktop/PG_TEST/tdcc_project2/tdcc_project2/backend')
import shutil
from database import SessionLocal, engine, TDCCData, Base
from services.scraper import download_and_update_tdcc
from services.screener import run_screener

# Clear cache directories
cache_dirs = [
    'k:/jc/desktop/PG_TEST/tdcc_project2/tdcc_project2/backend/cache',
    'k:/jc/desktop/PG_TEST/tdcc_project2/tdcc_project2/backend/stock_price_cache'
]
for c_dir in cache_dirs:
    if os.path.exists(c_dir):
        print(f"Clearing {c_dir}...")
        for f in glob.glob(os.path.join(c_dir, "*")):
            try:
                os.remove(f)
            except Exception as e:
                print(f"Failed to remove {f}: {e}")

# Clear and recreate database
print("Clearing database...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("Database cleared.")

# Download and update TDCC data (12 weeks mock history)
def progress_cb(p, e=-1, c=0, t=0):
    if p % 10 == 0:
        print(f"TDCC Update Progress: {p}%")

print("Downloading and updating TDCC data...")
download_and_update_tdcc(weeks=12, progress_callback=progress_cb)

# Run screener to populate caches
def screener_progress_cb(p, e=-1, c=0, t=0):
    if p % 20 == 0:
        print(f"Screener Progress: {p}%")

print("Running screener to repopulate cache...")
try:
    results = run_screener(weeks=3, retail_level=9, large_level=14, progress_callback=screener_progress_cb)
    print(f"Screener returned {len(results)} results.")
except Exception as e:
    import traceback
    traceback.print_exc()

print("All tasks completed.")
