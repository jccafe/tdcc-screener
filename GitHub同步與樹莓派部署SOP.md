# GitHub 同步與樹莓派部署 SOP

透過 Git 管理版本，您可以確保電腦上的開發成果能穩定、快速地遷移到樹莓派 (Raspberry Pi)。

---

## 1. 在開發電腦上 (PC 端)：凍結版本並上傳

請在您的電腦終端機執行以下指令：

### A. 提交目前版本
```bash
# 1. 將所有變更加入追蹤 (受 .gitignore 保護)
git add .

# 2. 存檔目前的穩定版本
git commit -m "部署穩定版：完成評分系統與 ETA 優化"

# 3. 推送到遠端 GitHub (假設您已連結 origin)
git push origin main
```

*(註：如果這是一個新倉庫，請先到 GitHub 建立 Repo，然後執行 `git remote add origin <URL>`)*

---

## 2. 在樹莓派上 (Pi 端)：初次安裝

登入您的樹莓派 SSH 後執行：

```bash
# 1. 抓取 GitHub 上的專案
git clone https://github.com/您的帳號/專案名稱.git

# 2. 進入資料夾
cd 專案名稱

# 3. 建立並啟動虛擬環境 (ARM 版)
python3 -m venv venv
source venv/bin/activate

# 4. 安裝依賴 (由 PC 的乾淨版本決定)
pip install fastapi uvicorn sqlalchemy requests pandas yfinance plotly passlib python-multipart

# 5. 啟動伺服器
python backend/main.py
```

---

## 3. 日後如何在樹莓派「一鍵更新」

當您在 PC 上修改了代碼並 `push` 到 GitHub 後，在樹莓派上只需要兩行指令就能同步：

```bash
# 進入資料夾並拉取最新代碼
cd 專案名稱
git pull

# 如果有增加新的 library，再執行一次安裝
pip install -r requirements.txt (如果您有產生此檔案)
```

---

## 4. 關鍵提示

- **資料庫同步**：`.gitignore` 已經排除了 `.sqlite`。這代表樹莓派會建立自己的乾淨資料庫。若您想把電腦的數據也帶過去，請手動透過 SFTP 複製 `database.db`。
- **快取同步**：股價快取檔案不需要同步，樹莓派運行時會自動生成最新的。

---
© 2026 穩定部署指南
