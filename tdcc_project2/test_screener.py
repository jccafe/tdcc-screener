import sys
import os
sys.path.append('k:/jc/desktop/PG_TEST/tdcc_project2/tdcc_project2/backend')
from services.screener import run_screener
import time

def test_progress(p, e=-1, c=0, t=0):
    print(f"Progress: {p}% (Current: {c}, Total: {t})")

# Remove cache to force recalculation
for f in os.listdir('cache'):
    os.remove(os.path.join('cache', f))

print("Cache cleared. Starting screener...")
start = time.time()
try:
    results = run_screener(weeks=3, retail_level=9, large_level=14, progress_callback=test_progress)
    print("Screener results length:", len(results))
    print("Screener successful!")
except Exception as e:
    import traceback
    traceback.print_exc()

end = time.time()
print(f"Time taken: {end-start:.2f} seconds")
