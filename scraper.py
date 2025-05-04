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
from urllib.parse import urljoin
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import threading
from contextlib import contextmanager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Scraper:
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    _thread_local = threading.local()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Scraper, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.proxy_manager = ProxyManager()
                    self.db = Database()
                    self.base_url = BASE_URL
                    self.category_base_url = CATEGORY_BASE_URL
                    self._initialized = True

    def _get_thread_local_playwright(self):
        """スレッドローカルのPlaywrightインスタンスを取得または作成"""
        if not hasattr(self._thread_local, 'playwright'):
            self._thread_local.playwright = sync_playwright().start()
            logging.info("Playwrightの初期化が完了しました")
        return self._thread_local.playwright

    def _get_thread_local_browser(self, proxy_config=None):
        """スレッドローカルのブラウザインスタンスを取得または作成"""
        if not hasattr(self._thread_local, 'browser'):
            playwright = self._get_thread_local_playwright()
            self._thread_local.browser = playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
        return self._thread_local.browser

    def _get_thread_local_context(self, proxy_config=None):
        """スレッドローカルのコンテキストインスタンスを取得または作成"""
        if not hasattr(self._thread_local, 'context'):
            browser = self._get_thread_local_browser(proxy_config)
            self._thread_local.context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                proxy=proxy_config
            )
        return self._thread_local.context

    @contextmanager
    def _get_page(self, proxy_config=None):
        """ページインスタンスを取得するコンテキストマネージャ"""
        page = None
        try:
            context = self._get_thread_local_context(proxy_config)
            page = context.new_page()
            page.set_default_timeout(60000)
            yield page
        finally:
            if page:
                try:
                    page.close()
                except Exception as e:
                    logging.error(f"ページのクローズに失敗: {str(e)}")

    def make_request(self, url, unit=None, max_retries=5):
        """Playwrightを使用してリクエストを送信"""
        for attempt in range(max_retries):
            try:
                # プロキシの取得
                best_proxy = self.proxy_manager.get_best_proxy()
                proxy_config = None
                if best_proxy:
                    # プロキシURLから認証情報を抽出
                    proxy_parts = best_proxy.split('@')
                    if len(proxy_parts) == 2:
                        auth_part = proxy_parts[0].replace('http://', '')
                        server_part = proxy_parts[1]
                        username, password = auth_part.split(':')
                        proxy_config = {
                            "server": f"http://{server_part}",
                            "username": username,
                            "password": password
                        }
                    else:
                        proxy_config = {
                            "server": best_proxy
                        }
                    logging.info(f"プロキシを使用: {best_proxy}")

                with self._get_page(proxy_config) as page:
                    # ページの読み込みを待機
                    page.goto(url, wait_until='networkidle')
                    
                    if unit:
                        try:
                            # 単位切り替えボタンが存在するか確認
                            unit_button = page.wait_for_selector(f"#unit_{unit}", timeout=10000)
                            if unit_button:
                                # JavaScriptを使用してクリックを実行
                                page.evaluate("(element) => element.click()", unit_button)
                                
                                # 価格リストの更新を待機
                                page.wait_for_function(
                                    "() => document.body.innerHTML.includes('change_volume(')",
                                    timeout=30000
                                )
                        except PlaywrightTimeoutError:
                            logging.info(f"unit_{unit} ボタンが存在しないためスキップします")
                    
                    # ページの読み込みを待機
                    time.sleep(3)
                    
                    # HTMLを取得
                    html = page.content()
                    
                    # レスポンスオブジェクトを作成
                    response = requests.Response()
                    response._content = html.encode('utf-8')
                    response.status_code = 200
                    response.encoding = 'utf-8'
                    
                    return response
                
            except Exception as e:
                if attempt == 0:
                    logging.warning(f"リクエスト失敗 (試行 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(5, 10))
                else:
                    raise

    def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            if hasattr(self._thread_local, 'context'):
                self._thread_local.context.close()
                delattr(self._thread_local, 'context')
            if hasattr(self._thread_local, 'browser'):
                self._thread_local.browser.close()
                delattr(self._thread_local, 'browser')
            if hasattr(self._thread_local, 'playwright'):
                self._thread_local.playwright.stop()
                delattr(self._thread_local, 'playwright')
        except Exception as e:
            logging.error(f"リソースのクリーンアップ中にエラー: {str(e)}")

    def __del__(self):
        """デストラクタでリソースをクリーンアップ"""
        self.cleanup()

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
        page = 1
        for size_type in sizes:
            category_url = f"{self.category_base_url}{size_type}/"
            logging.info(f"処理中のURL: {category_url}")

            product_ids = []
            
            has_next_page = True
            processed_urls = set()  # 処理済みURLを記録

            try:
                while has_next_page:
                    url = f"{category_url}?page={page}"
                    
                    # 既に処理済みのURLの場合はスキップ
                    if url in processed_urls:
                        logging.warning(f"URLが既に処理済みです: {url}")
                        has_next_page = False
                        break
                    
                    processed_urls.add(url)
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
                    
                    # エンコーディングを修正
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
                                    # 既に取得済みの商品IDはスキップ
                                    if any(p['id'] == product_id for p in product_ids):
                                        logging.info(f"商品ID {product_id} は既に取得済みです")
                                        continue

                                    product_url_tag = box.find('a')
                                    relative_url = product_url_tag['href'] if product_url_tag and product_url_tag.has_attr('href') else None
                                    full_url = urljoin(BASE_URL, relative_url) if relative_url else None
                                    
                                    product_data = {
                                        'id': product_id,
                                        'name': product_name,
                                        'url': full_url
                                    }
                                    product_ids.append(product_data)
                                    logging.info(f"商品IDを取得: {product_id} - {product_name}")
                        except Exception as e:
                            logging.error(f"商品情報の取得中にエラー: {str(e)}")
                            continue

                    # 次のページの確認
                    next_page_link = soup.find('li', class_='next_page')
                    if not next_page_link:
                        logging.info("次のページが見つかりません。ページネーション終了")
                        has_next_page = False

                        # 商品IDをデータベースに保存
                        if product_ids:
                            self.db.save_product_ids(product_ids, size_type)
                            all_product_ids.extend(product_ids)
                            logging.info(f"サイズ {size_type} の商品ID {len(product_ids)} 件を保存しました")
                        else:
                            logging.warning(f"サイズ {size_type} の商品が見つかりませんでした")
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
        all_data = []  # 全商品のデータを格納するリスト
        
        for product_id in product_ids:
            try:
                urls = self.db.get_url_by_product_id(product_id)
                if not urls:
                    logging.error(f"商品ID {product_id} のURLが見つかりません")
                    continue
                    
                url = urls[0]['url']
                logging.info(f"商品詳細の取得を開始: {url}")
                
                # 1枚単位の価格を取得
                max_retries = 3  # 最大再試行回数
                for attempt in range(max_retries):
                    try:
                        with self._get_page() as page:
                            logging.info("新しいページを作成しました")
                            
                            # ページの読み込みを待機
                            logging.info("ページの読み込みを開始")
                            try:
                                page.goto(url, wait_until='networkidle')
                                time.sleep(5)  # ページの完全な読み込みを待機
                                logging.info("ページの読み込みが完了しました")
                            except Exception as e:
                                logging.error(f"ページの読み込みに失敗: {str(e)}")
                                if attempt < max_retries - 1:
                                    time.sleep(5)  # 再試行前に待機
                                    continue
                                raise
                            
                            # 1枚単位の価格を取得
                            try:
                                logging.info("1枚単位の価格取得を開始")
                                unit_button = page.wait_for_selector("#unit_1", timeout=15000)
                                if unit_button:
                                    logging.info("unit_1 ボタンが見つかりました")
                                    try:
                                        page.evaluate("(element) => element.click()", unit_button)
                                        logging.info("unit_1 ボタンをクリックしました")
                                        
                                        # 価格リストの更新を待機
                                        logging.info("価格リストの更新を待機中")
                                        page.wait_for_function(
                                            "() => document.body.innerHTML.includes('change_volume(')",
                                            timeout=45000
                                        )
                                        time.sleep(5)  # 価格リストの更新を待機
                                        logging.info("価格リストの更新が完了しました")
                                    except Exception as e:
                                        logging.error(f"unit_1 ボタンのクリックに失敗: {str(e)}")
                                        raise
                            except PlaywrightTimeoutError:
                                logging.info("unit_1 ボタンが存在しないためスキップします")
                            
                            # HTMLを取得
                            logging.info("HTMLの取得を開始")
                            try:
                                html = page.content()
                                soup = BeautifulSoup(html, 'html.parser')
                                logging.info("HTMLの取得が完了しました")
                            except Exception as e:
                                logging.error(f"HTMLの取得に失敗: {str(e)}")
                                raise
                            
                            # 商品データの取得
                            logging.info("商品データの取得を開始")
                            try:
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
                                logging.info("商品データの取得が完了しました")
                            except Exception as e:
                                logging.error(f"商品データの取得に失敗: {str(e)}")
                                raise
                            
                            # 1枚単位の価格情報を取得
                            logging.info("1枚単位の価格情報の取得を開始")
                            try:
                                price_list = soup.find('ul', id='small_price_list')
                                if price_list:
                                    logging.info("価格リストが見つかりました")
                                    MAX_ITERATIONS = 120
                                    i = 1
                                    while i <= MAX_ITERATIONS:
                                        price_element = soup.find('li', id=f'small_price{i}')
                                        if not price_element:
                                            logging.info(f"価格要素 {i} が見つかりませんでした")
                                            break
                                            
                                        onclick_text = price_element.get('onclick', '')
                                        match = re.search(r'change_volume\((\d+),\s*(\d+),', onclick_text)
                                        if match:
                                            quantity = int(match.group(1))
                                            price = int(match.group(2))
                                            data[f'{quantity}枚の価格'] = price
                                            logging.info(f"{quantity}枚の価格を取得: {price}円")
                                            i += 1
                                        else:
                                            logging.info(f"価格要素 {i} のパターンマッチに失敗しました")
                                            break
                                else:
                                    logging.warning("価格リストが見つかりませんでした")
                            except Exception as e:
                                logging.error(f"1枚単位の価格情報の取得に失敗: {str(e)}")
                                raise
                            
                            # 10枚単位の価格を取得
                            try:
                                logging.info("10枚単位の価格取得を開始")
                                unit_button = page.wait_for_selector("#unit_10", timeout=15000)
                                if unit_button:
                                    logging.info("unit_10 ボタンが見つかりました")
                                    try:
                                        page.evaluate("(element) => element.click()", unit_button)
                                        logging.info("unit_10 ボタンをクリックしました")
                                        
                                        # 価格リストの更新を待機
                                        logging.info("価格リストの更新を待機中")
                                        page.wait_for_function(
                                            "() => document.body.innerHTML.includes('change_volume(')",
                                            timeout=45000
                                        )
                                        time.sleep(5)  # 価格リストの更新を待機
                                        logging.info("価格リストの更新が完了しました")
                                        
                                        # HTMLを再取得
                                        logging.info("HTMLの再取得を開始")
                                        html = page.content()
                                        soup = BeautifulSoup(html, 'html.parser')
                                        logging.info("HTMLの再取得が完了しました")
                                    except Exception as e:
                                        logging.error(f"unit_10 ボタンのクリックに失敗: {str(e)}")
                                        raise
                                else:
                                    logging.info("unit_10 ボタンが存在しないためスキップします")
                                
                                # 10枚単位の価格情報を取得
                                logging.info("10枚単位の価格情報の取得を開始")
                                price_list = soup.find('ul', id='small_price_list')
                                if price_list:
                                    logging.info("価格リストが見つかりました")
                                    MAX_ITERATIONS = 120
                                    i = 1
                                    while i <= MAX_ITERATIONS:
                                        price_element = soup.find('li', id=f'small_price{i}')
                                        if not price_element:
                                            logging.info(f"価格要素 {i} が見つかりませんでした")
                                            break
                                            
                                        onclick_text = price_element.get('onclick', '')
                                        match = re.search(r'change_volume\((\d+),\s*(\d+),', onclick_text)
                                        if match:
                                            quantity = int(match.group(1))
                                            price = int(match.group(2))
                                            data[f'{quantity}枚の価格'] = price
                                            logging.info(f"{quantity}枚の価格を取得: {price}円")
                                            i += 1
                                        else:
                                            logging.info(f"価格要素 {i} のパターンマッチに失敗しました")
                                            break
                                else:
                                    logging.warning("価格リストが見つかりませんでした")
                                
                                # まとめ買いの価格を取得
                                logging.info("まとめ買いの価格取得を開始")
                                big_price_list = soup.find('ul', id='big_price_list')
                                if big_price_list:
                                    logging.info("価格リストが見つかりました")
                                    MAX_ITERATIONS = 120
                                    i = 1
                                    while i <= MAX_ITERATIONS:
                                        big_price_element = big_price_list.find('li', id=f'big_price{i}')
                                        if not big_price_element:
                                            logging.info(f"価格要素 {i} が見つかりませんでした")
                                            break
                                            
                                        onclick_text = big_price_element.get('onclick', '')
                                        match = re.search(r'change_volume\((\d+),\s*(\d+),', onclick_text)
                                        if match:
                                            quantity = int(match.group(1))
                                            price = int(match.group(2))
                                            data[f'{quantity}枚の価格'] = price
                                            logging.info(f"{quantity}枚の価格を取得: {price}円")
                                            i += 1
                                        else:
                                            logging.info(f"価格要素 {i} のパターンマッチに失敗しました")
                                            break
                                else:
                                    logging.warning("価格リストが見つかりませんでした")
                            except Exception as e:
                                logging.error(f"10枚単位の価格取得中にエラー: {str(e)}")
                                raise
                            
                            # データベースに保存
                            logging.info("データベースへの保存を開始")
                            try:
                                self.db.save_product(data)
                                logging.info(f"商品データの取得完了: {product_id}")
                                
                                # 取得したデータをリストに追加
                                all_data.append(data)
                                logging.info("商品データをリストに追加しました")
                                break
                            except Exception as e:
                                logging.error(f"データベースへの保存に失敗: {str(e)}")
                                raise
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logging.warning(f"リクエスト失敗 (試行 {attempt + 1}/{max_retries}): {str(e)}")
                            time.sleep(random.uniform(10, 15))  # 再試行前の待機時間を延長
                        else:
                            raise
                
            except Exception as e:
                logging.error(f"商品 {product_id} の詳細取得中にエラー: {str(e)}")
                continue
        
        return all_data  # 取得した全商品のデータを返す

def main():
    """メイン処理"""
    try:
        scraper = Scraper()
        product_id = "12345"
        product_info = scraper.get_product_details(product_id)
        if product_info:
            print("商品情報を取得しました:", product_info)
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main() 