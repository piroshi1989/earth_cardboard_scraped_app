import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
from config import QUANTITIES

class Scraper:
    def __init__(self):
        self.base_url = "https://www.notosiki.co.jp/item/detail"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_product_data(self, product_code):
        """商品コードから商品データを取得"""
        url = f"{self.base_url}?num={product_code}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 商品データの取得
            data = {
                'データ取得日': datetime.now(),
                'url': url,
                '種類': self._get_text(soup, '種類'),
                '長さ_内寸': self._get_numeric(soup, '長さ (内寸)'),
                '幅_内寸': self._get_numeric(soup, '幅 (内寸)'),
                '深さ_内寸': self._get_numeric(soup, '深さ (内寸)'),
                '外形_三辺合計': self._get_numeric(soup, '外形 三辺合計'),
                '色': self._get_text(soup, '色'),
                '印刷': self._get_text(soup, '印刷'),
                '形式': self._get_text(soup, '形式'),
                '厚み': self._get_numeric(soup, '厚み'),
                '材質': self._get_text(soup, '材質'),
            }

            # 枚数データの取得
            for size in QUANTITIES:
                data[f'枚数_{size}'] = self._get_numeric(soup, f'{size}')

            return data
        except Exception as e:
            print(f"エラー: {product_code} - {str(e)}")
            return None

    def _get_text(self, soup, label):
        """テキストデータを取得"""
        try:
            if label == '種類':
                # og:titleから種類を取得
                meta = soup.find('meta', property='og:title')
                if meta:
                    title = meta.get('content', '').strip()
                    # 「|」の前の部分だけを取得
                    return title.split('|')[0].strip()
                return None
            elif label == '色':
                # itemクラスの「色・印刷：」の直後のIvariety-color-selectedクラスから色を取得
                color_label = soup.find('span', class_='item', string='色・印刷：')
                if color_label:
                    color_element = color_label.find_next('span', class_='Ivariety-color-selected')
                    if color_element:
                        return color_element.text.strip()
                return None
            elif label == '印刷':
                # itemクラスの「ロゴ印刷：」の直後のIvariety-color-selectedクラスから印刷情報を取得
                print_label = soup.find('span', class_='item', string='ロゴ印刷：')
                if print_label:
                    print_element = print_label.find_next('span', class_='Ivariety-color-selected')
                    if print_element:
                        return print_element.text.strip()
                return None
            elif label == '形式':
                # item_spec_spクラスのth要素で「形 式」を含む行の次のtd要素から形式を取得
                print("形式の取得を開始")  # デバッグ用
                form_label = soup.find('th', class_='item_spec_sp', string=lambda text: text and '形 式' in text)
                if form_label:
                    print(f"形式のラベルが見つかりました: {form_label}")  # デバッグ用
                    form_element = form_label.find_next('td', class_='item_spec_sp item_spec_sp_col2')
                    if form_element:
                        print(f"形式の要素が見つかりました: {form_element}")  # デバッグ用
                        return form_element.text.strip()
                print("形式が見つかりませんでした")  # デバッグ用
                return None
            else:
                element = soup.find('th', string=label)
                if element:
                    return element.find_next('td').text.strip()
                return None
        except Exception as e:
            print(f"エラーが発生しました: {str(e)}")  # デバッグ用
            return None

    def _get_numeric(self, soup, label):
        """数値データを取得"""
        try:
            if label in ['長さ (内寸)', '幅 (内寸)', '深さ (内寸)', '外形 三辺合計']:
                # detail_itemspecクラスから寸法を取得
                detail_spec = soup.find('div', class_='detail_itemspec')
                if detail_spec:
                    text = detail_spec.get_text()
                    if '内寸' in text:
                        # 内寸の部分を抽出
                        inner_size = text.split('内寸')[1].split('mm')[0].strip()
                        # 数値を抽出
                        if label == '長さ (内寸)':
                            return float(inner_size.split('×')[0].replace('長さ', '').strip())
                        elif label == '幅 (内寸)':
                            return float(inner_size.split('×')[1].replace('幅', '').strip())
                        elif label == '深さ (内寸)':
                            return float(inner_size.split('×')[2].replace('深さ', '').strip())
                    if '3辺合計' in text:
                        # 3辺合計の部分を抽出
                        total_size = text.split('3辺合計')[1].split('cm')[0].strip()
                        return float(total_size)
            else:
                element = soup.find('th', string=label)
                if element:
                    value = element.find_next('td').text.strip()
                    return float(value) if value else None
            return None
        except:
            return None

    def scrape_products(self, product_codes):
        """複数の商品データを取得"""
        all_data = []
        for code in product_codes:
            data = self.get_product_data(code)
            if data:
                all_data.append(data)
            time.sleep(1)  # サーバーへの負荷を軽減
        return pd.DataFrame(all_data)

if __name__ == "__main__":
    # テスト用
    scraper = Scraper()
    product_codes = ['A4-60', 'K-50']  # 取得したい商品コードのリスト
    df = scraper.scrape_products(product_codes)
    print(df) 