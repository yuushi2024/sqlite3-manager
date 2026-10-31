import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3

import db_utils

# ==========================================
#  モダンな入力ダイアログクラス (日本語版 & 色修正)
# ==========================================
class ModernDialog(tk.Toplevel):
    """VS Code風のモダンな入力ダイアログ"""
    def __init__(self, parent, title, fields, values=None, font_family="TkDefaultFont"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg="#252526") # 背景色
        self.result = None
        self.entries = {}
        self.font_family = font_family

        # ウィンドウサイズと位置調整
        # 高さを動的に調整
        window_height = 150 + len(fields) * 65
        self.geometry(f"500x{window_height}")
        self.resizable(False, False)

        # メインコンテナ
        main_frame = tk.Frame(self, bg="#252526", padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)

        # フォント設定
        label_font = (font_family, 9, 'bold')
        entry_font = (font_family, 10)

        # カラー設定（文字が見えない問題を修正）
        entry_bg = "#3c3c3c"       # 入力欄の背景
        entry_fg = "#ffffff"       # 入力文字の色（白）
        cursor_color = "#ffffff"   # カーソルの色（白）

        # フィールド生成
        for field in fields:
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
                               activebackground="#505050", activeforeground="white", width=12, font=(font_family, 9))
        btn_cancel.pack(side='right', padx=10)

        # 保存ボタン（青色）
        btn_save = tk.Button(btn_frame, text="保存する", command=self.on_save,
                             bg="#007acc", fg="white", relief="flat",
                             activebackground="#0062a3", activeforeground="white", width=15, font=(font_family, 9, 'bold'))
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
    # 日本語表示に適したフォント候補（上から順に採用、無ければTk既定）
    FONT_CANDIDATES = ("Yu Gothic UI", "Meiryo UI", "Meiryo", "Noto Sans CJK JP", "Noto Sans JP")
    MONO_FONT_CANDIDATES = ("Consolas", "Menlo", "DejaVu Sans Mono", "Noto Sans Mono")

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

        self.font_family = db_utils.pick_font_family(root, self.FONT_CANDIDATES)
        self.mono_font = db_utils.pick_font_family(
            root, self.MONO_FONT_CANDIDATES, fallback="TkFixedFont"
        )

        self.setup_theme()
        self.create_layout()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_theme(self):
        # フォント設定（利用可能な日本語フォントを自動選択）
        default_font = (self.font_family, 10)
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
                        font=(self.font_family, 9, 'bold'),
                        padding=8,
                        relief="flat")
        style.map("Treeview.Heading", background=[('active', '#404040')])

        # サイドバー用 Treeview
        style.configure("Sidebar.Treeview",
                        background=colors["bg_sidebar"],
                        foreground=colors["fg_primary"],
                        fieldbackground=colors["bg_sidebar"],
                        rowheight=28,
                        font=(self.font_family, 11))
        style.map("Sidebar.Treeview", background=[("selected", colors["selected"])])

        # ボタン
        style.configure("TButton", padding=6, relief="flat", background="#3c3c3c", foreground="white")
        style.map("TButton", background=[('active', '#505050')])

        # アクセントボタン（青）
        style.configure("Accent.TButton", background=colors["accent"], font=(self.font_family, 9, 'bold'))
        style.map("Accent.TButton", background=[('active', '#0062a3')])

        # タブ
        style.configure("TNotebook", background=colors["bg_dark"], tabmargins=[0, 0, 0, 0])
        style.configure("TNotebook.Tab", padding=[20, 8], font=(self.font_family, 10))
        style.map("TNotebook.Tab", background=[("selected", colors["bg_dark"]), ("!selected", "#2d2d2d")])

    def create_layout(self):
        # トップバー
        top_bar = tk.Frame(self.root, bg="#333333", height=40)
        top_bar.pack(fill='x')
        top_bar.pack_propagate(False)

        tk.Label(top_bar, text="Py-SQLite Studio JP", bg="#333333", fg="#007acc", font=(self.font_family, 10, 'bold'), padx=15).pack(side='left')

        btn_open = tk.Button(top_bar, text="📂 データベースを開く", command=self.open_db,
                             bg="#333333", fg="white", relief="flat", activebackground="#444", activeforeground="white")
        btn_open.pack(side='left', padx=10)

        self.lbl_status = tk.Label(top_bar, text="未接続", bg="#333333", fg="#888", font=(self.font_family, 9))
        self.lbl_status.pack(side='right', padx=15)

        # 画面分割
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill='both', expand=True)

        # サイドバー
        sidebar_frame = ttk.Frame(paned, style="Sidebar.TFrame", width=250)
        paned.add(sidebar_frame, weight=1)

        tk.Label(sidebar_frame, text="エクスプローラー", bg=self.colors["bg_sidebar"], fg="#888", font=(self.font_family, 8, 'bold'), anchor='w').pack(fill='x', padx=10, pady=10)

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
        entry_search = tk.Entry(search_frame, textvariable=self.search_var, bg="#3c3c3c", fg="white", insertbackground="white", relief="flat", font=(self.font_family, 10))
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

        tk.Label(container, text="SQLクエリ入力:", bg=self.colors["bg_dark"], fg="#aaa", font=(self.font_family, 10, 'bold')).pack(anchor='w')

        self.txt_sql = tk.Text(container, height=8, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
                               relief="solid", borderwidth=1, font=(self.mono_font, 11))
        self.txt_sql.pack(fill='x', pady=5)
        self.txt_sql.bind('<Control-Return>', lambda e: (self.run_sql(), "break")[1])

        btn_run = ttk.Button(container, text="▶ 実行 (Ctrl+Enter)", style="Accent.TButton", command=self.run_sql)
        btn_run.pack(anchor='e', pady=(0, 10))

        self.tree_sql = ttk.Treeview(container, style="Treeview", height=10)
        self.tree_sql.pack(fill='both', expand=True)

    # ============================
    #  ロジック
    # ============================

    def on_closing(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except sqlite3.Error:
                pass
            self.conn = None
        self.root.destroy()

    def open_db(self):
        path = filedialog.askopenfilename(filetypes=[("SQLite データベース", "*.db *.sqlite *.sqlite3"), ("すべてのファイル", "*.*")])
        if not path: return

        try:
            if self.conn: self.conn.close()
            self.conn = sqlite3.connect(path)
            self.db_path = path
            filename = path.replace("\\", "/").split("/")[-1]
            self.lbl_status.config(text=f"接続中: {filename}")
            self.current_table = None
            self.primary_key = None
            self.table_meta = []
            self.tree.delete(*self.tree.get_children())
            self.refresh_sidebar()
        except Exception as e:
            messagebox.showerror("接続エラー", str(e))

    def refresh_sidebar(self):
        self.sidebar_tree.delete(*self.sidebar_tree.get_children())
        if self.conn is None:
            return
        root_id = self.sidebar_tree.insert("", "end", text=" テーブル一覧", open=True)

        for name in db_utils.list_tables(self.conn):
            self.sidebar_tree.insert(root_id, "end", text=f" 📄 {name}", values=(name,))

    def on_table_select(self, event):
        sel = self.sidebar_tree.selection()
        if not sel: return

        item = self.sidebar_tree.item(sel[0])
        if not item['values']: return

        self.current_table = item['values'][0]
        self.current_page = 0
        self.search_var.set("")

        self.table_meta = db_utils.table_columns(self.conn, self.current_table)
        self.primary_key = db_utils.primary_key_column(self.table_meta)

        self.load_data()

    def load_data(self):
        if not self.current_table or self.conn is None: return

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = [c[1] for c in self.table_meta]
        self.tree["show"] = "headings"

        for col in self.table_meta:
            name = col[1]
            self.tree.heading(name, text=name, anchor='w')
            self.tree.column(name, width=120, anchor='w')

        try:
            rows, row_ids, total, self.current_page = db_utils.fetch_table_page(
                self.conn,
                self.current_table,
                self.table_meta,
                page=self.current_page,
                page_size=self.page_size,
                search_text=self.search_var.get(),
            )
        except sqlite3.Error as e:
            messagebox.showerror("エラー", str(e))
            return

        for row_id, row in zip(row_ids, rows):
            self.tree.insert("", "end", iid=row_id, values=row)

        offset = self.current_page * self.page_size
        start = offset + 1 if total > 0 else 0
        end = min(offset + self.page_size, total)
        self.lbl_page_info.config(text=f"表示: {start}-{end} / 全 {total} 件")

    def add_row(self):
        if not self.current_table: return
        fields = [c[1] for c in self.table_meta]

        dlg = ModernDialog(self.root, f"{self.current_table} に追加", fields, font_family=self.font_family)

        if dlg.result:
            try:
                cols = []
                vals = []
                qs = []
                for k, v in dlg.result.items():
                    if v == "": continue
                    cols.append(db_utils.quote_identifier(k))
                    vals.append(v)
                    qs.append("?")

                if not cols: return

                table = db_utils.quote_identifier(self.current_table)
                sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(qs)})"
                self.conn.execute(sql, vals)
                self.conn.commit()
                self.load_data()
            except Exception as e:
                messagebox.showerror("エラー", str(e))

    def on_double_click(self, event):
        if not self.current_table: return

        item_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not item_id or not col_id: return

        col_idx = int(col_id.replace('#', '')) - 1
        if col_idx < 0 or col_idx >= len(self.table_meta): return
        col_name = self.table_meta[col_idx][1]

        current_val = self.tree.item(item_id, 'values')[col_idx]

        dlg = ModernDialog(self.root, f"編集: {col_name}", [col_name], values={col_name: current_val}, font_family=self.font_family)

        if dlg.result:
            new_val = dlg.result[col_name]
            if new_val == current_val: return

            # 主キーが無いテーブルでも編集できるよう、行の識別には rowid を使う
            row_key = self.primary_key if self.primary_key else "rowid"
            try:
                table = db_utils.quote_identifier(self.current_table)
                sql = (f"UPDATE {table} SET {db_utils.quote_identifier(col_name)} = ? "
                       f"WHERE {db_utils.quote_identifier(row_key)} = ?")
                self.conn.execute(sql, (new_val, item_id))
                self.conn.commit()
                self.load_data()
            except Exception as e:
                messagebox.showerror("エラー", str(e))

    def delete_row(self):
        sel = self.tree.selection()
        if not sel: return

        if messagebox.askyesno("確認", f"選択した {len(sel)} 件のデータを削除しますか？"):
            row_key = self.primary_key if self.primary_key else "rowid"
            try:
                table = db_utils.quote_identifier(self.current_table)
                sql = f"DELETE FROM {table} WHERE {db_utils.quote_identifier(row_key)} = ?"
                for iid in sel:
                    self.conn.execute(sql, (iid,))
                self.conn.commit()
                self.load_data()
            except Exception as e:
                messagebox.showerror("エラー", str(e))

    def run_sql(self):
        query = self.txt_sql.get("1.0", tk.END).strip()
        if not query or self.conn is None: return

        self.tree_sql.delete(*self.tree_sql.get_children())
        statements = db_utils.split_statements(query)
        last_cur = None
        try:
            for stmt in statements:
                last_cur = self.conn.execute(stmt)
        except sqlite3.Error as e:
            messagebox.showerror("SQLエラー", str(e))
            return

        # 表示用の結果は最後に実行した SELECT のもの
        cur = last_cur
        if cur is not None and cur.description:
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
            messagebox.showinfo("完了", f"実行完了しました。\n影響行数: {cur.rowcount if cur else 0}")
            if self.current_table: self.load_data()

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
            try:
                count = db_utils.export_table_to_csv(self.conn, self.current_table, self.table_meta, path)
                messagebox.showinfo("完了", f"{count} 件をCSVに保存しました。")
            except Exception as e:
                messagebox.showerror("エラー", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    db_utils.enable_dpi_awareness()

    app = ModernSQLiteStudio(root)
    root.mainloop()
