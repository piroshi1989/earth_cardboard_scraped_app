import streamlit as st

# Streamlitの設定
st.set_page_config(
    page_title="段ボールスクレイピングアプリ",
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
from datetime import datetime
import time
import pytz

# JSTタイムゾーンの設定
jst = pytz.timezone('Asia/Tokyo')

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
file_handler = logging.FileHandler('data/logs/app.log', mode='a', encoding='utf-8')
file_handler.setFormatter(log_formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler]
)
# タイトル
st.title("アースワンスクレイピングアプリ")

# スクレイパーの初期化
@st.cache_resource
def init_scraper():
    return Scraper()

scraper = init_scraper()

# データベースの初期化
db = Database()

# メインコンテンツの前に追加
st.header("データベースの内容")

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
    
    st.dataframe(products_df)
else:
    st.info("商品テーブルは空です")

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'data/logs/{datetime.now().strftime("%Y%m%d")}.log', mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
    
# サイズ選択
st.header("サイズ選択")
selected_size = st.selectbox(
    "取得したいサイズを選択してください",
    SIZES,
    index=0
)

if not selected_size:
    st.warning("サイズを選択してください。")
else:
    if st.button("選択したサイズの商品IDを取得"):
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
                    
                    # 商品IDを選択して詳細を取得する機能
                    st.subheader("特定の商品IDの詳細を取得")
                    selected_product_id = st.selectbox(
                        "詳細を取得したい商品IDを選択してください",
                        options=df['商品ID'].tolist(),
                        index=0
                    )
                    
                    if st.button("選択した商品の詳細を取得"):
                        with st.spinner("商品詳細を取得中..."):
                            try:
                                data = scraper.get_product_details([selected_product_id])
                                if data:
                                    st.success("商品詳細を取得しました。")
                                    st.subheader("商品詳細")
                                    detail_df = pd.DataFrame([data])
                                    st.dataframe(detail_df)
                                    
                                    # CSVダウンロード
                                    csv = detail_df.to_csv(index=False).encode('utf-8')
                                    st.download_button(
                                        label="CSVダウンロード",
                                        data=csv,
                                        file_name=f"product_detail_{selected_product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                else:
                                    st.error("商品詳細の取得に失敗しました。")
                            except Exception as e:
                                st.error(f"エラーが発生しました: {str(e)}")
                                logging.error(f"商品詳細取得中にエラーが発生: {str(e)}", exc_info=True)
                    
                    # サイズごとの絞り込みボタン
                    if st.button(f"{selected_size}の商品を絞り込む"):
                        filtered_df = df[df['サイズ'] == selected_size]
                        st.subheader(f"{selected_size}の商品")
                        st.dataframe(filtered_df)
                    
                    # CSVダウンロード
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="CSVダウンロード",
                        data=csv,
                        file_name=f"product_ids_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("商品IDの取得に失敗しました。")
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                logging.error(f"商品ID取得中にエラーが発生: {str(e)}", exc_info=True)

    # 商品詳細取得
    st.header("商品詳細取得")
    if st.button("選択したサイズの商品詳細を一括取得"):
        with st.spinner("商品詳細を取得中..."):
            try:
                # 選択したサイズの商品IDを取得
                product_ids = scraper.get_product_ids([selected_size])
                if not product_ids:
                    st.warning("商品IDが見つかりません。")
                    st.stop()
                
                # 進捗バーの設定
                progress_bar = st.progress(0)
                total_products = len(product_ids)
                
                # 商品詳細の取得
                all_data = []
                for i, product in enumerate(product_ids, 1):
                    try:
                        product_id = product['id']
                        data = scraper.get_product_details([product_id])
                        if data:
                            all_data.append(data)
                        progress_bar.progress(i / total_products)
                    except Exception as e:
                        logging.error(f"商品 {product.get('id', 'unknown')} の詳細取得中にエラーが発生: {str(e)}", exc_info=True)
                        continue
                
                if all_data:
                    st.success(f"{len(all_data)}件の商品詳細を取得しました。")
                    
                    # 商品詳細の表示
                    st.subheader("取得した商品詳細")
                    df = pd.DataFrame(all_data)
                    st.dataframe(df)
            
                    # CSVダウンロード
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="CSVダウンロード",
                        data=csv,
                        file_name=f"product_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("商品詳細の取得に失敗しました。")
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                logging.error(f"商品詳細取得中にエラーが発生: {str(e)}", exc_info=True)

if __name__ == "__main__":
    pass