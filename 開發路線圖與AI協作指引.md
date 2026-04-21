# TDCC 股市監測儀 - 開發路線圖與 AI 協作指引

## 一、 開發核心階段
1. **Scraper**: 使用 requests 抓取 TDCC CSV，Pandas 清洗。
2. **Database**: SQLite 儲存週變化。
3. **Screener**: 量化篩選 (大戶增/散戶減) + 評分模型。
4. **API**: FastAPI 提供進度 (/progress) 與結果 (/results)。
5. **Frontend**: 毛玻璃設計、Plotly 圖表、事件委派機制。

## 二、 推薦提示詞 (Prompts)
- **篩選邏輯**: 「幫我寫一個 Python 邏輯，篩選出連續 3 週大戶持股比例上升且散戶人數下降的股票。」
- **ETA 預估**: 「在 for 迴圈中加入時間計算，回傳預計剩餘的分鐘與秒數。」
- **UI 優化**: 「幫我優化 CSS 版面，讓左側導航固定，右側表格自適應寬度並縮小字體。」

---
© 2026 TDCC 開發指南
