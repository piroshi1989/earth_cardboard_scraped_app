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
QUANTITIES = [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    20,
    30,
    40,
    50,
    60,
    70,
    80,
    100,
    110,
    120,
    130,
    140,
    150,
    160,
    170,
    180,
    190,
    200,
    300,
    400,
    500,
    600,
    700,
    800,
    900,
    1000,
    1400,
    1600,
    1800,
    2000,
    2200,
    2400,
    2600,
    2800,
    3000,
    3200,
    3400,
    3600,
    3800,
    4000,
    4200,
] 

# リクエストヘッダーの設定
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0'
}

# 商品詳細ページのURL
BASE_URL = 'https://www.bestcarton.com/cardboard/box/'

# カテゴリページのURL
CATEGORY_BASE_URL = 'https://www.bestcarton.com/category/size/'