import json
import os
import logging
from config import CHECKPOINT_POSTS_FILE, CHECKPOINT_COMMENTS_FILE

logger = logging.getLogger(__name__)

class CheckpointManager:
    def __init__(self):
        self.posts_checkpoint = {}
        self.comments_checkpoint = {}
        self._load_checkpoints()
    
    def _load_checkpoints(self):
        if os.path.exists(CHECKPOINT_POSTS_FILE):
            try:
                with open(CHECKPOINT_POSTS_FILE, 'r', encoding='utf-8') as f:
                    self.posts_checkpoint = json.load(f)
            except Exception as e:
                logger.error(f'加载帖子断点文件失败: {e}')
        
        if os.path.exists(CHECKPOINT_COMMENTS_FILE):
            try:
                with open(CHECKPOINT_COMMENTS_FILE, 'r', encoding='utf-8') as f:
                    self.comments_checkpoint = json.load(f)
            except Exception as e:
                logger.error(f'加载评论断点文件失败: {e}')
    
    def save_post_checkpoint(self, uid, latest_time):
        self.posts_checkpoint[uid] = latest_time
        self._save_posts_checkpoint()
    
    def _save_posts_checkpoint(self):
        try:
            with open(CHECKPOINT_POSTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.posts_checkpoint, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f'保存帖子断点失败: {e}')
    
    def get_post_checkpoint(self, uid):
        return self.posts_checkpoint.get(uid, None)
    
    def save_comment_checkpoint(self, post_id, max_id):
        self.comments_checkpoint[str(post_id)] = max_id
        self._save_comments_checkpoint()
    
    def _save_comments_checkpoint(self):
        try:
            with open(CHECKPOINT_COMMENTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.comments_checkpoint, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f'保存评论断点失败: {e}')
    
    def get_comment_checkpoint(self, post_id):
        return self.comments_checkpoint.get(str(post_id), 0)
    
    def has_comment_checkpoint(self, post_id):
        return str(post_id) in self.comments_checkpoint