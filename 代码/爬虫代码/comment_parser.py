import json
import re
import logging
from bs4 import BeautifulSoup
from config import COMMENT_MAX_PAGES, TARGET_UIDS

logger = logging.getLogger(__name__)

class CommentParser:
    def __init__(self, session_manager):
        self.session = session_manager
        self.target_uids = set(TARGET_UIDS.values())
    
    def _extract_comment_text(self, text):
        if not text:
            return ''
        
        try:
            soup = BeautifulSoup(text, 'html.parser')
            
            text = soup.get_text(separator=' ')
            
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception as e:
            logger.error(f'解析评论文本失败: {e}')
            return text
    
    def _extract_comment_pics(self, comment_data):
        pics = []
        if 'pics' in comment_data and comment_data['pics']:
            for pic in comment_data['pics']:
                if 'large' in pic and 'url' in pic['large']:
                    pics.append(pic['large']['url'])
                elif 'url' in pic:
                    pics.append(pic['url'])
        return ','.join(pics)
    
    def _parse_comment(self, comment_data, post_id, is_reply=False, parent_comment_id=''):
        user = comment_data.get('user', {})
        user_id = str(user.get('id', ''))
        
        return {
            'post_id': str(post_id),
            'comment_id': str(comment_data.get('id', '')),
            'comment_user_name': user.get('screen_name', ''),
            'comment_user_id': user_id,
            'comment_text': self._extract_comment_text(comment_data.get('text', '')),
            'comment_created_at': comment_data.get('created_at', ''),
            'comment_like_count': comment_data.get('like_count', 0),
            'is_reply': 1 if is_reply else 0,
            'reply_to_comment_id': str(parent_comment_id) if is_reply else '',
            'comment_pics': self._extract_comment_pics(comment_data)
        }
    
    def fetch_comments(self, post_id, max_id=0):
        all_comments = []
        page = 0
        current_max_id = max_id
        
        logger.info(f'正在抓取微博 {post_id} 的评论...')
        
        while page < COMMENT_MAX_PAGES:
            url = f'https://m.weibo.cn/comments/hotflow?id={post_id}&mid={post_id}&max_id={current_max_id}&max_id_type=0'
            response = self.session.get(url)
            
            if not response:
                break
            
            try:
                logger.debug(f'微博 {post_id} 评论响应: {response.text[:500]}')
                data = response.json()
            except json.JSONDecodeError:
                logger.error(f'解析微博 {post_id} 评论失败，响应不是JSON: {response.text[:500]}')
                break
            
            if data.get('ok') != 1:
                msg = data.get('msg', '未知错误')
                if msg == '未知错误':
                    msg = '可能是权限限制或内容限制'
                logger.warning(f'获取微博 {post_id} 评论失败: {msg}')
                break
            
            comment_list = data.get('data', {}).get('data', [])
            
            if not comment_list:
                break
            
            for comment in comment_list:
                parsed = self._parse_comment(comment, post_id)
                if parsed:
                    all_comments.append(parsed)
                
                has_child = comment.get('total_number', 0) > 0
                if has_child:
                    child_comments = self._fetch_child_comments(post_id, comment.get('id', ''))
                    all_comments.extend(child_comments)
            
            current_max_id = data.get('data', {}).get('max_id', 0)
            if current_max_id == 0:
                break
            
            page += 1
        
        filtered_comments = self._filter_target_comments(all_comments)
        
        logger.info(f'微博 {post_id} 评论抓取完成，找到 {len(filtered_comments)} 条目标评论')
        return filtered_comments, current_max_id
    
    def _fetch_child_comments(self, post_id, parent_comment_id):
        child_comments = []
        page = 0
        max_id = 0
        
        while page < COMMENT_MAX_PAGES:
            url = f'https://m.weibo.cn/comments/hotFlowChild?cid={parent_comment_id}&max_id={max_id}&max_id_type=0'
            response = self.session.get(url)
            
            if not response:
                break
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.error(f'解析微博 {post_id} 子评论失败')
                break
            
            if data.get('ok') != 1:
                break
            
            response_data = data.get('data', {})
            if isinstance(response_data, list):
                child_list = response_data
                max_id = 0
            else:
                child_list = response_data.get('data', [])
                max_id = response_data.get('max_id', 0)
            
            if not child_list:
                break
            
            for child in child_list:
                parsed = self._parse_comment(child, post_id, is_reply=True, parent_comment_id=parent_comment_id)
                if parsed:
                    child_comments.append(parsed)
            
            if max_id == 0:
                break
            
            page += 1
        
        return child_comments
    
    def _filter_target_comments(self, all_comments):
        comment_id_to_comment = {c['comment_id']: c for c in all_comments}
        target_comment_ids = set()
        
        queue = []
        
        for comment in all_comments:
            user_id = comment.get('comment_user_id', '')
            if user_id in self.target_uids:
                target_comment_ids.add(comment['comment_id'])
                
                if comment.get('reply_to_comment_id') and comment['reply_to_comment_id'] not in target_comment_ids:
                    queue.append(comment['reply_to_comment_id'])
        
        while queue:
            parent_id = queue.pop(0)
            if parent_id in target_comment_ids:
                continue
            
            target_comment_ids.add(parent_id)
            
            if parent_id in comment_id_to_comment:
                parent_comment = comment_id_to_comment[parent_id]
                if parent_comment.get('reply_to_comment_id') and parent_comment['reply_to_comment_id'] not in target_comment_ids:
                    queue.append(parent_comment['reply_to_comment_id'])
        
        reply_to_map = {}
        for comment in all_comments:
            reply_to = comment.get('reply_to_comment_id')
            if reply_to:
                if reply_to not in reply_to_map:
                    reply_to_map[reply_to] = []
                reply_to_map[reply_to].append(comment['comment_id'])
        
        queue = list(target_comment_ids.copy())
        while queue:
            current_id = queue.pop(0)
            if current_id in reply_to_map:
                for reply_id in reply_to_map[current_id]:
                    if reply_id not in target_comment_ids:
                        reply_comment = comment_id_to_comment.get(reply_id)
                        if reply_comment:
                            reply_user_id = reply_comment.get('comment_user_id', '')
                            if reply_user_id in self.target_uids:
                                target_comment_ids.add(reply_id)
                                queue.append(reply_id)
        
        filtered = [c for c in all_comments if c['comment_id'] in target_comment_ids]
        
        return filtered