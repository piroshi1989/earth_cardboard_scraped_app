import requests
import logging
import time
from datetime import datetime, timedelta
from config import PROXY_CONFIGS

class ProxyManager:
    def __init__(self):
        self.proxy_configs = PROXY_CONFIGS
        self.current_proxy_index = 0
        self.working_proxies = []
        self.proxy_stats = {}  # プロキシの使用統計
        self.test_interval = 300  # プロキシテスト間隔（秒）
        self.timeout = 10  # タイムアウト時間（秒）
        self.max_retries = 3  # 最大リトライ回数
        self.last_test_time = {}  # 最後のテスト時間
        self._init_proxies()

    def _init_proxies(self):
        """プロキシURLを初期化"""
        self.proxies = []
        for config in self.proxy_configs:
            proxy_url = self._format_proxy_url(config)
            self.proxies.append(proxy_url)
            self.proxy_stats[proxy_url] = {
                'success_count': 0,
                'failure_count': 0,
                'last_success': None,
                'last_failure': None,
                'total_response_time': 0
            }
            self.last_test_time[proxy_url] = datetime.now() - timedelta(seconds=self.test_interval)
        logging.info(f"{len(self.proxies)}件のプロキシを初期化しました")

    def _format_proxy_url(self, config):
        """プロキシ設定からURLを生成"""
        return f"http://{config['username']}:{config['password']}@{config['host']}:{config['port']}"

    def get_next_proxy(self):
        """次のプロキシを取得（ローテーション）"""
        if not self.proxies:
            logging.warning("利用可能なプロキシがありません")
            return None

        # 動作するプロキシを優先
        if self.working_proxies:
            proxy = self.working_proxies[self.current_proxy_index % len(self.working_proxies)]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.working_proxies)
        else:
            proxy = self.proxies[self.current_proxy_index % len(self.proxies)]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)

        logging.info(f"プロキシを切り替え: {proxy}")
        return proxy

    def test_proxy(self, proxy, timeout=None):
        """プロキシの動作確認"""
        if timeout is None:
            timeout = self.timeout

        # テスト間隔をチェック
        if (datetime.now() - self.last_test_time[proxy]).total_seconds() < self.test_interval:
            return self.proxy_stats[proxy]['success_count'] > 0

        try:
            start_time = time.time()
            proxies = {
                'http': proxy,
                'https': proxy
            }
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=timeout
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                self._update_proxy_stats(proxy, success=True, response_time=response_time)
                logging.info(f"プロキシ動作確認成功: {proxy} (応答時間: {response_time:.2f}秒)")
                return True
        except Exception as e:
            self._update_proxy_stats(proxy, success=False)
            logging.warning(f"プロキシ動作確認失敗 ({proxy}): {str(e)}")
        return False

    def _update_proxy_stats(self, proxy, success, response_time=0):
        """プロキシの統計情報を更新"""
        stats = self.proxy_stats[proxy]
        if success:
            stats['success_count'] += 1
            stats['last_success'] = datetime.now()
            stats['total_response_time'] += response_time
        else:
            stats['failure_count'] += 1
            stats['last_failure'] = datetime.now()
        self.last_test_time[proxy] = datetime.now()

    def get_working_proxies(self):
        """動作するプロキシのリストを取得"""
        working_proxies = []
        for proxy in self.proxies:
            if self.test_proxy(proxy):
                working_proxies.append(proxy)
        
        if not working_proxies:
            logging.error("動作するプロキシが見つかりません")
        else:
            logging.info(f"動作するプロキシを {len(working_proxies)} 件見つけました")
        
        self.working_proxies = working_proxies
        return working_proxies

    def get_proxy_stats(self):
        """プロキシの統計情報を取得"""
        return self.proxy_stats

    def get_best_proxy(self):
        """最も信頼性の高いプロキシを取得"""
        if not self.proxy_stats:
            return None

        best_proxy = max(
            self.proxy_stats.items(),
            key=lambda x: (
                x[1]['success_count'],
                -x[1]['failure_count'],
                -x[1]['total_response_time'] / max(x[1]['success_count'], 1)
            )
        )[0]
        return best_proxy

    def make_request_with_proxy(self, url, max_retries=None):
        """プロキシを使用してリクエストを送信"""
        if max_retries is None:
            max_retries = self.max_retries

        for attempt in range(max_retries):
            proxy = self.get_next_proxy()
            if not proxy:
                logging.error("利用可能なプロキシがありません")
                return None

            try:
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
                response = requests.get(url, proxies=proxies, timeout=self.timeout)
                response.raise_for_status()
                self._update_proxy_stats(proxy, success=True)
                return response
            except Exception as e:
                self._update_proxy_stats(proxy, success=False)
                logging.warning(f"リクエスト失敗 (試行 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # リトライ前の待機

        logging.error(f"最大リトライ回数を超えました: {url}")
        return None

def main():
    """メイン処理"""
    try:
        proxy_manager = ProxyManager()
        working_proxies = proxy_manager.get_working_proxies()
        if working_proxies:
            print("動作するプロキシを取得しました:")
            for proxy in working_proxies:
                print(proxy)
            
            print("\nプロキシの統計情報:")
            stats = proxy_manager.get_proxy_stats()
            for proxy, stat in stats.items():
                print(f"\n{proxy}:")
                print(f"  成功回数: {stat['success_count']}")
                print(f"  失敗回数: {stat['failure_count']}")
                if stat['success_count'] > 0:
                    avg_time = stat['total_response_time'] / stat['success_count']
                    print(f"  平均応答時間: {avg_time:.2f}秒")
            
            best_proxy = proxy_manager.get_best_proxy()
            print(f"\n最適なプロキシ: {best_proxy}")
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main() 