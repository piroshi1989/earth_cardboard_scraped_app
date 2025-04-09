import streamlit as st
from scraper import Scraper
from database import Database
import pandas as pd
from config import PRODUCT_CODES

def main():
    st.title("ダンボールワン商品データスクレイピング")
    
    # 商品コードの入力
    product_codes = st.text_area(
        "商品コードを入力（1行に1つ）",
        "\n".join(PRODUCT_CODES)
    ).split('\n')
    
    if st.button("データをスクレイピング"):
        with st.spinner('データを取得中...'):
            # スクレイピング
            scraper = Scraper()
            df = scraper.scrape_products(product_codes)
            
            if df is not None and not df.empty:
                # データベースに保存
                db = Database()
                db.save_data(df)
                db.close()
                st.success("データを保存しました！")
            else:
                st.error("データの取得に失敗しました。")

    # 保存済みデータの表示
    db = Database()
    data = db.get_data()
    db.close()
    
    if not data.empty:
        st.dataframe(data)
        
        # CSVダウンロードボタン
        csv = data.to_csv(index=False)
        st.download_button(
            label="CSVとしてダウンロード",
            data=csv,
            file_name="scraped_data.csv",
            mime="text/csv"
        )
    else:
        st.info("データがありません。スクレイピングを実行してください。")

if __name__ == "__main__":
    main() 