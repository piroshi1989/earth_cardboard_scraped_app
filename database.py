import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import os

class Database:
    def __init__(self):
        # データベースファイルをカレントディレクトリのdataフォルダに保存
        os.makedirs('data', exist_ok=True)
        db_path = os.path.join('data', 'scraping.db')
        print(f"Using database at: {db_path}")  # デバッグ用
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        with self.conn:
            print("Creating table if not exists...")  # デバッグ用
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS scraped_data (
                    url TEXT PRIMARY KEY,
                    種類 TEXT,
                    長さ_内寸 REAL,
                    幅_内寸 REAL,
                    深さ_内寸 REAL,
                    外形_三辺合計 REAL,
                    色 TEXT,
                    印刷 TEXT,
                    形式 TEXT,
                    厚み REAL,
                    材質 TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    データ取得日 TIMESTAMP,
                    枚数_1 REAL,
                    枚数_10 REAL,
                    枚数_20 REAL,
                    枚数_30 REAL,
                    枚数_40 REAL,
                    枚数_50 REAL,
                    枚数_60 REAL,
                    枚数_70 REAL,
                    枚数_80 REAL,
                    枚数_100 REAL,
                    枚数_110 REAL,
                    枚数_120 REAL,
                    枚数_130 REAL,
                    枚数_140 REAL,
                    枚数_150 REAL,
                    枚数_160 REAL,
                    枚数_170 REAL,
                    枚数_180 REAL,
                    枚数_190 REAL,
                    枚数_195 REAL,
                    枚数_200 REAL,
                    枚数_210 REAL,
                    枚数_220 REAL,
                    枚数_240 REAL,
                    枚数_250 REAL,
                    枚数_260 REAL,
                    枚数_270 REAL,
                    枚数_280 REAL,
                    枚数_285 REAL,
                    枚数_300 REAL,
                    枚数_320 REAL,
                    枚数_330 REAL,
                    枚数_340 REAL,
                    枚数_350 REAL,
                    枚数_360 REAL,
                    枚数_380 REAL,
                    枚数_390 REAL,
                    枚数_400 REAL,
                    枚数_420 REAL,
                    枚数_440 REAL,
                    枚数_450 REAL,
                    枚数_480 REAL,
                    枚数_500 REAL,
                    枚数_540 REAL,
                    枚数_550 REAL,
                    枚数_560 REAL,
                    枚数_600 REAL,
                    枚数_640 REAL,
                    枚数_650 REAL,
                    枚数_700 REAL,
                    枚数_720 REAL,
                    枚数_750 REAL,
                    枚数_780 REAL,
                    枚数_800 REAL,
                    枚数_840 REAL,
                    枚数_900 REAL,
                    枚数_960 REAL,
                    枚数_1000 REAL,
                    枚数_1050 REAL,
                    枚数_1080 REAL,
                    枚数_1120 REAL,
                    枚数_1200 REAL,
                    枚数_1250 REAL,
                    枚数_1300 REAL,
                    枚数_1400 REAL,
                    枚数_1500 REAL,
                    枚数_1600 REAL,
                    枚数_1750 REAL,
                    枚数_1960 REAL,
                    枚数_2000 REAL,
                    枚数_2030 REAL,
                    枚数_2040 REAL,
                    枚数_2080 REAL,
                    枚数_2100 REAL,
                    枚数_2500 REAL,
                    枚数_3000 REAL,
                    枚数_3010 REAL,
                    枚数_3040 REAL,
                    枚数_3080 REAL
                )
            """)
            print("Table creation completed")  # デバッグ用

    def _convert_value(self, value):
        """データ型を適切に変換する"""
        if pd.isna(value):
            return None
        if isinstance(value, (np.int64, np.float64)):
            return float(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def save_data(self, df):
        print("Saving data to database...")  # デバッグ用
        print(f"Columns in DataFrame: {df.columns.tolist()}")  # デバッグ用
        # カラム名の変換（カッコをアンダースコアに置換）
        df.columns = df.columns.str.replace('(', '_').str.replace(')', '')
        with self.conn:
            for _, row in df.iterrows():
                # 値を適切な型に変換
                values = [self._convert_value(v) for v in row]
                
                # カラム名とプレースホルダーを準備
                columns = ', '.join(row.index)
                placeholders = ', '.join(['?' for _ in row])
                
                # INSERT OR REPLACE文を実行
                sql = f"""
                    INSERT OR REPLACE INTO scraped_data ({columns})
                    VALUES ({placeholders})
                """
                print(f"Executing SQL: {sql}")  # デバッグ用
                self.conn.execute(sql, values)
        print("Data saved successfully")  # デバッグ用

    def get_data(self):
        """データを取得"""
        try:
            # テーブルの存在を確認
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scraped_data'")
            if not cursor.fetchone():
                return pd.DataFrame()  # テーブルが存在しない場合は空のDataFrameを返す

            # カラム名を取得
            cursor.execute("PRAGMA table_info(scraped_data)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if not columns:
                return pd.DataFrame()  # カラムが存在しない場合は空のDataFrameを返す

            # カラム名を指定してデータを取得
            columns_str = ', '.join(columns)
            query = f"SELECT {columns_str} FROM scraped_data ORDER BY データ取得日 DESC"
            return pd.read_sql(query, self.conn)
        except Exception as e:
            print(f"データ取得エラー: {str(e)}")
            return pd.DataFrame()  # エラーが発生した場合は空のDataFrameを返す

    def close(self):
        self.conn.close() 