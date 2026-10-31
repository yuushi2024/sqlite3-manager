# SQLite Studio (日本語版)

Tkinter 製の軽量な SQLite データベース管理 GUI です。VS Code 風のダークテーマで、
テーブルの閲覧・編集・SQL 実行・CSV エクスポートができます。

## 主な機能

- データベースファイルを開いてテーブル一覧を表示
- テーブルデータのページ送り表示(1 ページ 100 件)
- 行の追加 / ダブルクリックでセル編集 / 行の削除
- 全列を対象とした部分一致検索(LIKE、ワイルドカードはエスケープ)
- SQL タブで任意のクエリを実行(複数文のスクリプト対応、Ctrl+Enter で実行)
- 表示中テーブルの CSV エクスポート(Excel 対応の UTF-8 BOM 付き)

## 必要環境

- Python 3.8 以上
- Tkinter(`python3-tk`。Windows/macOS の標準 Python には同梱)
- 追加のサードパーティ製ライブラリは不要です(標準ライブラリのみ)

## 使い方

```bash
python main.py
```

1. 上部の「📂 データベースを開く」から `.db` / `.sqlite` / `.sqlite3` を選択
2. 左のエクスプローラーでテーブルを選択するとデータが表示されます
3. 「データ編集」タブで行の追加・編集・削除、「SQL 実行」タブで自由なクエリを実行

## 構成

| ファイル | 役割 |
| --- | --- |
| `main.py` | Tkinter GUI(画面と操作) |
| `db_utils.py` | 画面に依存しない SQLite 処理(識別子のクォート、ページング、検索、CSV 出力など) |
| `tests/test_db_utils.py` | `db_utils` のユニットテスト |

DB 操作は `db_utils.py` に分離してあり、GUI なしでテストできます。

## テスト

```bash
python -m unittest discover -s tests -v
```

実際の SQLite(インメモリ)に対してテストを実行します。

## 実装上の注意

- テーブル名・列名は必ずダブルクォートでエスケープしています。SQLite では識別子を
  プレースホルダにできないため、`quote_identifier` で安全に埋め込みます。
- 主キーのないテーブルは SQLite の暗黙の `rowid` を使って行を識別し、編集・削除を
  可能にしています。
- 日本語フォントは環境に応じて自動選択します(Yu Gothic UI → Meiryo → Noto Sans など)。
