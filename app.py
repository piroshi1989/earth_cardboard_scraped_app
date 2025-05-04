import streamlit as st

# Streamlitの設定
st.set_page_config(
    page_title="アースワンスクレイピングアプリ",
    page_icon="📦",
    layout="wide"
)
import pandas as pd
from scraper import Scraper
from database import Database
import pandas as pd
from config import SIZES, QUANTITIES
import logging
import os
from datetime import datetime, timezone
import time
import pytz
from io import StringIO

# JSTタイムゾーンの設定
jst = pytz.timezone('Asia/Tokyo')

# ログをキャプチャするためのストリーム
log_stream = StringIO()

# ログのフォーマッターをカスタマイズ
class JSTFormatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.astimezone(jst)
    
    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%Y-%m-%d %H:%M:%S %Z')

# ログの設定
log_formatter = JSTFormatter('%(asctime)s - %(levelname)s - %(message)s')

# ファイルハンドラ
file_handler = logging.FileHandler(f'data/logs/{datetime.now().strftime("%Y%m%d")}.log', mode='a', encoding='utf-8')
file_handler.setFormatter(log_formatter)

# ストリームハンドラ（Streamlit用）
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setFormatter(log_formatter)

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# タイトル
st.title("アースワンスクレイピングアプリ")

# ログ表示用のコンポーネント
st.sidebar.header("ログ")
log_container = st.sidebar.empty()

# ログを更新する関数
def update_log_display():
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_container.text_area("ログ", value=log_stream.getvalue(), height=300, key=f"log_display_{current_time}")

# スクレイパーの初期化
@st.cache_resource(ttl=3600)  # 1時間でキャッシュを無効化
def init_scraper():
    scraper = Scraper()
    return scraper

# スクレイパーの取得（スレッドセーフな方法）
def get_scraper():
    if 'scraper' not in st.session_state:
        st.session_state.scraper = init_scraper()
    return st.session_state.scraper

# スクレイパーの使用
scraper = get_scraper()

# データベースの初期化
db = Database()

# メインコンテンツの前に追加
st.header("データベースの内容")

# データベースリセットボタン
if st.button("データベースをリセット"):
    try:
        db_path = 'data/database.db'
        if os.path.exists(db_path):
            os.remove(db_path)
            st.success("データベースをリセットしました。ページをリロードしてください。")
            st.experimental_rerun()
        else:
            st.warning("データベースファイルが存在しません。")
    except Exception as e:
        st.error(f"データベースのリセット中にエラーが発生しました: {str(e)}")
        logging.error(f"データベースのリセット中にエラーが発生: {str(e)}")

# 商品IDテーブルの表示
# productsテーブルの表示
st.subheader("商品テーブル")
products = db.get_all_product_ids()
if products:
    # SQLite3のRowオブジェクトを辞書のリストに変換
    products_list = [dict(row) for row in products]
    products_df = pd.DataFrame(products_list)
    
    # カラムの順序を指定（必要に応じて調整）
    columns_order = [
        'id', 'product_id', 'name', 'size', 'url',
        'created_at', 'updated_at',
        'outer_dimension_sum',
        'inner_length', 'inner_width', 'inner_depth',
        'outer_length', 'outer_width', 'outer_depth',
        'manufacturing_method', 'processing_location',
        'color', 'box_type', 'thickness', 'material',
        'standard_width'
    ]
    # 価格カラムを追加
    price_columns = [f'price_{q}' for q in QUANTITIES]
    columns_order.extend(price_columns)
    
    # 存在するカラムのみを選択
    available_columns = [col for col in columns_order if col in products_df.columns]
    products_df = products_df[available_columns]
    
    # 日本語のカラム名マッピング
    column_names = {
        'id': 'ID',
        'product_id': '商品ID',
        'name': '商品名',
        'size': 'サイズ',
        'url': 'URL',
        'created_at': '作成日時',
        'updated_at': '更新日時',
        'outer_dimension_sum': '外形三辺合計',
        'inner_length': '内寸_長さ',
        'inner_width': '内寸_幅',
        'inner_depth': '内寸_深さ',
        'outer_length': '外寸_長さ',
        'outer_width': '外寸_幅',
        'outer_depth': '外寸_深さ',
        'manufacturing_method': '製法',
        'processing_location': '加工先',
        'color': '色',
        'box_type': '形式',
        'thickness': '厚み',
        'material': '材質',
        'standard_width': '規格幅'
    }
    # 価格カラムの日本語名を追加
    for q in QUANTITIES:
        column_names[f'price_{q}'] = f'{q}枚の価格'
    
    # カラム名を日本語に変更
    products_df = products_df.rename(columns=column_names)
    
    # DataFrameでの時刻表示をフォーマット
    def format_datetime(dt):
        if pd.isna(dt):
            return ''
        return pd.to_datetime(dt).tz_localize('UTC').tz_convert('Asia/Tokyo').strftime('%Y-%m-%d %H:%M:%S')

    # DataFrameの日時カラムにフォーマットを適用
    if 'created_at' in products_df.columns:
        products_df['作成日時'] = products_df['created_at'].apply(format_datetime)
    if 'updated_at' in products_df.columns:
        products_df['更新日時'] = products_df['updated_at'].apply(format_datetime)
    
    # サイズごとの絞り込み機能
    st.write("サイズごとの絞り込み")
    selected_size = st.selectbox(
        "絞り込みたいサイズを選択",
        options=[""] + sorted(products_df['サイズ'].unique().tolist()),
        index=0
    )
    
    if st.button("サイズで絞り込む"):
        if selected_size:
            filtered_df = products_df[products_df['サイズ'] == selected_size]
            st.dataframe(filtered_df)
            st.write(f"{selected_size}サイズの商品数: {len(filtered_df)}件")
        else:
            # サイズが空の場合は全サイズ表示
            st.dataframe(products_df)
            st.write(f"全サイズの商品数: {len(products_df)}件")
    else:
        # デフォルトで全サイズ表示
        st.dataframe(products_df)
else:
    st.info("商品テーブルは空です")

# ログを更新
update_log_display()

# サイズ選択
st.header("①サイズ選択")
selected_size = st.selectbox(
    "取得したいサイズを選択してください",
    SIZES,
    index=0
)

if not selected_size:
    st.warning("サイズを選択してください。")
else:
    if st.button("①選択したサイズの商品ID、商品名、URLを取得"):
        with st.spinner("商品IDを取得中..."):
            try:
                product_ids = scraper.get_product_ids([selected_size])
                if product_ids:
                    st.success(f"{len(product_ids)}件の商品IDを取得しました。")
                    
                    # 商品IDの表示
                    st.subheader("取得した商品ID")
                    df = pd.DataFrame([
                        {"商品ID": p['id'], "商品名": p['name'], "サイズ": selected_size}
                        for p in product_ids
                    ])
                    st.dataframe(df)
                else:
                    st.error("商品IDの取得に失敗しました。")
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                logging.error(f"商品ID取得中にエラーが発生: {str(e)}", exc_info=True)
            finally:
                update_log_display()

    # 商品詳細取得
    st.header("②-1 商品詳細取得(複数商品)")
    # データベースから選択したサイズの商品IDを取得
    stored_products = db.get_product_ids(selected_size)
    if stored_products:
        if st.button("②選択したサイズの商品詳細を一括取得"):
            with st.spinner("商品詳細を取得中..."):
                try:
                    # 進捗バーの設定
                    progress_bar = st.progress(0)
                    total_products = len(stored_products)
                    status_text = st.empty()
                    
                    # 失敗した商品IDを記録するリスト
                    failed_products = []
                    
                    # 商品詳細の取得
                    all_data = []
                    for i, product in enumerate(stored_products, 1):
                        try:
                            # 進捗状況の更新
                            progress = i / total_products
                            progress_bar.progress(progress)
                            status_text.text(f"処理中: {i}/{total_products} 件目 ({(progress*100):.1f}%)")
                            
                            # 商品IDの存在確認
                            if not isinstance(product, dict):
                                logging.error(f"不正な商品データ形式: {product}")
                                failed_products.append({"id": str(product), "reason": "不正な商品データ形式"})
                                continue
                                
                            product_id = product.get('product_id')
                            if not product_id:
                                logging.error(f"商品IDが存在しません: {product}")
                                failed_products.append({"id": str(product), "reason": "商品IDが存在しません"})
                                continue
                                
                            # 商品IDの形式確認
                            if not isinstance(product_id, (str, int)):
                                logging.error(f"不正な商品ID形式: {product_id}")
                                failed_products.append({"id": str(product_id), "reason": "不正な商品ID形式"})
                                continue
                                
                            # 商品IDを文字列に変換
                            product_id = str(product_id)
                            
                            # 商品詳細の取得
                            data = scraper.get_product_details([product_id])
                            if data:
                                all_data.append(data)
                                logging.info(f"商品 {i}/{len(stored_products)} の詳細を取得しました: {product_id}")
                            else:
                                logging.warning(f"商品 {i}/{len(stored_products)} の詳細を取得できませんでした: {product_id}")
                                failed_products.append({"id": product_id, "reason": "商品詳細の取得に失敗"})
                                
                        except Exception as e:
                            logging.error(f"商品 {i}/{len(stored_products)} の処理中にエラー: {str(e)}")
                            failed_products.append({"id": str(product.get('product_id', '不明')), "reason": str(e)})
                            continue
                    
                    if all_data:
                        st.success(f"{len(all_data)}件の商品詳細を取得しました。")
                        
                        # 商品詳細の表示
                        st.subheader("取得した商品詳細")
                        df = pd.DataFrame(all_data)
                        st.dataframe(df)
                        
                        # 失敗した商品の表示
                        if failed_products:
                            st.warning(f"{len(failed_products)}件の商品の取得に失敗しました。")
                            st.subheader("失敗した商品一覧")
                            failed_df = pd.DataFrame(failed_products)
                            st.dataframe(failed_df)
                    else:
                        st.error("商品詳細の取得に失敗しました。")
                        if failed_products:
                            st.subheader("失敗した商品一覧")
                            failed_df = pd.DataFrame(failed_products)
                            st.dataframe(failed_df)
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
                    logging.error(f"商品詳細取得中にエラーが発生: {str(e)}", exc_info=True)
                finally:
                    update_log_display()
                    progress_bar.empty()
                    status_text.empty()
    else:
        st.warning(f"{selected_size}のサイズの商品IDがデータベースに存在しません。")

    # 商品詳細取得（単一商品）
    st.header("②-2 商品詳細取得（単一商品）")

    # データベースから選択したサイズの商品IDを取得
    stored_products = db.get_product_ids(selected_size)
    if stored_products:
        # 商品IDと商品名のリストを作成
        product_options = [f"{p['product_id']} - {p['name']}" for p in stored_products]
        
        # 商品IDの選択
        selected_product = st.selectbox(
            "詳細を取得したい商品を選択してください",
            options=product_options,
            index=0
        )
        
        # 選択された商品IDを抽出
        selected_product_id = selected_product.split(" - ")[0]
        
        if st.button("選択した商品の詳細を取得"):
            with st.spinner("商品詳細を取得中..."):
                try:
                    # 選択した商品IDの詳細を取得
                    data = scraper.get_product_details([selected_product_id])
                    if data:
                        st.success("商品詳細を取得しました。")
                        
                        # 商品詳細の表示
                        st.subheader("商品詳細")
                        detail_df = pd.DataFrame([data])
                        
                        # 日本語のカラム名マッピング
                        column_names = {
                            'product_id': '商品ID',
                            'name': '商品名',
                            'size': 'サイズ',
                            'url': 'URL',
                            'outer_dimension_sum': '外形三辺合計',
                            'inner_length': '内寸_長さ',
                            'inner_width': '内寸_幅',
                            'inner_depth': '内寸_深さ',
                            'outer_length': '外寸_長さ',
                            'outer_width': '外寸_幅',
                            'outer_depth': '外寸_深さ',
                            'manufacturing_method': '製法',
                            'processing_location': '加工先',
                            'color': '色',
                            'box_type': '形式',
                            'thickness': '厚み',
                            'material': '材質',
                            'standard_width': '規格幅'
                        }
                        # 価格カラムの日本語名を追加
                        for q in QUANTITIES:
                            column_names[f'price_{q}'] = f'{q}枚の価格'
                        
                        # カラム名を日本語に変更
                        detail_df = detail_df.rename(columns=column_names)
                        
                        st.dataframe(detail_df)
                        
                    else:
                        st.error("商品詳細の取得に失敗しました。")
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
                    logging.error(f"商品詳細取得中にエラーが発生: {str(e)}", exc_info=True)
                finally:
                    update_log_display()
    else:
        st.warning(f"{selected_size}のサイズの商品がデータベースに存在しません。")

if __name__ == "__main__":
    pass