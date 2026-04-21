import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

# 預設 Gmail SMTP 設定 (您可以在啟動腳本或系統環境變數中設定)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "jc.ain8n@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", SENDER_EMAIL)

def send_screener_report(date_str, results):
    """
    將篩選結果發送為 HTML 郵件
    """
    if not SENDER_EMAIL or "your-email" in SENDER_EMAIL:
        print("未設定 Email 帳號，跳過發信。")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = f"📈 TDCC 股市監測亮點報 - {date_str}"

        # 製作 HTML 表格內容
        rows = ""
        for s in results[:20]: # 最多取前20名
            rows += f"""
            <tr>
                <td style='border:1px solid #ddd; padding:8px;'>{s['stock_id']} {s.get('stock_name', '')}</td>
                <td style='border:1px solid #ddd; padding:8px; text-align:center; color:red; font-weight:bold;'>{s['score']}</td>
                <td style='border:1px solid #ddd; padding:8px; text-align:right;'>{s['close']}</td>
                <td style='border:1px solid #ddd; padding:8px; text-align:right;'>{s['large_change_pct']}%</td>
                <td style='border:1px solid #ddd; padding:8px; text-align:right;'>{s['retail_change']} 人</td>
                <td style='border:1px solid #ddd; padding:8px;'>{s.get('industry', '')}</td>
            </tr>
            """

        html = f"""
        <html>
        <body>
            <h2>TDCC 集保籌碼監測報告 (日期: {date_str})</h2>
            <p>以下為根據大戶增持、散戶減持模型篩選出的前 20 名潛力標的：</p>
            <table style='width:100%; border-collapse:collapse;'>
                <thead>
                    <tr style='background-color:#f2f2f2;'>
                        <th style='border:1px solid #ddd; padding:8px;'>股票標的</th>
                        <th style='border:1px solid #ddd; padding:8px;'>評分</th>
                        <th style='border:1px solid #ddd; padding:8px;'>收盤價</th>
                        <th style='border:1px solid #ddd; padding:8px;'>大戶增持</th>
                        <th style='border:1px solid #ddd; padding:8px;'>散戶縮減</th>
                        <th style='border:1px solid #ddd; padding:8px;'>產業</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            <p><small>本郵件由樹莓派股市監控儀自動發送。投資有風險，入市需謹慎。</small></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"郵件報告發送成功！內容包含 {len(results)} 隻股票。")
        return True
    except Exception as e:
        print(f"郵件發送失敗: {e}")
        return False
