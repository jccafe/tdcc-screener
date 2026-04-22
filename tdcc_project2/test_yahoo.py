import re
from curl_cffi import requests

res = requests.get('https://tw.stock.yahoo.com/quote/2330', impersonate='chrome110')
with open('test_yahoo_out.txt', 'w', encoding='utf-8') as f:
    if '半導體' in res.text:
        idx = res.text.find('半導體')
        f.write(f"Found 半導體 at {idx}\n")
        f.write(f"Context around 半導體: {res.text[idx-200:idx+200]}\n")
    else:
        f.write("Did not find 半導體 in the text.\n")
