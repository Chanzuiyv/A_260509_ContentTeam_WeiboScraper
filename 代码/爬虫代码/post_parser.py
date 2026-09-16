import json
import re
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class PostParser:
    def __init__(self, session_manager):
        self.session = session_manager
    
    def _extract_text(self, html_text):
        if not html_text:
            return ''
        
        try:
            html_text = html_text.replace('<br/>', '\n').replace('<br />', '\n')
            
            soup = BeautifulSoup(html_text, 'html.parser')
            
            text = soup.get_text(separator=' ')
            
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception as e:
            logger.error(f'解析文本失败: {e}')
            return html_text
    
    def _extract_pics(self, post_data):
        pics = []
        if 'pics' in post_data and post_data['pics']:
            for pic in post_data['pics']:
                if 'large' in pic and 'url' in pic['large']:
                    pics.append(pic['large']['url'])
                elif 'url' in pic:
                    pics.append(pic['url'])
        return pics
    
    def _extract_videos(self, post_data):
        videos = []
        if 'page_info' in post_data and post_data['page_info']:
            page_info = post_data['page_info']
            if page_info.get('type') == 'video':
                if 'media_info' in page_info:
                    media_info = page_info['media_info']
                    if 'mp4_720p_mp4' in media_info:
                        videos.append(media_info['mp4_720p_mp4'])
                    elif 'mp4_hd_url' in media_info:
                        videos.append(media_info['mp4_hd_url'])
                    elif 'mp4_url' in media_info:
                        videos.append(media_info['mp4_url'])
                    elif 'stream_url_hd' in media_info:
                        videos.append(media_info['stream_url_hd'])
                    elif 'stream_url' in media_info:
                        videos.append(media_info['stream_url'])
        return videos
    
    def _parse_created_at(self, created_at_str):
        try:
            if not created_at_str:
                return ''
            
            if '分钟前' in created_at_str:
                minutes = int(re.search(r'(\d+)分钟前', created_at_str).group(1))
                dt = datetime.now() - timedelta(minutes=minutes)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            elif '小时前' in created_at_str:
                hours = int(re.search(r'(\d+)小时前', created_at_str).group(1))
                dt = datetime.now() - timedelta(hours=hours)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            elif '昨天' in created_at_str:
                dt = datetime.now() - timedelta(days=1)
                time_str = re.search(r'昨天 (\d+:\d+)', created_at_str).group(1)
                return f"{dt.strftime('%Y-%m-%d')} {time_str}:00"
            elif created_at_str.count('-') == 1:
                return f"{datetime.now().year}-{created_at_str} 00:00:00"
            elif len(created_at_str) == 10:
                return f"{created_at_str} 00:00:00"
            else:
                try:
                    dt = datetime.strptime(created_at_str, '%a %b %d %H:%M:%S %z %Y')
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        dt = datetime.strptime(created_at_str, '%a %b %d %H:%M:%S +0800 %Y')
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        return created_at_str
        except Exception as e:
            logger.error(f'解析时间失败: {created_at_str}, 错误: {e}')
            return created_at_str
    
    def _is_original(self, post_data):
        if 'retweeted_status' in post_data and post_data['retweeted_status']:
            return 0
        return 1
    
    def _fetch_long_text(self, post_id):
        url = f'https://m.weibo.cn/statuses/extend?id={post_id}'
        try:
            response = self.session.get(url)
            if response:
                data = response.json()
                if data.get('ok') == 1:
                    long_text = data.get('data', {}).get('longTextContent', '')
                    if long_text and len(long_text) > 0:
                        logger.debug(f'成功获取长微博 {post_id}，长度: {len(long_text)}')
                        return long_text
                    else:
                        logger.warning(f'长微博 {post_id} 内容为空')
        except Exception as e:
            logger.error(f'获取长微博内容失败: {post_id}, 错误: {e}')
        return None
    
    def parse_post(self, post_data):
        try:
            post_id = str(post_data.get('id', ''))
            text = post_data.get('text', '')
            
            if post_data.get('isLongText'):
                long_text = self._fetch_long_text(post_id)
                if long_text:
                    text = long_text
            
            return {
                'screen_name': post_data.get('user', {}).get('screen_name', ''),
                'id': post_id,
                'created_at': self._parse_created_at(post_data.get('created_at', '')),
                'text': self._extract_text(text),
                'is_original': self._is_original(post_data),
                'reposts_count': post_data.get('reposts_count', 0),
                'comments_count': post_data.get('comments_count', 0),
                'attitudes_count': post_data.get('attitudes_count', 0),
                'pics': ','.join(self._extract_pics(post_data)),
                'videos': ','.join(self._extract_videos(post_data)),
                'url': f"https://m.weibo.cn/detail/{post_data.get('id', '')}"
            }
        except Exception as e:
            logger.error(f'解析帖子失败: {e}')
            return None
    
    def fetch_user_posts(self, uid, since_date=None, until_date=None):
        posts = []
        scan_records = []  # 用于保存扫描详情
        page = 1
        base_url = f'https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}&containerid=107603{uid}'
        
        logger.info(f'开始获取用户 {uid} 的微博列表')
        
        while page <= 100:
            url = f'{base_url}&page={page}'
            logger.info(f'正在请求第 {page} 页: {url}')
            response = self.session.get(url)
            
            if not response:
                logger.warning(f'用户 {uid} 第 {page} 页请求失败')
                break
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.error(f'解析用户 {uid} 微博列表失败，响应不是JSON')
                break
            
            if data.get('ok') != 1:
                logger.warning(f'获取用户 {uid} 微博列表失败: {data.get("msg", "未知错误")}')
                break
            
            cards = data.get('data', {}).get('cards', [])
            card_count = len(cards)
            
            logger.info(f'用户 {uid} 第 {page} 页返回 {card_count} 个 card')
            
            page_has_any_after_since = False
            
            for card in cards:
                card_type = card.get('card_type')
                logger.info(f'处理 card_type={card_type}')
                
                if card_type == 9:
                    mblog = card.get('mblog', {})
                    post = self.parse_post(mblog)
                    if post:
                        post_time = post['created_at']
                        
                        if not post_time:
                            scan_records.append({
                                'page': page,
                                'card_type': card_type,
                                'weibo_id': post['id'],
                                'created_at': 'N/A',
                                'is_original': 'N/A',
                                'is_collected': False,
                                'reason': '时间解析失败',
                                'weibo_url': f'https://m.weibo.cn/detail/{post["id"]}'
                            })
                            continue
                        
                        post_date = post_time.split(' ')[0] if ' ' in post_time else post_time
                        is_original = post['is_original'] == 1
                        
                        logger.info(f'微博 {post["id"]}: 时间={post_date}, 原创={is_original}')
                        
                        if since_date and post_date >= since_date:
                            page_has_any_after_since = True
                        
                        reason = ''
                        is_collected = True
                        
                        if not is_original:
                            reason = '不是原创微博'
                            is_collected = False
                        elif since_date and post_date < since_date:
                            reason = f'早于时间起点 {since_date}'
                            is_collected = False
                        elif until_date and post_date > until_date:
                            reason = f'晚于时间终点 {until_date}'
                            is_collected = False
                        
                        if is_collected:
                            posts.append(post)
                            logger.info(f'微博 {post["id"]} 已添加到采集列表')
                        else:
                            logger.info(f'微博 {post["id"]} {reason}，跳过')
                        
                        scan_records.append({
                            'page': page,
                            'card_type': card_type,
                            'weibo_id': post['id'],
                            'created_at': post_date,
                            'is_original': is_original,
                            'is_collected': is_collected,
                            'reason': reason,
                            'weibo_url': f'https://m.weibo.cn/detail/{post["id"]}'
                        })
                
                elif card_type == 11:
                    sub_cards = card.get('card_group', [])
                    logger.info(f'card_type=11，包含 {len(sub_cards)} 个子 card')
                    for sub_card in sub_cards:
                        if sub_card.get('card_type') == 9:
                            mblog = sub_card.get('mblog', {})
                            post = self.parse_post(mblog)
                            if post:
                                post_time = post['created_at']
                                
                                if not post_time:
                                    scan_records.append({
                                        'page': page,
                                        'card_type': '11→9',
                                        'weibo_id': post['id'],
                                        'created_at': 'N/A',
                                        'is_original': 'N/A',
                                        'is_collected': False,
                                        'reason': '时间解析失败',
                                        'weibo_url': f'https://m.weibo.cn/detail/{post["id"]}'
                                    })
                                    continue
                                
                                post_date = post_time.split(' ')[0] if ' ' in post_time else post_time
                                is_original = post['is_original'] == 1
                                
                                logger.info(f'子微博 {post["id"]}: 时间={post_date}, 原创={is_original}')
                                
                                if since_date and post_date >= since_date:
                                    page_has_any_after_since = True
                                
                                reason = ''
                                is_collected = True
                                
                                if not is_original:
                                    reason = '不是原创微博'
                                    is_collected = False
                                elif since_date and post_date < since_date:
                                    reason = f'早于时间起点 {since_date}'
                                    is_collected = False
                                elif until_date and post_date > until_date:
                                    reason = f'晚于时间终点 {until_date}'
                                    is_collected = False
                                
                                if is_collected:
                                    posts.append(post)
                                    logger.info(f'子微博 {post["id"]} 已添加到采集列表')
                                else:
                                    logger.info(f'子微博 {post["id"]} {reason}，跳过')
                                
                                scan_records.append({
                                    'page': page,
                                    'card_type': '11→9',
                                    'weibo_id': post['id'],
                                    'created_at': post_date,
                                    'is_original': is_original,
                                    'is_collected': is_collected,
                                    'reason': reason,
                                    'weibo_url': f'https://m.weibo.cn/detail/{post["id"]}'
                                })
                
                elif card_type == 156:
                    mblog = card.get('mblog', {})
                    if mblog:
                        post = self.parse_post(mblog)
                        if post:
                            post_time = post['created_at']
                            
                            if not post_time:
                                scan_records.append({
                                    'page': page,
                                    'card_type': '156',
                                    'weibo_id': post['id'],
                                    'created_at': 'N/A',
                                    'is_original': 'N/A',
                                    'is_collected': False,
                                    'reason': '时间解析失败',
                                    'weibo_url': f'https://m.weibo.cn/detail/{post["id"]}'
                                })
                                continue
                            
                            post_date = post_time.split(' ')[0] if ' ' in post_time else post_time
                            is_original = post['is_original'] == 1
                            
                            logger.info(f'card156微博 {post["id"]}: 时间={post_date}, 原创={is_original}')
                            
                            if since_date and post_date >= since_date:
                                page_has_any_after_since = True
                            
                            reason = ''
                            is_collected = True
                            
                            if not is_original:
                                reason = '不是原创微博'
                                is_collected = False
                            elif since_date and post_date < since_date:
                                reason = f'早于时间起点 {since_date}'
                                is_collected = False
                            elif until_date and post_date > until_date:
                                reason = f'晚于时间终点 {until_date}'
                                is_collected = False
                            
                            if is_collected:
                                posts.append(post)
                                logger.info(f'card156微博 {post["id"]} 已添加到采集列表')
                            else:
                                logger.info(f'card156微博 {post["id"]} {reason}，跳过')
                            
                            scan_records.append({
                                'page': page,
                                'card_type': '156',
                                'weibo_id': post['id'],
                                'created_at': post_date,
                                'is_original': is_original,
                                'is_collected': is_collected,
                                'reason': reason,
                                'weibo_url': f'https://m.weibo.cn/detail/{post["id"]}'
                            })
                    else:
                        logger.info(f'card_type=156 无 mblog 数据')
                        scan_records.append({
                            'page': page,
                            'card_type': '156',
                            'weibo_id': 'N/A',
                            'created_at': 'N/A',
                            'is_original': 'N/A',
                            'is_collected': False,
                            'reason': '无 mblog 数据',
                            'weibo_url': 'N/A'
                        })
                else:
                    logger.info(f'未处理的 card_type={card_type}')
                    scan_records.append({
                        'page': page,
                        'card_type': card_type,
                        'weibo_id': 'N/A',
                        'created_at': 'N/A',
                        'is_original': 'N/A',
                        'is_collected': False,
                        'reason': f'未处理的card_type={card_type}',
                        'weibo_url': 'N/A'
                    })
            
            logger.info(f'用户 {uid} 第 {page} 页完成，已采集 {len(posts)} 条微博')
            
            if not page_has_any_after_since and since_date:
                logger.info(f'用户 {uid} 第 {page} 页无时间范围内微博，停止采集')
                break
            
            page += 1
        
        logger.info(f'用户 {uid} 采集完成，共 {len(posts)} 条原创微博')
        return posts, scan_records
