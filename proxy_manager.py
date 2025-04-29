import requests
from bs4 import BeautifulSoup
import random
import time
import os

class ProxyManager:
    def __init__(self):
        self.proxy_sources = [
            "https://free-proxy-list.net/",
            "https://www.sslproxies.org/",
            "https://www.us-proxy.org/"
        ]
        self.proxies = []
        self.load_proxies()

    def load_proxies(self):
        """無料プロキシリストからプロキシを取得"""
        for source in self.proxy_sources:
            try:
                print(f"プロキシを取得中: {source}")
                response = requests.get(source, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # プロキシテーブルから情報を抽出
                table = soup.find('table')
                if table:
                    for row in table.find_all('tr')[1:]:  # ヘッダー行をスキップ
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            proxy = f"http://{ip}:{port}"
                            self.proxies.append(proxy)
                            print(f"プロキシを追加: {proxy}")
                
                # 次のサイトへのリクエスト前に待機
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"プロキシ取得エラー ({source}): {str(e)}")
                continue

        print(f"合計 {len(self.proxies)} 件のプロキシを取得しました")

    def test_proxy(self, proxy, timeout=5):
        """プロキシの動作確認"""
        try:
            proxies = {
                'http': proxy,
                'https': proxy
            }
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=timeout
            )
            if response.status_code == 200:
                print(f"プロキシ動作確認成功: {proxy}")
                return True
        except Exception as e:
            print(f"プロキシ動作確認失敗 ({proxy}): {str(e)}")
        return False

    def get_working_proxies(self, count=3):
        """動作するプロキシを取得"""
        working_proxies = []
        for proxy in self.proxies:
            if self.test_proxy(proxy):
                working_proxies.append(proxy)
                if len(working_proxies) >= count:
                    break
            time.sleep(1)  # テスト間の待機
        
        return working_proxies

def main():
    """メイン処理"""
    try:
        proxy_manager = ProxyManager()
        working_proxies = proxy_manager.get_working_proxies()
        if working_proxies:
            print("動作するプロキシを取得しました:")
            for proxy in working_proxies:
                print(proxy)
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main() 