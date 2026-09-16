import argparse
import logging
import os
import csv
import sys
from datetime import datetime
from config import LOG_DIR, LOG_FILE, LOG_FORMAT, DATA_DIR, TARGET_UIDS, COOKIES_FILE, SCAN_DETAILS_DIR
from session_manager import SessionManager
from checkpoint import CheckpointManager
from post_parser import PostParser
from comment_parser import CommentParser

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[95m',
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        record.msg = f"{color}{record.msg}{reset}"
        return super().format(record)

def save_scan_details(screen_name, scan_records):
    """保存扫描详情到CSV，记录每一条微博的处理状态"""
    os.makedirs(SCAN_DETAILS_DIR, exist_ok=True)
    filename = os.path.join(SCAN_DETAILS_DIR, f'{screen_name}_scan_details.csv')
    
    headers = [
        'page', 'card_type', 'weibo_id', 'created_at', 'is_original', 
        'is_collected', 'reason', 'weibo_url'
    ]
    
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        
        for record in scan_records:
            writer.writerow(record)

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE) if os.path.dirname(LOG_FILE) else '.', exist_ok=True)
    
    formatter = logging.Formatter(LOG_FORMAT)
    colored_formatter = ColoredFormatter(LOG_FORMAT)
    
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(colored_formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def save_posts_to_csv(posts, screen_name):
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = os.path.join(DATA_DIR, f'{screen_name}.csv')
    
    headers = ['screen_name', 'id', 'created_at', 'text', 'is_original', 
               'reposts_count', 'comments_count', 'attitudes_count', 'pics', 'videos', 'url']
    
    existing_ids = set()
    existing_rows = []
    
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_ids.add(row['id'])
                existing_rows.append(row)
    
    new_posts = []
    for post in posts:
        if post['id'] not in existing_ids:
            new_posts.append(post)
    
    if new_posts:
        all_rows = existing_rows + new_posts
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)
        logger = logging.getLogger(__name__)
        logger.info(f'写入 {len(new_posts)} 条新微博到 {screen_name}.csv，跳过 {len(posts)-len(new_posts)} 条重复微博')

def save_comments_to_csv(comments):
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = os.path.join(DATA_DIR, 'member_comments.csv')
    
    headers = ['post_id', 'comment_id', 'comment_user_name', 'comment_user_id', 
               'comment_text', 'comment_created_at', 'comment_like_count', 
               'is_reply', 'reply_to_comment_id', 'comment_pics']
    
    existing_ids = set()
    existing_rows = []
    
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['comment_id'] not in existing_ids:
                    existing_ids.add(row['comment_id'])
                    existing_rows.append(row)
    
    comments_seen = set()
    new_comments = []
    for comment in comments:
        comment_id = comment['comment_id']
        if comment_id not in comments_seen and comment_id not in existing_ids:
            comments_seen.add(comment_id)
            new_comments.append(comment)
    
    if new_comments:
        all_rows = existing_rows + new_comments
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)
        logger = logging.getLogger(__name__)
        logger.info(f'写入 {len(new_comments)} 条新评论到 member_comments.csv，跳过 {len(comments)-len(new_comments)} 条重复评论')

def deduplicate_all_posts_csv():
    logger = logging.getLogger(__name__)
    logger.info('开始清理所有微博文件中的重复数据...')
    
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv') and not f.startswith('member_comments')]
    
    for csv_file in csv_files:
        filename = os.path.join(DATA_DIR, csv_file)
        headers = ['screen_name', 'id', 'created_at', 'text', 'is_original', 
                   'reposts_count', 'comments_count', 'attitudes_count', 'pics', 'videos', 'url']
        
        existing_ids = set()
        unique_rows = []
        
        with open(filename, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['id'] not in existing_ids:
                    existing_ids.add(row['id'])
                    unique_rows.append(row)
        
        original_count = sum(1 for _ in open(filename, 'r', encoding='utf-8-sig')) - 1
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in unique_rows:
                writer.writerow(row)
        
        logger.info(f'清理 {csv_file}：原 {original_count} 条，去重后 {len(unique_rows)} 条，删除 {original_count - len(unique_rows)} 条重复')

def deduplicate_comments_csv():
    logger = logging.getLogger(__name__)
    filename = os.path.join(DATA_DIR, 'member_comments.csv')
    
    if not os.path.exists(filename):
        return
    
    logger.info('开始清理评论文件中的重复数据...')
    
    headers = ['post_id', 'comment_id', 'comment_user_name', 'comment_user_id', 
               'comment_text', 'comment_created_at', 'comment_like_count', 
               'is_reply', 'reply_to_comment_id', 'comment_pics']
    
    existing_ids = set()
    unique_rows = []
    
    with open(filename, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['comment_id'] not in existing_ids:
                existing_ids.add(row['comment_id'])
                unique_rows.append(row)
    
    original_count = sum(1 for _ in open(filename, 'r', encoding='utf-8-sig')) - 1
    
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in unique_rows:
            writer.writerow(row)
    
    logger.info(f'清理 member_comments.csv：原 {original_count} 条，去重后 {len(unique_rows)} 条，删除 {original_count - len(unique_rows)} 条重复')

def crawl_posts(selected_uids, since_date, until_date, incremental, mode):
    session = SessionManager()
    checkpoint = CheckpointManager()
    post_parser = PostParser(session)
    comment_parser = CommentParser(session)
    
    logger = logging.getLogger(__name__)
    
    for screen_name, uid in selected_uids.items():
        since = since_date
        if incremental:
            last_time = checkpoint.get_post_checkpoint(uid)
            if last_time:
                since = last_time
                logger.info(f'增量模式: 用户 {screen_name} 上次采集到 {last_time}，将从该时间继续')
        
        logger.info(f'开始采集 {screen_name}，时间范围：{since} ~ {until_date}')
        
        posts, scan_records = post_parser.fetch_user_posts(uid, since, until_date)
        
        # 保存扫描详情
        save_scan_details(screen_name, scan_records)
        logger.info(f'扫描详情已保存到 {SCAN_DETAILS_DIR}/{screen_name}_scan_details.csv')
        
        if posts:
            save_posts_to_csv(posts, screen_name)
            
            latest_time = posts[0]['created_at']
            checkpoint.save_post_checkpoint(uid, latest_time)
            
            logger.info(f'{screen_name} 采集完成，共 {len(posts)} 条微博')
            
            if mode == 3:
                logger.info(f'开始采集 {screen_name} 的评论...')
                for post in posts:
                    if post['comments_count'] > 0:
                        comments, max_id = comment_parser.fetch_comments(post['id'])
                        if comments:
                            save_comments_to_csv(comments)
                        checkpoint.save_comment_checkpoint(post['id'], max_id)
            else:
                logger.info(f'模式为仅采集微博，跳过评论采集')

def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                    微博爬虫 v1.0                               ║
║                  交互式采集工具                                 ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def select_users():
    print("\n📋 可选用户列表：")
    user_list = list(TARGET_UIDS.items())
    for i, (name, uid) in enumerate(user_list, 1):
        print(f"  {i}. {name} (UID: {uid})")
    
    print("\n请输入要采集的用户序号（用空格分隔，如: 1 3 5，输入 all 选择全部）：")
    while True:
        choice = input("➡️ 输入选择: ").strip()
        if choice.lower() == 'all':
            return TARGET_UIDS
        try:
            indices = [int(x.strip()) - 1 for x in choice.split()]
            selected = {}
            for idx in indices:
                if 0 <= idx < len(user_list):
                    name, uid = user_list[idx]
                    selected[name] = uid
                else:
                    print(f"❌ 序号 {idx + 1} 超出范围，请重新输入")
                    break
            else:
                if selected:
                    print(f"\n✅ 已选择 {len(selected)} 个用户")
                    for name in selected:
                        print(f"   - {name}")
                    return selected
                else:
                    print("❌ 请至少选择一个用户")
        except ValueError:
            print("❌ 输入格式错误，请输入数字序号")

def input_cookies():
    print("\n🍪 Cookie 设置")
    print("提示：如果已有 cookies.txt 文件，可直接回车跳过")
    
    use_existing = input("是否使用现有 cookies.txt？(y/n): ").strip().lower()
    if use_existing == 'y':
        if os.path.exists(COOKIES_FILE):
            print("✅ 使用现有 cookies.txt")
            return
        else:
            print("❌ cookies.txt 文件不存在，请输入 Cookie")
    
    print("\n请输入微博 Cookie（从浏览器获取）：")
    cookie = input("➡️ Cookie: ").strip()
    
    if cookie:
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write(cookie)
        print("✅ Cookie 已保存到 cookies.txt")
    else:
        print("⚠️ 未输入 Cookie，将以游客模式运行")

def input_date_range():
    print("\n📅 日期范围设置")
    
    default_since = '2020-01-01'
    default_until = datetime.now().strftime('%Y-%m-%d')
    
    since = input(f"开始日期 (YYYY-MM-DD) [默认: {default_since}]: ").strip() or default_since
    until = input(f"结束日期 (YYYY-MM-DD) [默认: {default_until}]: ").strip() or default_until
    
    try:
        datetime.strptime(since, '%Y-%m-%d')
        datetime.strptime(until, '%Y-%m-%d')
    except ValueError:
        print("❌ 日期格式错误，使用默认值")
        since = default_since
        until = default_until
    
    print(f"✅ 日期范围: {since} ~ {until}")
    return since, until

def input_incremental():
    print("\n🔄 增量模式")
    incremental = input("是否启用增量模式？(y/n) [默认: n]: ").strip().lower() == 'y'
    if incremental:
        print("✅ 已启用增量模式")
    return incremental

def select_mode():
    print("\n🎯 选择采集模式")
    print("  1. 采集微博原文")
    print("  2. 采集评论（需先采集微博）")
    print("  3. 同时采集微博和评论")
    
    while True:
        choice = input("➡️ 输入选择 (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            return int(choice)
        print("❌ 输入错误，请输入 1、2 或 3")

def crawl_comments_from_file(file_path):
    session = SessionManager()
    checkpoint = CheckpointManager()
    comment_parser = CommentParser(session)
    
    if not os.path.exists(file_path):
        logging.error(f'文件 {file_path} 不存在')
        return
    
    post_ids = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'id' in row:
                post_ids.append(row['id'])
    
    logger = logging.getLogger(__name__)
    logger.info(f'从文件 {file_path} 读取到 {len(post_ids)} 条微博ID')
    
    for post_id in post_ids:
        if checkpoint.has_comment_checkpoint(post_id):
            max_id = checkpoint.get_comment_checkpoint(post_id)
        else:
            max_id = 0
        
        comments, new_max_id = comment_parser.fetch_comments(post_id, max_id)
        
        if comments:
            save_comments_to_csv(comments)
        
        checkpoint.save_comment_checkpoint(post_id, new_max_id)

def main():
    print_banner()
    
    mode = select_mode()
    
    if mode == 2:
        input_cookies()
        
        print("\n📁 选择微博数据文件")
        os.makedirs(DATA_DIR, exist_ok=True)
        files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv') and not f.startswith('member_comments')]
        if not files:
            print("❌ 未找到微博数据文件，请先采集微博")
            return
        
        print("可用文件：")
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f}")
        
        while True:
            choice = input("➡️ 输入文件序号: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(files):
                    file_path = os.path.join(DATA_DIR, files[idx])
                    break
                print("❌ 序号超出范围")
            except ValueError:
                print("❌ 输入格式错误")
        
        setup_logging()
        
        try:
            crawl_comments_from_file(file_path)
            print("\n🎉 评论采集完成！")
            print(f"📁 数据已保存到 {DATA_DIR}/member_comments.csv")
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断")
        return
    
    selected_uids = select_users()
    input_cookies()
    since_date, until_date = input_date_range()
    incremental = input_incremental()
    
    print("\n" + "="*60)
    print("🚀 开始采集任务")
    print(f"   模式: {'仅微博' if mode == 1 else '微博+评论'}")
    print(f"   用户: {', '.join(selected_uids.keys())}")
    print(f"   时间范围: {since_date} ~ {until_date}")
    print(f"   增量模式: {'开启' if incremental else '关闭'}")
    print("="*60 + "\n")
    
    setup_logging()
    
    try:
        crawl_posts(selected_uids, since_date, until_date, incremental, mode)
        print("\n🎉 采集任务完成！")
        print(f"📁 数据已保存到 {DATA_DIR}/ 目录")
        print(f"📝 日志已保存到 {LOG_FILE}")
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断，采集任务已停止")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"采集过程中发生错误: {e}", exc_info=True)
        print(f"\n❌ 采集过程中发生错误: {e}")
    
    # 最后去重
    try:
        if os.path.exists(DATA_DIR):
            print("\n🧹 开始清理重复数据...")
            deduplicate_all_posts_csv()
            deduplicate_comments_csv()
            print("✅ 重复数据清理完成！")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"清理重复数据时发生错误: {e}", exc_info=True)
        print(f"❌ 清理重复数据时发生错误: {e}")

if __name__ == '__main__':
    main()