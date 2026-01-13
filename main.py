import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import csv

# ==========================================
#  モダンな入力ダイアログクラス (日本語版 & 色修正)
# ==========================================
class ModernDialog(tk.Toplevel):
    """VS Code風のモダンな入力ダイアログ"""
    def __init__(self, parent, title, fields, values=None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg="#252526") # 背景色
        self.result = None
        self.entries = {}
        
        # ウィンドウサイズと位置調整
        # 高さを動的に調整
        window_height = 150 + len(fields) * 65
        self.geometry(f"500x{window_height}")
        self.resizable(False, False)
        
        # メインコンテナ
        main_frame = tk.Frame(self, bg="#252526", padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)

        # フォント設定
        label_font = ('Yu Gothic UI', 9, 'bold')
        entry_font = ('Yu Gothic UI', 10)
        
        # カラー設定（文字が見えない問題を修正）
        entry_bg = "#3c3c3c"       # 入力欄の背景
        entry_fg = "#ffffff"       # 入力文字の色（白）
        cursor_color = "#ffffff"   # カーソルの色（白）
        
        # フィールド生成
        for i, field in enumerate(fields):
            # ラベル
            lbl = tk.Label(main_frame, text=field, bg="#252526", fg="#cccccc", font=label_font, anchor='w')
            lbl.pack(fill='x', pady=(10, 2))
            
            # エントリー（入力欄）
            initial_val = values.get(field, "") if values else ""
            
            # ここで色を明示的に指定して、文字が見えない問題を回避
            entry = tk.Entry(main_frame, 
                             bg=entry_bg, 
                             fg=entry_fg, 
                             insertbackground=cursor_color, # カーソル色
                             selectbackground="#007acc",    # 選択範囲の背景
                             selectforeground="#ffffff",    # 選択文字の色
                             relief="flat", 
                             font=entry_font)
            
            entry.pack(fill='x', ipady=5, pady=(0, 5))
            entry.insert(0, str(initial_val) if initial_val is not None else "")
            
            self.entries[field] = entry

        # ボタンエリア
        btn_frame = tk.Frame(self, bg="#252526", pady=20)
        btn_frame.pack(fill='x', side='bottom')

        # キャンセルボタン
        btn_cancel = tk.Button(btn_frame, text="キャンセル", command=self.destroy,
                               bg="#3c3c3c", fg="white", relief="flat", 
                               activebackground="#505050", activeforeground="white", width=12, font=('Yu Gothic UI', 9))
        btn_cancel.pack(side='right', padx=10)

        # 保存ボタン（青色）
        btn_save = tk.Button(btn_frame, text="保存する", command=self.on_save,
                             bg="#007acc", fg="white", relief="flat", 
                             activebackground="#0062a3", activeforeground="white", width=15, font=('Yu Gothic UI', 9, 'bold'))
        btn_save.pack(side='right')

        # モーダル化（親ウィンドウを操作できなくする）
        self.transient(parent)
        self.grab_set()
        self.center_window(parent)
        self.wait_window()

    def center_window(self, parent):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def on_save(self):
        self.result = {field: entry.get() for field, entry in self.entries.items()}
        self.destroy()


# ==========================================
#  メインアプリケーション (日本語UI)
# ==========================================
class ModernSQLiteStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite Studio - 日本語版")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1e1e1e")

        self.db_path = None
        self.conn = None
        self.current_table = None
        self.primary_key = None
        self.page_size = 100
        self.current_page = 0
        self.table_meta = []

        self.setup_theme()
        self.create_layout()

    def setup_theme(self):
        # フォント設定（Windows向けにYu Gothic UIを使用）
        default_font = ('Yu Gothic UI', 10)
        self.root.option_add("*Font", default_font)

        style = ttk.Style()
        style.theme_use('clam')

        # カラー定義
        colors = {
            "bg_dark": "#1e1e1e",
            "bg_sidebar": "#252526",
            "bg_list": "#1e1e1e",
            "fg_primary": "#d4d4d4",
            "accent": "#007acc",
            "header": "#2d2d2d",
            "selected": "#094771",
        }
        self.colors = colors

        # スタイル設定
        style.configure(".", background=colors["bg_dark"], foreground=colors["fg_primary"], borderwidth=0)
        style.configure("TFrame", background=colors["bg_dark"])
        style.configure("Sidebar.TFrame", background=colors["bg_sidebar"])

        # Treeview (表)
        style.configure("Treeview", 
                        background=colors["bg_list"],
                        foreground=colors["fg_primary"], 
                        fieldbackground=colors["bg_list"],
                        rowheight=30,
                        borderwidth=0)
        style.map("Treeview", background=[("selected", colors["selected"])])
        
        # Treeview ヘッダー
        style.configure("Treeview.Heading", 
                        background=colors["header"], 
                        foreground=colors["fg_primary"],
                        font=('Yu Gothic UI', 9, 'bold'),
                        padding=8,
                        relief="flat")
        style.map("Treeview.Heading", background=[('active', '#404040')])

        # サイドバー用 Treeview
        style.configure("Sidebar.Treeview", 
                        background=colors["bg_sidebar"],
                        foreground=colors["fg_primary"],
                        fieldbackground=colors["bg_sidebar"],
                        rowheight=28,
                        font=('Yu Gothic UI', 11))
        style.map("Sidebar.Treeview", background=[("selected", colors["selected"])])

        # ボタン
        style.configure("TButton", padding=6, relief="flat", background="#3c3c3c", foreground="white")
        style.map("TButton", background=[('active', '#505050')])

        # アクセントボタン（青）
        style.configure("Accent.TButton", background=colors["accent"], font=('Yu Gothic UI', 9, 'bold'))
        style.map("Accent.TButton", background=[('active', '#0062a3')])

        # タブ
        style.configure("TNotebook", background=colors["bg_dark"], tabmargins=[0, 0, 0, 0])
        style.configure("TNotebook.Tab", padding=[20, 8], font=('Yu Gothic UI', 10))
        style.map("TNotebook.Tab", background=[("selected", colors["bg_dark"]), ("!selected", "#2d2d2d")])

    def create_layout(self):
        # トップバー
        top_bar = tk.Frame(self.root, bg="#333333", height=40)
        top_bar.pack(fill='x')
        top_bar.pack_propagate(False)
        
        tk.Label(top_bar, text="Py-SQLite Studio JP", bg="#333333", fg="#007acc", font=('Yu Gothic UI', 10, 'bold'), padx=15).pack(side='left')
        
        btn_open = tk.Button(top_bar, text="📂 データベースを開く", command=self.open_db, 
                             bg="#333333", fg="white", relief="flat", activebackground="#444", activeforeground="white")
        btn_open.pack(side='left', padx=10)

        self.lbl_status = tk.Label(top_bar, text="未接続", bg="#333333", fg="#888", font=('Yu Gothic UI', 9))
        self.lbl_status.pack(side='right', padx=15)

        # 画面分割
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill='both', expand=True)

        # サイドバー
        sidebar_frame = ttk.Frame(paned, style="Sidebar.TFrame", width=250)
        paned.add(sidebar_frame, weight=1)

        tk.Label(sidebar_frame, text="エクスプローラー", bg=self.colors["bg_sidebar"], fg="#888", font=('Yu Gothic UI', 8, 'bold'), anchor='w').pack(fill='x', padx=10, pady=10)
        
        self.sidebar_tree = ttk.Treeview(sidebar_frame, style="Sidebar.Treeview", show="tree", selectmode="browse")
        self.sidebar_tree.pack(fill='both', expand=True)
        self.sidebar_tree.bind('<<TreeviewSelect>>', self.on_table_select)

        # メインコンテンツ
        content_frame = ttk.Frame(paned)
        paned.add(content_frame, weight=5)

        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill='both', expand=True)

        # タブ1: データ編集
        self.tab_data = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_data, text="  データ編集  ")
        self.setup_data_view()

        # タブ2: SQL
        self.tab_sql = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sql, text="  SQL実行  ")
        self.setup_sql_view()

    def setup_data_view(self):
        # ツールバー
        toolbar = tk.Frame(self.tab_data, bg=self.colors["bg_dark"], pady=10, padx=10)
        toolbar.pack(fill='x')

        ttk.Button(toolbar, text="➕ 行を追加", style="Accent.TButton", command=self.add_row).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar, text="🗑 行を削除", command=self.delete_row).pack(side='left', padx=5)
        ttk.Button(toolbar, text="⬇ CSV保存", command=self.export_csv).pack(side='left', padx=5)

        # 検索
        search_frame = tk.Frame(toolbar, bg=self.colors["bg_dark"])
        search_frame.pack(side='right')
        
        self.search_var = tk.StringVar()
        entry_search = tk.Entry(search_frame, textvariable=self.search_var, bg="#3c3c3c", fg="white", insertbackground="white", relief="flat", font=('Yu Gothic UI', 10))
        entry_search.pack(side='left', ipady=4, ipadx=5)
        entry_search.bind('<Return>', lambda e: self.load_data())
        
        btn_search = tk.Button(search_frame, text="🔍", command=self.load_data, bg="#3c3c3c", fg="white", relief="flat")
        btn_search.pack(side='left', padx=(2,0))

        # テーブル表示
        grid_frame = ttk.Frame(self.tab_data)
        grid_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(grid_frame, style="Treeview", selectmode="extended")
        
        vsb = ttk.Scrollbar(grid_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(grid_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')
        
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_rowconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_double_click)

        # フッター（ページネーション）
        footer = tk.Frame(self.tab_data, bg=self.colors["bg_dark"], pady=5, padx=10)
        footer.pack(fill='x')
        
        self.lbl_page_info = tk.Label(footer, text="0 件", bg=self.colors["bg_dark"], fg="#888")
        self.lbl_page_info.pack(side='right')
        
        btn_prev = tk.Button(footer, text="< 前へ", command=self.prev_page, bg=self.colors["bg_dark"], fg="white", relief="flat", activebackground="#333", activeforeground="white")
        btn_prev.pack(side='left')
        btn_next = tk.Button(footer, text="次へ >", command=self.next_page, bg=self.colors["bg_dark"], fg="white", relief="flat", activebackground="#333", activeforeground="white")
        btn_next.pack(side='left')

    def setup_sql_view(self):
        container = tk.Frame(self.tab_sql, bg=self.colors["bg_dark"], padx=10, pady=10)
        container.pack(fill='both', expand=True)
        
        tk.Label(container, text="SQLクエリ入力:", bg=self.colors["bg_dark"], fg="#aaa", font=('Yu Gothic UI', 10, 'bold')).pack(anchor='w')
        
        self.txt_sql = tk.Text(container, height=8, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", 
                               relief="solid", borderwidth=1, font=('Consolas', 11))
        self.txt_sql.pack(fill='x', pady=5)
        self.txt_sql.bind('<Control-Return>', lambda e: self.run_sql())
        
        btn_run = ttk.Button(container, text="▶ 実行 (Ctrl+Enter)", style="Accent.TButton", command=self.run_sql)
        btn_run.pack(anchor='e', pady=(0, 10))
        
        self.tree_sql = ttk.Treeview(container, style="Treeview", height=10)
        self.tree_sql.pack(fill='both', expand=True)

    # ============================
    #  ロジック
    # ============================

    def open_db(self):
        path = filedialog.askopenfilename(filetypes=[("SQLite データベース", "*.db"), ("すべてのファイル", "*.*")])
        if not path: return
        
        try:
            if self.conn: self.conn.close()
            self.conn = sqlite3.connect(path)
            self.db_path = path
            filename = path.replace("\\", "/").split("/")[-1]
            self.lbl_status.config(text=f"接続中: {filename}")
            self.refresh_sidebar()
        except Exception as e:
            messagebox.showerror("接続エラー", str(e))

    def refresh_sidebar(self):
        self.sidebar_tree.delete(*self.sidebar_tree.get_children())
        root_id = self.sidebar_tree.insert("", "end", text=" テーブル一覧", open=True)
        
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cur.fetchall()
        
        for t in tables:
            self.sidebar_tree.insert(root_id, "end", text=f" 📄 {t[0]}", values=(t[0],))

    def on_table_select(self, event):
        sel = self.sidebar_tree.selection()
        if not sel: return
        
        item = self.sidebar_tree.item(sel[0])
        if not item['values']: return
        
        self.current_table = item['values'][0]
        self.current_page = 0
        
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({self.current_table})")
        self.table_meta = cur.fetchall()
        
        self.primary_key = None
        for col in self.table_meta:
            if col[5] >= 1: self.primary_key = col[1]

        self.load_data()

    def load_data(self):
        if not self.current_table: return
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = [c[1] for c in self.table_meta]
        self.tree["show"] = "headings"
        
        for col in self.table_meta:
            name = col[1]
            self.tree.heading(name, text=name, anchor='w')
            self.tree.column(name, width=120, anchor='w')

        cur = self.conn.cursor()
        query = f"SELECT * FROM {self.current_table}"
        params = []

        search_txt = self.search_var.get()
        if search_txt:
            cols = [c[1] for c in self.table_meta]
            query += " WHERE " + " OR ".join([f"{c} LIKE ?" for c in cols])
            params = [f"%{search_txt}%" for _ in cols]

        limit = self.page_size
        offset = self.current_page * limit
        
        cur.execute(f"SELECT COUNT(*) FROM ({query})", params)
        total = cur.fetchone()[0]
        
        query += f" LIMIT {limit} OFFSET {offset}"
        cur.execute(query, params)
        
        for row in cur.fetchall():
            pk_idx = -1
            if self.primary_key:
                for idx, col in enumerate(self.table_meta):
                    if col[1] == self.primary_key:
                        pk_idx = idx
                        break
            
            row_id = str(row[pk_idx]) if pk_idx >= 0 else None
            self.tree.insert("", "end", iid=row_id, values=row)

        start = offset + 1 if total > 0 else 0
        end = min(offset + limit, total)
        self.lbl_page_info.config(text=f"表示: {start}-{end} / 全 {total} 件")

    def add_row(self):
        if not self.current_table: return
        fields = [c[1] for c in self.table_meta]
        
        dlg = ModernDialog(self.root, f"{self.current_table} に追加", fields)
        
        if dlg.result:
            try:
                cols = []
                vals = []
                qs = []
                for k, v in dlg.result.items():
                    if v == "": continue
                    cols.append(k)
                    vals.append(v)
                    qs.append("?")
                
                if not cols: return

                sql = f"INSERT INTO {self.current_table} ({','.join(cols)}) VALUES ({','.join(qs)})"
                self.conn.execute(sql, vals)
                self.conn.commit()
                self.load_data()
            except Exception as e:
                messagebox.showerror("エラー", str(e))

    def on_double_click(self, event):
        if not self.current_table or not self.primary_key: return
        
        item_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not item_id or not col_id: return
        
        col_idx = int(col_id.replace('#', '')) - 1
        col_name = self.table_meta[col_idx][1]
        
        current_val = self.tree.item(item_id, 'values')[col_idx]
        
        dlg = ModernDialog(self.root, f"編集: {col_name}", [col_name], values={col_name: current_val})
        
        if dlg.result:
            new_val = dlg.result[col_name]
            if new_val == current_val: return
            
            try:
                sql = f"UPDATE {self.current_table} SET {col_name} = ? WHERE {self.primary_key} = ?"
                self.conn.execute(sql, (new_val, item_id))
                self.conn.commit()
                self.load_data()
            except Exception as e:
                messagebox.showerror("エラー", str(e))

    def delete_row(self):
        sel = self.tree.selection()
        if not sel or not self.primary_key: return
        
        if messagebox.askyesno("確認", f"選択した {len(sel)} 件のデータを削除しますか？"):
            try:
                for iid in sel:
                    self.conn.execute(f"DELETE FROM {self.current_table} WHERE {self.primary_key} = ?", (iid,))
                self.conn.commit()
                self.load_data()
            except Exception as e:
                messagebox.showerror("エラー", str(e))
    
    def run_sql(self):
        query = self.txt_sql.get("1.0", tk.END).strip()
        if not query: return
        
        self.tree_sql.delete(*self.tree_sql.get_children())
        try:
            cur = self.conn.cursor()
            cur.execute(query)
            
            if cur.description:
                cols = [d[0] for d in cur.description]
                self.tree_sql["columns"] = cols
                self.tree_sql["show"] = "headings"
                for c in cols:
                    self.tree_sql.heading(c, text=c)
                    self.tree_sql.column(c, width=100)
                for row in cur.fetchall():
                    self.tree_sql.insert("", "end", values=row)
            else:
                self.conn.commit()
                messagebox.showinfo("完了", f"実行完了しました。\n影響行数: {cur.rowcount}")
                if self.current_table: self.load_data()
        except Exception as e:
            messagebox.showerror("SQLエラー", str(e))

    def next_page(self):
        self.current_page += 1
        self.load_data()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_data()

    def export_csv(self):
        if not self.current_table: return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV ファイル", "*.csv")])
        if path:
            cur = self.conn.cursor()
            cur.execute(f"SELECT * FROM {self.current_table}")
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow([c[1] for c in self.table_meta])
                w.writerows(cur.fetchall())

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = ModernSQLiteStudio(root)
    root.mainloop()