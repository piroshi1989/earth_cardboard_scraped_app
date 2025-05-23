import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import os
import stat
import logging
import threading
from config import QUANTITIES
import pytz

# JSTタイムゾーンの設定
jst = pytz.timezone('Asia/Tokyo')

# ログディレクトリの作成
log_dir = 'data/logs'
os.makedirs(log_dir, exist_ok=True)

# ログの設定
file_handler = logging.FileHandler(f'{log_dir}/{datetime.now().strftime("%Y%m%d")}.log', mode='a', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

class JSTFormatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.astimezone(jst)
    
    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%Y-%m-%d %H:%M:%S %Z')

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.db_path = 'data/database.db'
        self._ensure_directory_exists()
        self._thread_local = threading.local()
        self._create_tables()
    
    def _get_connection(self):
        if not hasattr(self._thread_local, 'conn'):
            self._thread_local.conn = sqlite3.connect(self.db_path)
            self._thread_local.conn.row_factory = sqlite3.Row
        return self._thread_local.conn
    
    def _ensure_directory_exists(self):
        """データベースディレクトリが存在することを確認"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # ディレクトリのパーミッションを確認
        if not os.access(os.path.dirname(self.db_path), os.R_OK | os.W_OK | os.X_OK):
            logging.error(f"ディレクトリのパーミッションが不適切です: {os.path.dirname(self.db_path)}")
            raise PermissionError("ディレクトリのパーミッションが不適切です")

    def _create_tables(self):
        """必要なテーブルを作成"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
        
            # 価格カラムの定義を生成
            price_columns = []
            for q in QUANTITIES:
                price_columns.append(f'price_{q} INTEGER')
            price_columns_str = ',\n'.join(price_columns)
            
            # productsテーブルの作成
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT UNIQUE,
                    name TEXT,
                    size TEXT,
                    url TEXT,
                    outer_dimension_sum REAL,
                    inner_length REAL,
                    inner_width REAL,
                    inner_depth REAL,
                    manufacturing_method TEXT,
                    outer_length REAL,
                    outer_width REAL,
                    outer_depth REAL,
                    processing_location TEXT,
                    color TEXT,
                    box_type TEXT,
                    thickness TEXT,
                    material TEXT,
                    standard_width REAL,
                    {price_columns_str},
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logging.info("テーブルの作成が完了しました")
            
        except sqlite3.Error as e:
            logging.error(f"テーブル作成中にエラーが発生: {str(e)}")
            raise
        finally:
            cursor.close()

    def save_product(self, product_data):
        """商品情報を保存"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 既存の商品をチェック
            cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_data['商品コード'],))
            existing = cursor.fetchone()
            
            # カラム名と値のマッピング
            column_mapping = {
                'product_id': '商品コード',
                'name': '商品名',
                'size': 'サイズ',
                'url': 'url',
                'outer_dimension_sum': '外形_三辺合計',
                'inner_length': '長さ_内寸',
                'inner_width': '幅_内寸',
                'inner_depth': '深さ_内寸',
                'outer_length': '長さ_外寸',
                'outer_width': '幅_外寸',
                'outer_depth': '深さ_外寸',
                'manufacturing_method': '製法',
                'processing_location': '加工先',
                'color': '色',
                'box_type': '形式',
                'thickness': '厚み',
                'material': '材質',
                'standard_width': '規格幅'
            }
            
            # 価格データの処理
            price_data = {}
            for key, value in product_data.items():
                if '枚の価格' in key:
                    quantity = int(key.replace('枚の価格', ''))
                    price_data[f'price_{quantity}'] = value
            
            if existing:
                # 価格データの変更をチェック
                price_changed = False
                for col, val in price_data.items():
                    if existing[col] != val:
                        price_changed = True
                        break
                
                # 空でない値だけを更新対象にする
                columns = []
                values = []
                for col, key in column_mapping.items():
                    val = product_data.get(key)
                    if val is not None and str(val).strip() != "":
                        columns.append(f"{col} = ?")
                        values.append(val)
                
                # 価格データの更新
                for col, val in price_data.items():
                    columns.append(f"{col} = ?")
                    values.append(val)
                
                # updated_atは必ず更新
                columns.append("updated_at = datetime('now')")
                sql = f'''
                    UPDATE products SET
                    {", ".join(columns)}
                    WHERE product_id = ?
                '''
                values.append(product_data['商品コード'])
                cursor.execute(sql, values)
                
                # 価格データが変更された場合のみログを出力
                if price_changed:
                    logging.info(f"商品情報を更新しました（価格変更）: {product_data['商品コード']}")
            else:
                # 挿入時は従来通り
                columns = list(column_mapping.keys()) + list(price_data.keys()) + ['created_at', 'updated_at']
                placeholders = ['?'] * (len(column_mapping) + len(price_data)) + ["datetime('now')", "datetime('now')"]
                sql = f'''
                    INSERT INTO products (
                    {", ".join(columns)}
                    ) VALUES (
                    {", ".join(placeholders)}
                    )
                '''
                values = [product_data.get(column_mapping[col]) for col in column_mapping.keys()]
                values.extend(price_data.values())
                cursor.execute(sql, values)
                logging.info(f"商品情報を新規保存しました: {product_data['商品コード']}")
            
            conn.commit()
            
        except sqlite3.Error as e:
            logging.error(f"商品情報の保存中にエラーが発生: {str(e)}")
            raise
        finally:
            cursor.close()

    def save_product_ids(self, product_ids, size):
        """商品IDと商品名を保存"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # product_idsの形式をログ出力
            logging.info(f"保存するproduct_ids: {product_ids}")
            logging.info(f"サイズ: {size}")
            
            for product in product_ids:
                try:
                    # product_idとnameが存在することを確認
                    if not isinstance(product, dict) or 'id' not in product or 'name' not in product:
                        logging.warning(f"無効な商品データ形式: {product}")
                        continue
                    
                    # 既存のデータを取得（商品名を更新するため）
                    cursor.execute('SELECT * FROM products WHERE product_id = ?', (str(product['id']),))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 既存の商品名がある場合は更新
                        cursor.execute('''
                            UPDATE products 
                            SET name = ?, size = ?, url = ?, 
                            updated_at = datetime('now', '+9 hours')
                            WHERE product_id = ?
                        ''', (str(product['name']), str(size), str(product['url']), str(product['id'])))
                        logging.info(f"商品を更新: ID={product['id']}, 名前={product['name']}, サイズ={size}")
                    else:
                        # 新規挿入
                        cursor.execute('''
                            INSERT INTO products 
                            (product_id, name, size, url, created_at, updated_at)
                            VALUES 
                            (?, ?, ?, ?, datetime('now', '+9 hours'), datetime('now', '+9 hours'))
                        ''', (str(product['id']), str(product['name']), str(size), str(product['url'])))
                        logging.info(f"商品を新規追加: ID={product['id']}, 名前={product['name']}, サイズ={size}")
                    
                except Exception as e:
                    logging.error(f"個別の商品保存中にエラー: {str(e)}, 商品データ: {product}")
                    continue
            
            conn.commit()
            logging.info(f"商品ID {len(product_ids)} 件を保存しました")
            
        except Exception as e:
            logging.error(f"商品IDの保存中にエラーが発生: {str(e)}")
            logging.error(f"エラーの詳細:", exc_info=True)
            raise
        finally:
            cursor.close()

    def get_products_by_size(self, size=None):
        """指定されたサイズの商品を取得（size=Noneの場合は全商品）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if size is not None:
                cursor.execute('SELECT * FROM products WHERE size = ?', (size,))
            else:
                cursor.execute('SELECT * FROM products')
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"商品情報の取得中にエラーが発生: {str(e)}")
            return []
        finally:
            cursor.close()

    def get_url_by_product_id(self, product_id):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if product_id is not None:
                cursor.execute('SELECT url FROM products WHERE product_id = ?', (product_id,))
            else:
                cursor.execute('SELECT url FROM products')
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"商品URLの取得中にエラーが発生: {str(e)}")
            return []
        finally:
            cursor.close()


    def close(self):
        """データベース接続を閉じる"""
        if hasattr(self._thread_local, 'conn'):
            self._thread_local.conn.close()
            delattr(self._thread_local, 'conn')
            logging.info("データベース接続を閉じました")
    
    def get_all_product_ids(self):
        """商品IDテーブルの全データを取得"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products")
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"商品情報の取得中にエラーが発生: {str(e)}")
            return []
        finally:
            cursor.close()

    def get_all_product_details(self):
        """商品詳細テーブルの全データを取得"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products")
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"商品情報の取得中にエラーが発生: {str(e)}")
            return []
        finally:
            cursor.close()

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
        """商品データを保存"""
        cursor = self._get_connection().cursor()
        
        for _, row in df.iterrows():
            # カラム名と値を準備
            columns = ', '.join(row.index)
            placeholders = ', '.join(['?' for _ in row])
            values = tuple(row)
            
            cursor.execute(f'''
                INSERT OR REPLACE INTO product_data ({columns})
                VALUES ({placeholders})
            ''', values)
        
        self._get_connection().commit()
        cursor.close()

    def get_data(self):
        """データを取得"""
        try:
            # テーブルの存在を確認
            cursor = self._get_connection().cursor()
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
            return pd.read_sql(query, self._get_connection())
        except Exception as e:
            print(f"データ取得エラー: {str(e)}")
            return pd.DataFrame()  # エラーが発生した場合は空のDataFrameを返す

    def get_product_ids(self, size=None):
        """保存されている商品IDを取得"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if size is not None:
                cursor.execute(
                    "SELECT product_id, name, size, created_at FROM products WHERE size = ? ORDER BY created_at DESC",
                    (str(size),)
                )
                logging.info(f"サイズ {size} の商品IDを取得しています")
            else:
                cursor.execute("SELECT product_id, name, size, created_at FROM products ORDER BY created_at DESC")
                logging.info("全商品IDを取得しています")
            
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            logging.info(f"取得した商品ID数: {len(result)}")
            for row in result[:5]:  # 最初の5件だけログ出力
                logging.info(f"取得した商品: ID={row['product_id']}, 名前={row.get('name', 'なし')}, サイズ={row.get('size', 'なし')}")
            return result
            
        except sqlite3.Error as e:
            logging.error(f"商品ID取得エラー: {str(e)}")
            return []
        finally:
            cursor.close() 

    def recreate_tables(self):
        """テーブルを再作成"""
        try:
            self.drop_tables()
            self._create_tables()
            logging.info("テーブルの再作成が完了しました")
        except Exception as e:
            logging.error(f"テーブルの再作成中にエラーが発生: {str(e)}")
            raise

    def drop_tables(self):
        """既存のテーブルを削除"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # テーブルの存在確認と削除
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='products'
            """)
            
            tables = cursor.fetchall()
            for table in tables:
                table_name = table[0]
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                logging.info(f"テーブル {table_name} を削除しました")
            
            conn.commit()
            logging.info("全てのテーブルを削除しました")
            
        except sqlite3.Error as e:
            logging.error(f"テーブル削除中にSQLiteエラー: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"テーブル削除中に予期せぬエラー: {str(e)}")
            raise
        finally:
            try:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            except Exception as e:
                logging.error(f"接続のクローズ中にエラー: {str(e)}")


    def get_size_type(self, product_id):
        """商品IDからサイズタイプを取得"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT size FROM products WHERE product_id = ?", (product_id,))
            return cursor.fetchone()[0]
        except Exception as e:
            logging.error(f"サイズタイプの取得中にエラーが発生: {str(e)}")
            return None
        finally:
            cursor.close()