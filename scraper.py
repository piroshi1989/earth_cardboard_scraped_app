import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests
import time
import random
import logging
import re
from bs4 import BeautifulSoup
from database import Database
from config import SIZES, BASE_URL, CATEGORY_BASE_URL, HEADERS, QUANTITIES
from proxy_manager import ProxyManager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Scraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.db = Database()
        self.base_url = BASE_URL
        self.category_base_url = CATEGORY_BASE_URL
        self.proxy_manager = ProxyManager()
        self.proxies = self.proxy_manager.get_working_proxies()
        
        # リトライ設定を追加
        retry_strategy = Retry(
            total=3,  # 最大リトライ回数
            backoff_factor=1,  # リトライ間隔
            status_forcelist=[500, 502, 503, 504]  # リトライするステータスコード
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _make_request(self, url):
        """リクエストを送信し、レスポンスを返す"""
        try:
            if self.proxies:
                proxy = random.choice(self.proxies)
                self.session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
            
            # リクエスト前にランダムな待機時間を設定
            time.sleep(random.uniform(3, 7))
            
            # SSL証明書の検証を無効化し、タイムアウトを設定
            response = self.session.get(
                url,
                verify=False,
                timeout=30,
                headers=self.session.headers
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"リクエストエラー: {str(e)}")
            # エラーが発生した場合、プロキシを切り替えて再試行
            if self.proxies and len(self.proxies) > 1:
                self.proxies.remove(proxy)
                logging.info(f"プロキシを切り替えて再試行します。残りのプロキシ数: {len(self.proxies)}")
                return self._make_request(url)
            raise

    def _extract_size_from_url(self, url):
        """URLからサイズ情報を抽出"""
        size_match = re.search(r'/([A-Z]\d+)/', url)
        return size_match.group(1) if size_match else None
    
    def get_product_ids(self, size=None):
        """指定されたサイズの商品IDを取得してデータベースに保存"""
        if size is None:
            sizes = SIZES
        else:
            sizes = [size] if isinstance(size, str) else size

        logging.info(f"取得対象のサイズ: {sizes}")

        all_product_ids = []
        for size_type in sizes:
            category_url = f"{self.category_base_url}{size_type}/"
            logging.info(f"処理中のURL: {category_url}")

            product_ids = []
            page = 1
            has_next_page = True

            try:
                while has_next_page:
                    url = f"{category_url}?page={page}" if page > 1 else category_url
                    logging.info(f"ページ {page} の処理を開始...")
                    logging.info(f"URL: {url}")
                    
                    # リクエスト前に待機
                    sleep_time = random.uniform(2, 5)
                    logging.info(f"待機時間: {sleep_time:.2f}秒")
                    time.sleep(sleep_time)
                    
                    # リクエスト実行
                    logging.info("リクエスト送信中...")
                    response = self._make_request(url)
                    logging.info(f"ステータスコード: {response.status_code}")
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 商品ボックスの検索
                    result_box = soup.find('div', id='resultBox')
                    if result_box:
                        product_boxes = result_box.find_all('div', class_='product_box')
                    if not result_box:
                        logging.warning(f"ページ {page} で商品が見つかりません")
                        has_next_page = False
                        break
                    
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
                                        'url': product_url  # URLを追加
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
        
        selectors = {
            '外形 三辺合計': {
                'selector': 'dt:contains("3辺外寸合計") + dd a',
                'process': lambda text: float(text.split()[0]) if text else None
            },
            '長さ (内寸)': {
                'selector': 'dt:contains("内寸法") + dd',
                'process': lambda text: float(text.split('×')[0]) if text else None
            },
            '幅 (内寸)': {
                'selector': 'dt:contains("内寸法") + dd',
                'process': lambda text: float(text.split('×')[1]) if text else None
            },
            '深さ (内寸)': {
                'selector': 'dt:contains("内寸法") + dd',
                'process': lambda text: float(text.split('×')[2].split('(')[0]) if text else None
            },
            '長さ (外寸)': {
                'selector': 'dt:contains("外寸法") + dd',
                'process': lambda text: float(text.split('×')[0]) if text else None
            },
            '幅 (外寸)': {
                'selector': 'dt:contains("外寸法") + dd',
                'process': lambda text: float(text.split('×')[1]) if text else None
            },
            '深さ (外寸)': {
                'selector': 'dt:contains("外寸法") + dd',
                'process': lambda text: float(text.split('×')[2].split('(')[0]) if text else None
            }
        }

        if label in selectors:
            selector_info = selectors[label]
            element = soup.select_one(selector_info['selector'])
            
            if element:
                text = element.text.strip()
                if 'process' in selector_info:
                    result = selector_info['process'](text)
                    logging.info(f"{label} の取得結果: {result}")
                    return result
            else:
                logging.warning(f"{label} の要素が見つかりませんでした")
                logging.debug(f"HTMLの構造:\n{soup.prettify()[:1000]}")
                return None

        element = soup.find('th', string=label)
        if element:
            value = element.find_next('td').text.strip()
            result = float(value) if value else None
            logging.info(f"{label} の取得結果: {result}")
            return result
        
        logging.warning(f"{label} の要素が見つかりませんでした")
        return None

    def _get_text(self, soup, label):
        """テキストデータを取得"""
        logging.info(f"テキストデータの取得を開始: {label}")
        
        selectors = {
            '色': {
                'selector': 'dt:contains("表面色") + dd',
                'text': True
            },
            '形式': {
                'selector': 'dt:contains("箱形式") + dd a',
                'text': True
            },
            '厚み': {
                'selector': 'dt:contains("厚さ") + dd',
                'process': lambda text, soup: (text.strip() + " " + soup.select_one('dt:contains("フルート") + dd').text.strip()) if text else None
            },
            '材質': {
                'selector': 'dt:contains("紙質（強度）") + dd span#more_quality',
                'text': True
            }
        }

        if label in selectors:
            selector_info = selectors[label]
            element = soup.select_one(selector_info['selector'])
            
            if element:
                if 'attr' in selector_info:
                    value = element.get(selector_info['attr'], '').strip()
                    if 'process' in selector_info:
                        result = selector_info['process'](value, soup)
                        logging.info(f"{label} の取得結果: {result}")
                        return result
                    logging.info(f"{label} の取得結果: {value}")
                    return value
                elif selector_info.get('text', False):
                    result = element.text.strip()
                    logging.info(f"{label} の取得結果: {result}")
                    return result
                elif 'process' in selector_info:
                    result = selector_info['process'](element.text, soup)
                    logging.info(f"{label} の取得結果: {result}")
                    return result
            logging.warning(f"{label} の要素が見つかりませんでした")
            logging.debug(f"HTMLの構造:\n{soup.prettify()[:1000]}")
            return None

        element = soup.find('dt', string=label)
        if element:
            value = element.find_next('dd').text.strip()
            logging.info(f"{label} の取得結果: {value}")
            return value
        
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
                
                # リクエスト前に待機
                sleep_time = random.uniform(2, 5)
                logging.info(f"待機時間: {sleep_time:.2f}秒")
                time.sleep(sleep_time)
                
                # リクエスト実行
                logging.info("リクエスト送信中...")
                response = self._make_request(url)
                logging.info(f"ステータスコード: {response.status_code}")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 商品データの取得
                data = {
                    '商品コード': product_id,
                    '商品名': soup.select_one('dt:contains("商品名") + dd').text.strip(),
                    'サイズ': self._extract_size_from_url(url),
                    'url': url,
                    '外形_三辺合計': self._get_numeric(soup, '外形 三辺合計'),
                    '長さ_内寸': self._get_numeric(soup, '長さ (内寸)'),
                    '幅_内寸': self._get_numeric(soup, '幅 (内寸)'),
                    '深さ_内寸': self._get_numeric(soup, '深さ (内寸)'),
                    '製法': self._get_text(soup, '製法'),
                    '長さ_外寸': self._get_numeric(soup, '長さ (外寸)'),
                    '幅_外寸': self._get_numeric(soup, '幅 (外寸)'),
                    '深さ_外寸': self._get_numeric(soup, '深さ (外寸)'),
                    '加工先': self._get_text(soup, '加工先'),
                    '色': self._get_text(soup, '色'),
                    '形式': self._get_text(soup, '形式'),
                    '厚み': self._get_text(soup, '厚み'),
                    '材質': self._get_text(soup, '材質'),
                    '規格幅': self._get_numeric(soup, '規格幅')
                }
                
                logging.info(f"基本情報の取得完了: {data}")

                # 枚数データの取得
                for size in QUANTITIES:
                    logging.info(f"枚数 {size} の価格を取得中...")
                    price_element = soup.select_one(f'li#small_price1[onclick*="change_volume({size}"]')
                    if price_element:
                        price_text = price_element.text.strip()
                        price = int(re.sub(r'[^\d]', '', price_text.split('円')[0]))
                        data[f'枚数_{size}'] = price
                        logging.info(f"枚数 {size} の価格: {price}円")
                    else:
                        data[f'枚数_{size}'] = None
                        logging.warning(f"枚数 {size} の価格が見つかりませんでした")

                logging.info(f"商品データの取得完了: {data}")
                
                # データベースに保存
                self.db.save_product(data)

                return data
                
            except Exception as e:
                logging.error(f"商品 {product_id} の詳細取得中にエラー: {str(e)}")
                continue 