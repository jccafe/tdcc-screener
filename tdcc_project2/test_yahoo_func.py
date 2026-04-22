import re
from curl_cffi import requests

def get_tw_yahoo_local_info(stock_id: str):
    res = requests.get(f"https://tw.stock.yahoo.com/quote/{stock_id}", impersonate="chrome110", timeout=15)
    html = res.text
    name = None
    industry = None
    
    # 1. 抓取名稱
    title_re = r'<title>([^<]+?)\s*\(' + re.escape(stock_id) + r'(?:\.TW|\.TWO)?\)'
    title_match = re.search(title_re, html)
    if title_match:
        name = title_match.group(1).strip()
    
    # 2. 抓取產業
    industry_match = re.search(r'href="/class-quote\?[^"]+"[^>]*>([^<]+)</a>', html)
    if industry_match:
        industry = industry_match.group(1).strip()
        
    return name, industry

print(get_tw_yahoo_local_info("2330"))
print(get_tw_yahoo_local_info("0050"))
