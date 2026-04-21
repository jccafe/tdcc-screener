import tkinter as tk
from tkinter import ttk, messagebox
import database
import pandas as pd
import numpy as np
import platform
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import tempfile
import webbrowser
import base64
from io import BytesIO

# 設定 Matplotlib 中文字體
if platform.system() == 'Windows':
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
elif platform.system() == 'Darwin':
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class AnalysisManager:
    def __init__(self, parent_frame, year_var, semester_var):
        self.parent = parent_frame
        self.year_var = year_var
        self.semester_var = semester_var
        self.current_df = pd.DataFrame()
        self.create_ui()

    def create_ui(self):
        """建立分析介面與控制按鈕"""
        control_frame = ttk.Frame(self.parent, padding=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        left_frame = ttk.Frame(control_frame)
        left_frame.pack(side=tk.LEFT)
        ttk.Label(left_frame, text="🔍 分析範圍:", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=5)
        self.exam_type_var = tk.StringVar(value="第一次段考")
        self.exam_cb = ttk.Combobox(
            left_frame, textvariable=self.exam_type_var,
            values=["第一次段考", "第二次段考", "第三次段考", "學期成績平均", "學年成績平均"],
            state="readonly", width=15
        )
        self.exam_cb.pack(side=tk.LEFT, padx=5)
        self.exam_cb.bind("<<ComboboxSelected>>", lambda e: self.calculate_and_display())
        ttk.Button(left_frame, text="⚡ 執行計算", command=self.calculate_and_display).pack(side=tk.LEFT, padx=5)

        right_frame = ttk.Frame(control_frame)
        right_frame.pack(side=tk.RIGHT)
        ttk.Button(right_frame, text="🖨️ 班級總表", command=self.print_class_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(right_frame, text="🖨️ 個人報表", command=self.print_individual_report).pack(side=tk.LEFT, padx=2)
        ttk.Label(right_frame, text=" | ").pack(side=tk.LEFT)
        ttk.Button(right_frame, text="🔮 AI 診斷", command=self.show_ai_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(right_frame, text="📊 互動圖表", command=self.show_student_charts).pack(side=tk.LEFT, padx=2)

        table_frame = ttk.Frame(self.parent, padding=10)
        table_frame.pack(expand=True, fill=tk.BOTH)
        columns = ("id", "seat", "name", "total_score", "score_pr", "total_points", "point_pr")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=0, stretch=tk.NO)

        headers = [("seat", "座號", 50), ("name", "姓名", 80), ("total_score", "五科總分", 100), ("score_pr", "總分 PR", 90), ("total_points", "總積點", 100), ("point_pr", "積點 PR", 90)]
        for col, text, width in headers:
            self.tree.heading(col, text=text, command=lambda c=col: self.treeview_sort_column(c, False))
            self.tree.column(col, anchor=tk.CENTER, width=width)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def treeview_sort_column(self, col, reverse):
        """UI 表格點擊標題排序"""
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        def sort_key(val):
            v = str(val[0]).strip()
            if not v or v == "-": return -999.0
            try: return float(v)
            except ValueError: return v
        l.sort(key=sort_key, reverse=reverse)
        for index, (_, k) in enumerate(l): self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda c=col: self.treeview_sort_column(c, not reverse))

    def convert_to_points(self, score):
        if pd.isna(score): return 0
        if score >= 95: return 7
        elif score >= 90: return 6
        elif score >= 85: return 5
        elif score >= 75: return 4
        elif score >= 65: return 3
        elif score >= 50: return 2
        else: return 1

    def format_diff(self, diff):
        if pd.isna(diff) or diff == 0: return "-"
        return f"▲{int(diff)}" if diff > 0 else f"▼{abs(int(diff))}"

    def calculate_and_display(self):
        year, sem, exam = self.year_var.get(), self.semester_var.get(), self.exam_type_var.get()
        subs = ['chinese', 'english', 'math', 'social', 'science']

        if "平均" in exam:
            df_curr = self.get_aggregated_data(exam, year, sem)
            df_curr['score_diff'] = df_curr['point_diff'] = np.nan
            for s in subs:
                df_curr[f'{s}_diff'] = df_curr[f'{s}_pts_diff'] = np.nan
        else:
            df_curr = self.get_exam_data(exam, year, sem)
            prev_name = {"第二次段考": "第一次段考", "第三次段考": "第二次段考"}.get(exam)
            if prev_name:
                df_prev = self.get_exam_data(prev_name, year, sem)
                if not df_prev.empty:
                    m_cols = ['id', 'total_score', 'total_points'] + subs + [f"{s}_pts" for s in subs]
                    df_m = pd.merge(df_curr, df_prev[m_cols], on='id', how='left', suffixes=('', '_prev'))
                    df_curr['score_diff'] = df_m['total_score'] - df_m['total_score_prev']
                    df_curr['point_diff'] = df_m['total_points'] - df_m['total_points_prev']
                    for s in subs:
                        df_curr[f'{s}_diff'] = df_m[s] - df_m[f'{s}_prev']
                        df_curr[f'{s}_pts_diff'] = df_m[f'{s}_pts'] - df_m[f'{s}_pts_prev']
                else:
                    self._init_nan_diff(df_curr, subs)
            else:
                self._init_nan_diff(df_curr, subs)

        for row in self.tree.get_children():
            self.tree.delete(row)
            
        if df_curr.empty:
            self.current_df = pd.DataFrame()
            return

        cols_map = {
            'total_score': ('score_rank', 'score_pr'), 
            'total_points': ('point_rank', 'point_pr'),
            'chinese': ('c_rk', 'chinese_pr'), 'english': ('e_rk', 'english_pr'),
            'math': ('m_rk', 'math_pr'), 'social': ('s_rk', 'social_pr'), 'science': ('sc_rk', 'science_pr')
        }
        for col, (rk, pr) in cols_map.items():
            df_curr[rk] = df_curr[col].rank(method='min', ascending=False)
            N = df_curr[col].notna().sum()
            df_curr[pr] = 100 - np.floor(((df_curr[rk] - 1) / N) * 100) if N > 0 else np.nan

        self.current_df = df_curr.sort_values(by='seat_number')
        for _, r in self.current_df.iterrows():
            self.tree.insert("", tk.END, values=(
                r['id'], r['seat_number'], r['student_name'], 
                round(r['total_score'], 1), 
                int(r['score_pr']) if pd.notna(r['score_pr']) else "", 
                int(r['total_points']), 
                int(r['point_pr']) if pd.notna(r['point_pr']) else ""
            ))

    def _init_nan_diff(self, df, subs):
        df['score_diff'] = df['point_diff'] = np.nan
        for s in subs:
            df[f'{s}_diff'] = df[f'{s}_pts_diff'] = np.nan

    def get_exam_data(self, exam_type, year, sem):
        conn = database.get_db_connection()
        query = 'SELECT s.id, s.seat_number, s.student_name, sc.chinese, sc.english, sc.math, sc.social, sc.science FROM students s JOIN scores sc ON s.id = sc.student_id AND sc.exam_type = ? WHERE s.academic_year = ? AND s.semester = ?'
        df = pd.read_sql_query(query, conn, params=(exam_type, year, sem))
        conn.close()
        return self._process_dataframe(df)

    def get_aggregated_data(self, agg_type, year, sem):
        conn = database.get_db_connection()
        subs = ['chinese', 'english', 'math', 'social', 'science']
        if agg_type == "學期成績平均":
            df_all = pd.read_sql_query('SELECT s.id, s.seat_number, s.student_name, sc.chinese, sc.english, sc.math, sc.social, sc.science FROM students s JOIN scores sc ON s.id = sc.student_id WHERE s.academic_year = ? AND s.semester = ?', conn, params=(year, sem))
            df = df_all.groupby(['id', 'seat_number', 'student_name'])[subs].mean().reset_index() if not df_all.empty else df_all
        else:
            df_all = pd.read_sql_query('SELECT s.student_name, sc.chinese, sc.english, sc.math, sc.social, sc.science FROM students s JOIN scores sc ON s.id = sc.student_id WHERE s.academic_year = ?', conn, params=(year,))
            df_base = pd.read_sql_query('SELECT id, seat_number, student_name FROM students WHERE academic_year = ? AND semester = ?', conn, params=(year, sem))
            df = pd.merge(df_base, df_all.groupby('student_name')[subs].mean().reset_index(), on='student_name', how='inner') if not df_all.empty else df_all
        conn.close()
        return self._process_dataframe(df)

    def _process_dataframe(self, df):
        if df.empty: return df
        subs = ['chinese', 'english', 'math', 'social', 'science']
        df['total_score'] = df[subs].sum(axis=1, min_count=1)
        for s in subs:
            df[f'{s}_pts'] = df[s].apply(self.convert_to_points)
        df['total_points'] = df[[f'{s}_pts' for s in subs]].sum(axis=1)
        return df

    # ================= 🌟 升級版：多維度互動繪圖引擎 =================

   
    def _draw_dynamic_trend(self, ax1, sid, mode):
        """根據模式動態繪製總體或單科趨勢"""
        conn = database.get_db_connection()
        # 獲取歷次成績、計算積點與 PR
        query = '''SELECT exam_type, chinese, english, math, social, science 
                   FROM scores WHERE student_id = ? 
                   AND exam_type IN ('第一次段考', '第二次段考', '第三次段考')'''
        df = pd.read_sql_query(query, conn, params=(sid,))
        conn.close()

        if df.empty:
            ax1.text(0.5, 0.5, "尚無足夠數據", ha='center', va='center'); return

        df['order'] = df['exam_type'].map({'第一次段考': 1, '第二次段考': 2, '第三次段考': 3})
        df = df.sort_values('order')
        exams = df['exam_type'].tolist()
        subs_en = ['chinese', 'english', 'math', 'social', 'science']
        subs_zh = ['國文', '英文', '數學', '社會', '自然']

        if mode == "total":
            # --- 1. 總體模式：總分、總點、總分PR、總點PR ---
            df['t_score'] = df[subs_en].sum(axis=1)
            df['t_pts'] = df[subs_en].applymap(self.convert_to_points).sum(axis=1)
            # PR 邏輯 (此處假設已有當前 DataFrame 計算好的 PR 供參考，簡化演示採樣顯示)
            
            # 主軸 (左)：總分
            ax1.plot(exams, df['t_score'], color='#27AE60', marker='o', lw=3, label='總分 (0-500)')
            ax1.set_ylabel('總分', color='#27AE60', fontweight='bold')
            ax1.set_ylim(0, 500)

            # 副軸 (右1)：總點數與 PR
            ax2 = ax1.twinx()
            ax2.plot(exams, df['t_pts'], color='#E67E22', marker='s', lw=2, ls='--', label='總積點 (0-35)')
            ax2.set_ylabel('積點 / PR', color='#666')
            ax2.set_ylim(0, 100) # PR 與 點數共用此軸刻度
            
            # 副軸標示文字
            for i, val in enumerate(df['t_pts']):
                ax2.text(i, val+2, f"{int(val)}點", color='#E67E22', ha='center', fontweight='bold')

            ax1.set_title("總體成績走勢 (總分 / 積點 / PR)", fontweight='bold')
            ax1.legend(loc='upper left', fontsize=9)
            ax2.legend(loc='upper right', fontsize=9)

        else:
            # --- 2. 各科模式：單科分數、積點、PR ---
            colors = ['#E74C3C', '#3498DB', '#F1C40F', '#8E44AD', '#34495E']
            ax2 = ax1.twinx()
            
            for i, s in enumerate(subs_en):
                # 畫分數 (左軸)
                ax1.plot(exams, df[s], color=colors[i], marker='o', lw=2, label=f"{subs_zh[i]}分")
                # 畫積點 (右軸標示文字)
                for x_idx, val in enumerate(df[s]):
                    pts = self.convert_to_points(val)
                    ax2.text(x_idx, pts*10+2, f"{pts}點", color=colors[i], fontsize=8, ha='center')

            ax1.set_ylabel('單科分數 (0-100)', fontweight='bold')
            ax1.set_ylim(0, 100)
            ax2.set_ylabel('積點分布預估', color='#999')
            ax2.set_ylim(0, 100)
            ax2.set_yticks([]) # 隱藏右側刻度，僅顯示文字點數標籤
            
            ax1.set_title("各學科細節走勢 (分數 & 積點標籤)", fontweight='bold')
            ax1.legend(loc='upper left', bbox_to_anchor=(1.05, 1), fontsize=8)
    
    def _draw_radar_chart(self, ax, sid, name, title):
        """繪製單科學力雷達圖（含修正後的圖例）"""
        r = self.current_df[self.current_df['id'] == sid].iloc[0]
        cats = ['國文', '英文', '數學', '社會', '自然']
        subs = ['chinese', 'english', 'math', 'social', 'science']
        
        # 準備分數與積點數據
        v1 = [r[s] if pd.notna(r[s]) else 0 for s in subs] + [r[subs[0]] if pd.notna(r[subs[0]]) else 0]
        v2 = [(r[f'{s}_pts'] * 100/7) for s in subs] + [(r[f'{subs[0]}_pts'] * 100/7)]
        ang = [n / 5 * 2 * np.pi for n in range(5)] + [0]
        
        # 繪製分數區塊
        ax.plot(ang, v1, lw=2, label='原始分數 (0-100)', color='#2E5984')
        ax.fill(ang, v1, alpha=0.1, color='#2E5984')
        
        # 繪製積點虛線
        ax.plot(ang, v2, lw=2, ls='--', label='會考積點 (等比放大)', color='#E67E22')
        
        ax.set_xticks(ang[:-1])
        ax.set_xticklabels(cats, fontweight='bold', fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_title(f"{title} - 學力分布", fontweight='bold', pad=20)
        
        # 🌟 加入圖例：顯示在右下方，避免遮擋
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)


    def _generate_ai_report_text(self, sid, name, is_long_term=False):
        conn = database.get_db_connection()
        df = pd.read_sql_query("SELECT exam_type, chinese, english, math, social, science FROM scores WHERE student_id = ? AND exam_type IN ('第一次段考', '第二次段考', '第三次段考')", conn, params=(sid,))
        conn.close()
        
        report = f"🤖 {name} 同學的 {'年度學習深度診斷' if is_long_term else 'AI 學習預測報表'}\n" + "-"*45 + "\n"
        if df.empty:
            return report + "⚠️ 目前資料不足。"

        subs_zh = ['國文', '英文', '數學', '社會', '自然']
        subs_en = ['chinese', 'english', 'math', 'social', 'science']
        df['total'] = df[subs_en].sum(axis=1, min_count=1)
        df['order'] = df['exam_type'].map({'第一次段考': 1, '第二次段考': 2, '第三次段考': 3})
        df = df.sort_values('order')

        report += "📈 【趨勢預測與各科預估落點】：\n"
        if len(df) >= 2:
            x = range(len(df))
            predictions = []
            for zh, en in zip(subs_zh, subs_en):
                y = df[en].fillna(df[en].mean()).values
                slope, intercept = np.polyfit(x, y, 1)
                pred = min(100, max(0, int(slope * (x[-1]+1) + intercept)))
                predictions.append(f"{zh}:{pred}分")
            
            total_y = df['total'].values
            t_slope, _ = np.polyfit(x, total_y, 1)
            t_pred = int(total_y[-1] + t_slope)
            report += f"🔮 下學期首考總分預估：{t_pred} 分\n"
            report += f"📝 各科預估落點：{', '.join(predictions)}\n\n"
        else:
            report += "⚠️ 目前僅有單次成績，建議待第二次段考後開啟精準預測。\n\n"

        improved, declined = [], []
        r = self.current_df[self.current_df['id'] == sid].iloc[0]
        for zh, en in zip(subs_zh, subs_en):
            scores = df[en].dropna().tolist()
            if len(scores) >= 2:
                diff = scores[-1] - scores[0]
                if diff >= 5:
                    improved.append(f"{zh}(▲{int(diff)})")
                elif diff <= -5:
                    declined.append(f"{zh}(▼{abs(int(diff))})")
        
        report += "💡 【全學期科目診斷】：\n"
        if improved:
            report += f"✅ 【表現進步】：{', '.join(improved)}。請繼續保持學習節奏。\n"
        if declined:
            report += f"⚠️ 【需要注意】：{', '.join(declined)}。這幾科出現下滑趨勢，需檢視弱點單元。\n"
        if not improved and not declined:
            report += "🎯 【各科狀況】：各科表現持平，建議針對擅長科目衝刺積點。\n"
        
        return report

    def print_class_report(self):
        if self.current_df.empty: return
        title, hdr = self.exam_type_var.get(), self._get_class_header()
        
        html = f"""<html><head><meta charset='utf-8'><style>
            body {{ font-family: 'Microsoft JhengHei'; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; text-align: center; font-size: 12px; }}
            th, td {{ border: 1px solid #ddd; padding: 6px; }}
            th {{ background: #f4f4f4; cursor: pointer; transition: 0.2s; position: relative; }}
            th:hover {{ background: #e0e0e0; }}
            th::after {{ content: ' ⇅'; font-size: 10px; color: #aaa; }}
            @media print {{ button {{ display: none; }} th::after {{ display: none; }} }}
        </style>
        <script>
            function sortT(n) {{
                var table = document.getElementById("rt"), tbody = table.tBodies[0], rows = Array.from(tbody.rows);
                var dir = table.getAttribute("data-dir") === "asc" ? "desc" : "asc";
                table.setAttribute("data-dir", dir);
                rows.sort((a, b) => {{
                    var x = a.cells[n].getAttribute("data-v") || a.cells[n].innerText;
                    var y = b.cells[n].getAttribute("data-v") || b.cells[n].innerText;
                    return (dir === "asc" ? 1 : -1) * (parseFloat(x) - parseFloat(y) || x.localeCompare(y));
                }});
                rows.forEach(r => tbody.appendChild(r));
            }}
        </script></head><body>
        <button onclick='window.print()'>🖨️ 列印總表</button><h1>{hdr}</h1><h3>{title} 班級成績總表</h3>
        <table id='rt' data-dir='desc'><thead><tr>
        <th rowspan='2' onclick='sortT(0)'>座號</th><th rowspan='2' onclick='sortT(1)'>姓名</th>
        <th colspan='2'>國文</th><th colspan='2'>英文</th><th colspan='2'>數學</th><th colspan='2'>社會</th><th colspan='2'>自然</th>
        <th colspan='3'>總分分析</th><th colspan='3'>積點分析</th>
        </tr><tr>
        <th onclick='sortT(2)'>分</th><th onclick='sortT(3)'>點</th><th onclick='sortT(4)'>分</th><th onclick='sortT(5)'>點</th>
        <th onclick='sortT(6)'>分</th><th onclick='sortT(7)'>點</th><th onclick='sortT(8)'>分</th><th onclick='sortT(9)'>點</th>
        <th onclick='sortT(10)'>分</th><th onclick='sortT(11)'>點</th>
        <th onclick='sortT(12)'>總分</th><th onclick='sortT(13)'>名次</th><th onclick='sortT(14)'>PR</th>
        <th onclick='sortT(15)'>總點</th><th onclick='sortT(16)'>名次</th><th onclick='sortT(17)'>PR</th>
        </tr></thead><tbody>"""
        
        for _, r in self.current_df.iterrows():
            html += f"<tr><td data-v='{r['seat_number']}'>{r['seat_number']}</td><td>{r['student_name']}</td>"
            for s in ['chinese','english','math','social','science']:
                html += f"<td data-v='{r[s]}'>{self._f_sc(r[s], r[f'{s}_diff'])}</td><td data-v='{r[f'{s}_pts']}'>{int(r[f'{s}_pts'])}</td>"
            html += f"<td data-v='{r['total_score']}'>{self._f_sc(r['total_score'], r['score_diff'])}</td><td data-v='{r['score_rank']}'>{int(r['score_rank'])}</td><td>{int(r['score_pr'])}</td>"
            html += f"<td data-v='{r['total_points']}' style='color:#E67E22; font-weight:bold;'>{self._f_sc(r['total_points'], r['point_diff'])}</td><td data-v='{r['point_rank']}'>{int(r['point_rank'])}</td><td>{int(r['point_pr'])}</td></tr>"
        
        html += "</tbody></table></body></html>"
        self._open_html(html, 'class_report.html')

    def print_individual_report(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showinfo("提示", "請先點選一位學生！")
            return
        v = self.tree.item(sel, "values")
        sid, name, title = int(v[0]), v[2], self.exam_type_var.get()
        hdr = self._get_class_header()
        
        student_rows = self.current_df[self.current_df['id'] == sid]
        if student_rows.empty: return
        r = student_rows.iloc[0]

        conn = database.get_db_connection()
        df_h = pd.read_sql_query("SELECT exam_type, chinese, english, math, social, science FROM scores WHERE student_id = ? AND exam_type IN ('第一次段考', '第二次段考', '第三次段考')", conn, params=(sid,))
        conn.close()
        hist_rows = ""
        if not df_h.empty:
            df_h['order'] = df_h['exam_type'].map({'第一次段考': 1, '第二次段考': 2, '第三次段考': 3})
            for _, h in df_h.sort_values('order').iterrows():
                hist_rows += f"<tr style='background:#f9f9f9;'><td>{h['exam_type']}</td>"
                for s in ['chinese','english','math','social','science']:
                    hist_rows += f"<td>{int(h[s]) if pd.notna(h[s]) else '-'}<br><small>({self.convert_to_points(h[s])}點)</small></td>"
                hist_rows += f"<td style='background:#eee; font-weight:bold;'>{int(h[['chinese','english','math','social','science']].sum())}</td></tr>"

        fig = plt.figure(figsize=(10, 4.5))
        self._draw_radar_chart(fig.add_subplot(121, polar=True), sid, name, title)
        self._draw_dynamic_trend(fig.add_subplot(122), sid, "total")  # 修正：添加 mode 參數 "total"
        plt.tight_layout()
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        c64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        ai_html = self._generate_ai_report_text(sid, name, "平均" in title).replace('\n', '<br>')

        html = f"""<html><head><meta charset='utf-8'><style>
            body {{ font-family: 'Microsoft JhengHei'; padding: 30px; max-width: 850px; margin: auto; }}
            .hdr {{ text-align: center; border-bottom: 2px solid #2E5984; padding-bottom: 10px; }}
            .info {{ display: flex; justify-content: space-between; background: #f4f4f4; padding: 15px; margin: 15px 0; font-weight: bold; border-radius: 5px; }}
            table {{ width: 100%; border-collapse: collapse; text-align: center; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; }}
            th {{ background: #2E5984; color: white; }}
            .ai {{ background: #f0f7ff; border-left: 5px solid #2E5984; padding: 20px; margin-top: 20px; border-radius: 5px; line-height: 1.6; }}
            @media print {{ button {{ display: none; }} }}
        </style></head><body>
            <button onclick='window.print()'>🖨️ 列印診斷報表</button>
            <div class='hdr'><h1>{hdr}</h1><h3>{title} 個人成績診斷書</h3></div>
            <div class='info'><span>🧑‍🎓 姓名：{name}</span><span>🏆 總分PR：{int(r['score_pr'])} | 積點PR：{int(r['point_pr'])}</span></div>
            <table><tr><th>考別 / 科目</th><th>國文</th><th>英文</th><th>數學</th><th>社會</th><th>自然</th><th style='background:#eee; color:#333;'>總分</th></tr>
            {hist_rows}
            <tr style='background:#eef; font-weight:bold; border-top: 2px solid #2E5984;'><td>{title}結算</td>
            <td>{round(r['chinese'],1)}<br><small>({int(r['chinese_pr'])}PR)</small></td>
            <td>{round(r['english'],1)}<br><small>({int(r['english_pr'])}PR)</small></td>
            <td>{round(r['math'],1)}<br><small>({int(r['math_pr'])}PR)</small></td>
            <td>{round(r['social'],1)}<br><small>({int(r['social_pr'])}PR)</small></td>
            <td>{round(r['science'],1)}<br><small>({int(r['science_pr'])}PR)</small></td>
            <td style='background:#E67E22; color:white;'>{round(r['total_score'],1)}分<br><small>({int(r['total_points'])}點)</small></td></tr></table>
            <div style='text-align:center; margin-top:20px;'><img src='data:image/png;base64,{c64}' width='100%'></div>
            <div class='ai'><h3>🔮 AI 學習分析預測</h3>{ai_html}</div>
        </body></html>"""
        self._open_html(html, f'rep_{sid}.html')

    def _f_sc(self, sc, df):
        s = round(sc, 1) if pd.notna(sc) else ""
        d = self.format_diff(df)
        if d != "-":
            color = "#27AE60" if "▲" in d else "#E74C3C"
            return f"{s}<br><span style='font-size:10px; color:{color};'>{d}</span>"
        return f"{s}"

    def _get_class_header(self):
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        s = {row['key']: row['value'] for row in cursor.fetchall()}
        conn.close()
        return f"{s.get('school_name', '')} {s.get('class_name', '')} - {s.get('teacher_name', '')}"

    def _open_html(self, html, fname):
        path = os.path.join(tempfile.gettempdir(), fname)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        webbrowser.open('file://' + os.path.realpath(path))

    def show_student_charts(self):
        sel = self.tree.focus()
        if not sel: return
        v = self.tree.item(sel, "values")
        sid, name = int(v[0]), v[2]
        win = tk.Toplevel(self.parent)
        win.title(f"互動圖表 - {name}")
        win.geometry("900x500")
        fig = plt.figure(figsize=(10, 5))
        self._draw_radar_chart(fig.add_subplot(121, polar=True), sid, name, self.exam_type_var.get())
        self._draw_dynamic_trend(fig.add_subplot(122), sid, "total")  # 修正：使用正確的方法名稱和參數
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def show_ai_report(self):
        sel = self.tree.focus()
        if not sel: return
        v = self.tree.item(sel, "values")
        sid, name = int(v[0]), v[2]
        messagebox.showinfo("AI 診斷結果", self._generate_ai_report_text(sid, name, "平均" in self.exam_type_var.get()))