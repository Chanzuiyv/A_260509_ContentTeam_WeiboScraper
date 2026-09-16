import os

TARGET_UIDS = {
    'LASER-顾子尧': '7465134993',
    'LASER-林致': '7465083977',
    'LASER-乔殊': '7460501050',
    'LASER-夏予扬': '7465183385',
    'MANTA-柏闻': '7634755077',
    'MANTA-江恪': '7634619308',
    'MANTA-季少一': '7591534498',
    'MANTA-许向安': '7633605104',
    'MANTA-许向宁': '7634206986'
}

USER_AGENTS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 10; SM-G970F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.101 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.101 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 13_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Mobile/15E148 Safari/604.1'
]

DEFAULT_REFERER = 'https://m.weibo.cn/'

REQUEST_DELAY_MIN = 4
REQUEST_DELAY_MAX = 8

MAX_RETRY = 3
RETRY_DELAY_BASE = 10

BLOCKED_STATUS_CODES = [403, 418, 429, 432]

REQUEST_TIMEOUT = 30

COMMENT_MAX_PAGES = 500

COOKIES_FILE = 'cookies.txt'
CHECKPOINT_POSTS_FILE = 'checkpoint_posts.json'
CHECKPOINT_COMMENTS_FILE = 'checkpoint_comments.json'

DATA_DIR = 'data'
LOG_DIR = 'logs'
SCAN_DETAILS_DIR = 'scan_details'  # 存放扫描详情

LOG_FILE = os.path.join(LOG_DIR, 'weibo_spider.log')
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'