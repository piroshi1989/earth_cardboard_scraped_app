# サイズのリスト
SIZES = [
    'size-60',
    'size-80',
    'size-100',
    'size-120',
    'size-140',
    'size-160',
    'size-mail-A4-25',
    'size-mail-A4-30'
]

# 枚数のリスト
QUANTITIES = [i for i in range(1, 10)] + [i for i in range(10, 4210, 10)]

# プロキシ設定
PROXY_CONFIGS = [
    {'host': '82.23.196.48', 'port': 6754, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '82.23.84.7', 'port': 7263, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '159.148.109.87', 'port': 5689, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '207.228.6.9', 'port': 7741, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '212.60.14.209', 'port': 7006, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '45.56.142.244', 'port': 6634, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '72.1.179.52', 'port': 6446, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '82.23.63.197', 'port': 7951, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '72.1.135.186', 'port': 6578, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '159.148.109.224', 'port': 5826, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '82.21.52.209', 'port': 6473, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '82.23.95.156', 'port': 6882, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '154.194.17.187', 'port': 5497, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '154.217.183.155', 'port': 6557, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '45.196.34.226', 'port': 5538, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '159.148.109.236', 'port': 5838, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '69.30.72.52', 'port': 5108, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '63.246.132.187', 'port': 5505, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '45.196.48.55', 'port': 5481, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '46.203.32.201', 'port': 6700, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '69.30.76.121', 'port': 6517, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '156.237.36.57', 'port': 5959, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '156.237.49.68', 'port': 6469, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '45.45.201.179', 'port': 5466, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'},
    {'host': '130.180.255.178', 'port': 9869, 'username': 'eephhnsv', 'password': 'o6ubqbfofs5z'}
]

# リクエストヘッダーの設定
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'Referer': 'https://www.bestcarton.com/',
    'DNT': '1',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}

# 商品詳細ページのURL
BASE_URL = 'https://www.bestcarton.com'

# カテゴリページのURL
CATEGORY_BASE_URL = 'https://www.bestcarton.com/category/size/'