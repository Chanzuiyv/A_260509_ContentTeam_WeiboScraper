import requests
import random
import time
import os
import logging
from config import USER_AGENTS, DEFAULT_REFERER, COOKIES_FILE, MAX_RETRY, RETRY_DELAY_BASE, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, BLOCKED_STATUS_CODES, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.session = requests.Session()
        self.cookies = self._load_cookies()
        self.current_cookie_index = 0
        self.headers_list = self._generate_headers_list()
        self._update_session_headers()
    
    def _load_cookies(self):
        cookies = []
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        cookies.append(line)
        if not cookies:
            cookies.append('')
        return cookies
    
    def _generate_headers_list(self):
        headers_list = []
        for ua in USER_AGENTS:
            headers = {
                'User-Agent': ua,
                'Referer': DEFAULT_REFERER,
                'Accept': 'application/json, text/plain, */*',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0'
            }
            headers_list.append(headers)
        return headers_list
    
    def _update_session_headers(self):
        headers = random.choice(self.headers_list).copy()
        if self.cookies[self.current_cookie_index]:
            headers['Cookie'] = self.cookies[self.current_cookie_index]
        self.session.headers.clear()
        self.session.headers.update(headers)
    
    def _switch_cookie(self):
        self.current_cookie_index = (self.current_cookie_index + 1) % len(self.cookies)
        self._update_session_headers()
        logger.warning(f'已切换到第 {self.current_cookie_index + 1} 个Cookie')
    
    def request(self, method, url, **kwargs):
        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
        
        kwargs.setdefault('timeout', REQUEST_TIMEOUT)
        
        for retry in range(MAX_RETRY):
            try:
                self._update_session_headers()
                
                response = self.session.request(method, url, **kwargs)
                
                if response.status_code in BLOCKED_STATUS_CODES:
                    raise requests.exceptions.RequestException(f'请求被拦截，状态码: {response.status_code}')
                
                if self._is_blocked(response):
                    raise requests.exceptions.RequestException(f'请求被拦截')
                
                return response
            
            except requests.exceptions.RequestException as e:
                status_code = response.status_code if 'response' in dir() else '未知'
                delay = RETRY_DELAY_BASE ** retry
                logger.warning(f'请求失败 ({status_code}), 第{retry + 1}次重试，等待{delay}秒...')
                time.sleep(delay)
                
                if retry < MAX_RETRY - 1:
                    self._switch_cookie()
            
            except requests.exceptions.Timeout:
                delay = RETRY_DELAY_BASE ** retry
                logger.warning(f'请求超时，第{retry + 1}次重试，等待{delay}秒...')
                time.sleep(delay)
                
                if retry < MAX_RETRY - 1:
                    self._switch_cookie()
            
            except Exception as e:
                delay = RETRY_DELAY_BASE ** retry
                logger.warning(f'请求发生未知错误: {str(e)}，第{retry + 1}次重试，等待{delay}秒...')
                time.sleep(delay)
                
                if retry < MAX_RETRY - 1:
                    self._switch_cookie()
        
        logger.error(f'请求失败 {MAX_RETRY} 次，放弃: {url}')
        return None
    
    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)
    
    def _is_blocked(self, response):
        try:
            content = response.text.lower()
            if '验证码' in content or 'captcha' in content or 'blocked' in content:
                return True
            if '请输入验证码' in content or '安全验证' in content:
                return True
        except:
            pass
        
        return False