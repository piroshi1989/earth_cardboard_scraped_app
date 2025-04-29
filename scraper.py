import time
import random
import logging
import urllib3
import re
from bs4 import BeautifulSoup
import requests
from database import Database
from config import SIZES, BASE_URL, CATEGORY_BASE_URL, HEADERS, QUANTITIES
from proxy_manager import ProxyManager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Scraper:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.db = Database()
        self.base_url = BASE_URL
        self.category_base_url = CATEGORY_BASE_URL
        self.session = None
        self._init_session()

    def _init_session(self):
        """セッションの初期化"""
        try:
            # プロキシのテスト
            working_proxies = self.proxy_manager.get_working_proxies()
            if not working_proxies:
                raise Exception("動作するプロキシが見つかりません")

            # 最適なプロキシを取得
            best_proxy = self.proxy_manager.get_best_proxy()
            if not best_proxy:
                raise Exception("最適なプロキシが見つかりません")

            logging.info(f"最適なプロキシを使用: {best_proxy}")
            
        except Exception as e:
            logging.error(f"セッションの初期化に失敗: {str(e)}")
            raise

    def make_request(self, url, max_retries=3, unit=None):
        """Splashを使用してリクエストを送信"""
        splash_url = "http://localhost:8050/render.html"
        params = {
            "url": url,
            "wait": 2,  # ページの読み込み待機時間（秒）
            "timeout": 30,
            "proxy": self.proxy_manager.get_best_proxy() if self.proxy_manager.get_best_proxy() else None
        }
        
        # タブ切り替えのためのJavaScriptを追加
        if unit:
            params["lua_source"] = f"""
            function main(splash)
                splash:go(splash.args.url)
                splash:wait(2)
                -- タブをクリック
                splash:runjs("document.getElementById('unit_{unit}').click()")
                splash:wait(2)
                return splash:html()
            end
            """
        
        for attempt in range(max_retries):
            try:
                response = requests.get(splash_url, params=params, headers=HEADERS)
                response.raise_for_status()
                return response
            except Exception as e:
                logging.warning(f"リクエスト失敗 (試行 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 5))
                else:
                    raise

    def _extract_size_from_url(self, url):
        """URLからサイズ情報を抽出"""
        try:
            size_match = re.search(r'/([A-Z]\d+)/', url)
            if size_match:
                return size_match.group(1)
            logging.warning(f"URLからサイズ情報を抽出できませんでした: {url}")
            return None
        except Exception as e:
            logging.error(f"サイズ情報の抽出中にエラー: {str(e)}")
            return None
    
    def get_product_ids(self, size=None):
        """指定されたサイズの商品IDを取得してデータベースに保存"""
        if size is None:
            sizes = SIZES
        else:
            sizes = [size] if isinstance(size, str) else size

        logging.info(f"取得対象のサイズ: {sizes}")

        all_product_ids = []
        for size_type in sizes:
            page = 1
            category_url = f"{self.category_base_url}{size_type}/"
            logging.info(f"処理中のURL: {category_url}")

            product_ids = []
            page = 1
            has_next_page = True

            try:
                while has_next_page:
                    url = f"{category_url}?page={page}"
                    logging.info(f"ページ {page} の処理を開始...")
                    
                    # リクエスト前に待機
                    sleep_time = random.uniform(2, 5)
                    logging.info(f"待機時間: {sleep_time:.2f}秒")
                    time.sleep(sleep_time)
                    
                    # リクエスト実行
                    logging.info("リクエスト送信中...")
                    response = self.make_request(url)
                    
                    if not response:
                        logging.error("リクエストが失敗しました")
                        has_next_page = False
                        break
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 商品ボックスの検索
                    result_box = soup.find('div', id='resultBox')
                    if not result_box:
                        logging.warning(f"ページ {page} で商品が見つかりません")
                        has_next_page = False
                        break
                    
                    product_boxes = result_box.find_all('div', class_='product_box')
                    
                    # 商品情報の取得
                    for box in product_boxes:
                        try:
                            product_name = box.find('h4')
                            product_name = product_name.text.strip() if product_name else ""
                            
                            product_id_element = box.find('li', class_='product_id')
                            if product_id_element:
                                product_id = product_id_element.get('id')
                                if product_id:
                                    product_url = f"{self.base_url}{product_id}.html"
                                    product_ids.append({
                                        'id': product_id,
                                        'name': product_name,
                                        'url': product_url
                                    })
                                    logging.info(f"商品IDを取得: {product_id} - {product_name}")
                        except Exception as e:
                            logging.error(f"商品情報の取得中にエラー: {str(e)}")
                            continue

                    # 商品IDをデータベースに保存
                    if product_ids:
                        self.db.save_product_ids(product_ids, size_type)
                        all_product_ids.extend(product_ids)
                        logging.info(f"サイズ {size_type} の商品ID {len(product_ids)} 件を保存しました")
                    else:
                        logging.warning(f"サイズ {size_type} の商品が見つかりませんでした")
                        has_next_page = False         

                    # 次のページの確認
                    next_page_link = soup.find('li', class_='next_page')
                    if not next_page_link:
                        logging.info("次のページが見つかりません。ページネーション終了")
                        has_next_page = False
                    else:
                        page += 1
                        logging.info(f"次のページに移動します: {page}")
                    
            except Exception as e:
                logging.error(f"サイズ {size_type} の処理中にエラーが発生: {str(e)}")
                continue

        return all_product_ids

    def _get_numeric(self, soup, label):
        """数値データを取得"""
        logging.info(f"数値データの取得を開始: {label}")
        details_box = soup.find('div', id='detailsBox')
        if not details_box:
            logging.warning("detailsBoxが見つかりませんでした")
            return None

        # 「外寸法」や「内寸法」から分割して取得
        if label in ["長さ (外寸)", "幅 (外寸)", "深さ (外寸)"]:
            for dt in details_box.find_all('dt'):
                dt_text = dt.get_text(strip=True)
                if "外寸法" in dt_text:
                    dd = dt.find_next_sibling('dd')
                    if not dd:
                        logging.warning(f"外寸法 のdd要素が見つかりませんでした")
                        return None
                    text = dd.get_text(strip=True)
                    # 例: 276×198×28(深さ) mm
                    m = re.match(r'([\d\.]+)×([\d\.]+)×([\d\.]+)', text)
                    if m:
                        if label == "長さ (外寸)":
                            return float(m.group(1))
                        elif label == "幅 (外寸)":
                            return float(m.group(2))
                        elif label == "深さ (外寸)":
                            return float(m.group(3))
                    else:
                        logging.warning(f"外寸法の数値抽出に失敗: {text}")
                        return None

        # 「内寸法」も同様
        if label in ["長さ (内寸)", "幅 (内寸)", "深さ (内寸)"]:
            for dt in details_box.find_all('dt'):
                dt_text = dt.get_text(strip=True)
                if "内寸法" in dt_text:
                    dd = dt.find_next_sibling('dd')
                    if not dd:
                        logging.warning(f"内寸法 のdd要素が見つかりませんでした")
                        return None
                    text = dd.get_text(strip=True)
                    # 例: 305×220×25(深さ) mm
                    m = re.match(r'([\d\.]+)×([\d\.]+)×([\d\.]+)', text)
                    if m:
                        if label == "長さ (内寸)":
                            return float(m.group(1))
                        elif label == "幅 (内寸)":
                            return float(m.group(2))
                        elif label == "深さ (内寸)":
                            return float(m.group(3))
                    else:
                        logging.warning(f"内寸法の数値抽出に失敗: {text}")
                        return None

        # それ以外は従来通り
        for dt in details_box.find_all('dt'):
            dt_text = dt.get_text(strip=True)
            if label in dt_text:
                dd = dt.find_next_sibling('dd')
                if not dd:
                    logging.warning(f"{label} のdd要素が見つかりませんでした")
                    return None
                a = dd.find('a')
                text = a.get_text(strip=True) if a else dd.get_text(strip=True)
                logging.debug(f"{label} の抽出テキスト: {text}")
                m = re.search(r'([\d\.]+)', text)
                if m:
                    result = float(m.group(1))
                    logging.info(f"{label} の取得結果: {result}")
                    return result
                else:
                    logging.warning(f"{label} の数値抽出に失敗: {text}")
                    return None
        logging.warning(f"{label} のdt要素が見つかりませんでした")
        return None

    def _get_text(self, soup, label):
        """テキストデータを取得"""
        logging.info(f"テキストデータの取得を開始: {label}")
        
        details_box = soup.find('div', id='detailsBox')
        if not details_box:
            logging.warning("detailsBoxが見つかりませんでした")
            return None

        # dt要素の内容をデバッグ出力
        for dt in details_box.find_all('dt'):
            dt_text = dt.get_text(strip=True)
            logging.info(f"dt要素の内容: {dt_text}")
            if label in dt_text:
                dd = dt.find_next_sibling('dd')
                if dd:
                    # 材質の場合は特別な処理
                    if label == '紙質（強度）':
                        quality_span = dd.find('span', id='more_quality')
                        if quality_span:
                            text = quality_span.get_text(strip=True)
                            logging.info(f"{label} の取得結果: {text}")
                            return text
                        else:
                            logging.warning(f"{label} のspan要素が見つかりませんでした")
                            return None
                    else:
                        text = dd.get_text(strip=True)
                        logging.info(f"{label} の取得結果: {text}")
                        return text
                else:
                    logging.warning(f"{label} のdd要素が見つかりませんでした")
                    return None
        
        logging.warning(f"{label} の要素が見つかりませんでした")
        return None

    def get_product_details(self, product_ids=None):
        """商品の詳細情報を取得してデータベースに保存"""
        if product_ids is None:
            product_ids = self.db.get_all_product_ids()
        
        logging.info(f"取得対象の商品数: {len(product_ids)}")
        
        for product_id in product_ids:
            try:
                url = f"{self.base_url}{product_id}.html"
                logging.info(f"商品詳細の取得を開始: {url}")
                
                # 1枚単位の価格を取得
                response = self.make_request(url, unit=1)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 商品データの取得
                data = {
                    '商品コード': product_id,
                    '商品名': self._get_text(soup, '商品名'),
                    'サイズ': self.db.get_size_type(product_id),
                    'url': url,
                    '外形_三辺合計': self._get_numeric(soup, '3辺外寸合計'),
                    '長さ_内寸': self._get_numeric(soup, '長さ (内寸)'),
                    '幅_内寸': self._get_numeric(soup, '幅 (内寸)'),
                    '深さ_内寸': self._get_numeric(soup, '深さ (内寸)'),
                    '製法': self._get_text(soup, 'フルート'),
                    '長さ_外寸': self._get_numeric(soup, '長さ (外寸)'),
                    '幅_外寸': self._get_numeric(soup, '幅 (外寸)'),
                    '深さ_外寸': self._get_numeric(soup, '深さ (外寸)'),
                    '色': self._get_text(soup, '表面色'),
                    '形式': self._get_text(soup, '箱形式'),
                    '厚み': self._get_numeric(soup, '厚さ'),
                    '材質': self._get_text(soup, '紙質（強度）'),
                }
                
                # 1枚単位の価格情報を取得
                price_list = soup.find('ul', id='small_price_list')
                if price_list:
                    for i in range(1, 21):
                        price_element = soup.find('li', id=f'small_price{i}')
                        if price_element:
                            onclick_text = price_element.get('onclick', '')
                            match = re.search(r'change_volume\((\d+),\s*(\d+),', onclick_text)
                            if match:
                                quantity = int(match.group(1))
                                price = int(match.group(2))
                                data[f'{quantity}枚の価格'] = price
                                logging.info(f"{quantity}枚の価格: {price}円")
                
                # 10枚単位の価格を取得
                response = self.make_request(url, unit=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                price_list = soup.find('ul', id='small_price_list')
                if price_list:
                    for i in range(1, 21):
                        price_element = soup.find('li', id=f'small_price{i}')
                        if price_element:
                            onclick_text = price_element.get('onclick', '')
                            match = re.search(r'change_volume\((\d+),\s*(\d+),', onclick_text)
                            if match:
                                quantity = int(match.group(1))
                                price = int(match.group(2))
                                data[f'{quantity}枚の価格'] = price
                                logging.info(f"{quantity}枚の価格: {price}円")
                
                # big_priceの価格を取得（タブ切り替えなし）
                response = self.make_request(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for i in range(1, 21):
                    big_price_element = soup.find('li', id=f'big_price{i}')
                    if big_price_element:
                        onclick_text = big_price_element.get('onclick', '')
                        match = re.search(r'change_volume\((\d+),\s*(\d+),', onclick_text)
                        if match:
                            quantity = int(match.group(1))
                            price = int(match.group(2))
                            data[f'{quantity}枚の価格'] = price
                            logging.info(f"{quantity}枚の価格: {price}円")
                
                # データベースに保存
                self.db.save_product(data)
                logging.info(f"商品データの取得完了: {data}")
                
            except Exception as e:
                logging.error(f"商品 {product_id} の詳細取得中にエラー: {str(e)}")
                continue

def main():
    """メイン処理"""
    try:
        scraper = Scraper()
        product_id = "12345"
        product_info = scraper.get_product_details([product_id])
        if product_info:
            print("商品情報を取得しました:", product_info)
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main() 