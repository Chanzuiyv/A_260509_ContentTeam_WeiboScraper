# 📱 虚拟偶像成员微博采集与整理工具（逐声计划 · 内容组）

> 采集 LASER / MANTA 九位虚拟偶像成员微博账号 2020 年以来的**原创微博原文**及成员互评评论，支持登录态 Cookie、断点续爬、增量更新、反爬轮换与评论楼中楼筛选；最终按"成员 → 年份"自动整理为 Excel 语料库（9 人 × 7 年，共 **58 个工作簿、1953 条微博**）。
>
> 关键词：`Python` `requests` `BeautifulSoup` `微博移动端 API` `Cookie 登录态` `断点续爬` `增量采集` `pandas/openpyxl`

---

## 一、项目背景 & 目标

"逐声计划"除团综音频字幕外，还需要收集角色在**社交媒体上的公开发言**作为人物语料：成员微博能反映角色设定、成员互动（互评评论）与粉丝运营节奏。人工逐页复制成本高且难以持续更新，本工具解决：

1. **批量采集**——内置九位成员的微博 UID，一次配置即可抓取全部账号的原创微博；
2. **只收原创、按时间窗过滤**——自动跳过转发（retweet），可限定起止日期；
3. **成员互动评论提取**——不只抓评论，还通过 UID 过滤 + 回复链追踪，只保留九位成员**自己发的评论及其上下文对话**，过滤海量粉丝评论；
4. **可持续运行**——长任务支持断点续爬、增量模式（只抓上次之后的新微博）、随机延时、多 UA / 多 Cookie 轮换、失败重试；
5. **可直接交付的语料格式**——按成员和年份分簿整理成 Excel，非技术同学可直接使用。

---

## 二、使用工具

- **Python 3**（Windows 环境）
- 第三方依赖：

| 库 | 用途 |
|---|---|
| `requests` | 会话管理与 HTTP 请求 |
| `beautifulsoup4` | 微博/评论 HTML 正文清洗 |
| `pandas` | CSV 读取、按年份拆分、导出 Excel |
| `openpyxl` | Excel 读写与表格批处理 |
| 标准库 | `argparse` / `csv` / `json` / `logging` / `random` / `re` / `datetime` |

安装：

```bash
pip install requests beautifulsoup4 pandas openpyxl
```

---

## 三、数据来源与采集对象

- **目标站点**：微博移动端站点 `m.weibo.cn` 的公开 JSON 接口（无需 Selenium/浏览器驱动）；
- **九位采集对象**（UID 内置在 `config.py`）：

| 团体 | 成员 |
|---|---|
| LASER（4 人） | 顾子尧、林致、乔殊、夏予扬 |
| MANTA（5 人） | 柏闻、江恪、季少一、许向安、许向宁 |

接口与产物：

| 数据 | 接口 |
|---|---|
| 用户微博列表 | `GET /api/container/getIndex?type=uid&value={uid}&containerid=107603{uid}&page=N` |
| 长微博全文 | `GET /statuses/extend?id={微博id}` |
| 评论列表 | `GET /comments/hotflow?id={id}&mid={id}&max_id=...` |
| 楼中楼回复 | `GET /comments/hotFlowChild?cid={父评论id}&max_id=...` |

> 采集范围仅为公开可见内容，需登录态的接口以使用者本人 Cookie 访问；请遵守微博相关条款，控制频率、勿商用、勿传播个人隐私信息。

---

## 四、处理流程

```
main.py 交互式启动
  │  选模式（仅微博 / 仅评论 / 微博+评论）→ 选成员 → 配 Cookie → 起止日期 → 增量？
  ▼
PostParser 逐页翻微博列表（card_type 9 / 11 / 156 三种卡片全适配）
  │  · 转发微博剔除（retweeted_status）· 日期窗口过滤
  │  · isLongText 时调 extend 接口取全文 · HTML→纯文本 · 提取配图/视频 URL
  ▼
data/{成员名}.csv 增量追加（按微博 id 去重）
scan_details/{成员}_scan_details.csv 记录每条微博"采/未采+原因"（可审计）
  │
  ▼（模式 3 时）
CommentParser 抓评论 + 楼中楼
  │  九成员 UID 白名单：保留成员评论，并沿父评论链/子回复链补全对话上下文
  ▼
data/member_comments.csv（按 comment_id 去重）
  │
  ▼ 断点：checkpoint_posts.json（成员→最新微博时间）/ checkpoint_comments.json（微博→max_id）
结束时全量去重；后续用表格处理代码按"成员/年份"导出 Excel
```

### 关键机制

- **反爬策略**：8 个移动端 UA 随机轮换、每次请求随机间隔 **4–8 秒**、失败最多重试 3 次（间隔指数退避 1/10/100 秒）、命中 403/418/429/432 或响应中出现"验证码/安全验证"时自动切换下一个 Cookie；
- **断点与增量**：每个成员记录最新微博时间，增量模式下从上次位置继续；评论按 `max_id` 游标翻页（单条微博最多 500 页），中断重跑不重复；
- **时间格式兼容**：处理"x 分钟前 / x 小时前 / 昨天 / 短日期 / 英文标准时间"等微博全部常见格式，统一为 `YYYY-MM-DD HH:MM:SS`；
- **评论对话筛选**：先找九位成员发出的评论，再 BFS 追溯其回复的父评论、以及成员后续的楼中楼回复——最终保留的是"成员参与的对话片段"，而非全部粉丝评论；
- **运行可观测**：彩色控制台日志 + `logs/weibo_spider.log` 全量文件日志；扫描详情 CSV 逐条标注跳过原因（非原创 / 早于起点 / 晚于终点）。

### 产出数据字段

微博 CSV（每成员一个文件，11 列）：`screen_name, id, created_at, text, is_original, reposts_count, comments_count, attitudes_count, pics, videos, url`
评论 CSV（10 列）：`post_id, comment_id, comment_user_name, comment_user_id, comment_text, comment_created_at, comment_like_count, is_reply, reply_to_comment_id, comment_pics`

---

## 五、运行方式

### 1. 环境准备

```bash
pip install requests beautifulsoup4 pandas openpyxl
```

### 2. 获取微博 Cookie（必需）

1. 用 Chrome/Edge 登录 [m.weibo.cn](https://m.weibo.cn/)；
2. 按 `F12` 打开开发者工具 → **Network（网络）** 面板，刷新页面；
3. 点任意一个发往 `m.weibo.cn` 的请求，在 **Request Headers** 中找到 `Cookie:` 字段，复制整行值；
4. 在爬虫代码目录新建 `cookies.txt`，把 Cookie 粘贴为一行（支持多行存放多个 Cookie，程序会在被拦截时自动轮换；`#` 开头为注释）。

> 也可以直接运行程序，在交互提示"请输入微博 Cookie"处粘贴，程序会自动写入 `cookies.txt`。Cookie 等同于登录凭证，**请勿提交到 Git 或分享给他人**；失效后重新获取即可。

### 3. 运行爬虫

在 `代码/爬虫代码/` 目录下执行（程序以相对路径读取同目录 `cookies.txt` 与配置）：

```bash
python main.py
```

按交互菜单依次选择：采集模式 → 成员序号（如 `1 3 5`，或 `all`）→ 是否使用已有 Cookie → 起止日期（默认 2020-01-01 至今）→ 是否增量模式。模式 2 可在已有微博 CSV 的基础上单独补采评论。

### 4. 整理为语料 Excel

采集完成后运行表格处理脚本（路径硬编码，需先改为本机 data 目录）：

```bash
python ../表格处理代码/process_weibo_data.py
```

脚本按"成员名/年份/年份年微博.xlsx"导出，列为：成员名字、发帖日期、微博原文、是否有图片、图片、微博链接、是否有评论、评论表格链接，并按微博链接去重。

`process_excel.py` 为可选的评论表批处理工具（删除 `post_id/comment_id/comment_like_count` 内部列、把 pics 列替换为 √/❌ 标记），支持命令行传文件或目录：

```bash
python process_excel.py <xlsx文件或目录>
```

---

## 六、处理结果

`最终结果/微博原文/成员微博整理.zip` 为真实采集交付物，解压后结构：

```
成员微博整理/
├── 顾子尧/2020/2020年微博.xlsx … 2026/2026年微博.xlsx   （7 个簿）
├── 林致/ 乔殊/ 夏予扬/                                  （各 7 个簿）
└── 柏闻/ 江恪/ 季少一/ 许向安/ 许向宁/                   （各 6 个簿）
```

| 指标 | 数值 |
|---|---|
| 成员数 | 9 人 |
| Excel 工作簿 | 58 个（2020 年仅 LASER 4 人有账号内容，2021 年起 9 人齐全） |
| 微博原文总条数 | **1953 条** |
| 时间跨度 | 2020 – 2026 年 |
| 每簿列数 | 8 列（成员/日期/原文/有无图片/图片链接/微博链接/评论相关占位列） |

---

## 七、文件目录说明

```
A_260509_内容组_微博爬取/
├── README.md
├── 代码/
│   ├── 爬虫代码/
│   │   ├── main.py               ← 入口：交互式菜单、CSV 写出/去重、调度全流程
│   │   ├── config.py             ← 9 位成员 UID、UA 池、延时/重试阈值、目录与文件配置
│   │   ├── session_manager.py    ← requests 会话、Cookie/UA 轮换、封站检测与重试
│   │   ├── post_parser.py        ← 微博列表翻页、卡片解析、长微博、原创与日期过滤
│   │   ├── comment_parser.py     ← 评论/楼中楼抓取、成员 UID 白名单与对话链筛选
│   │   └── checkpoint.py         ← 微博/评论断点 JSON 读写
│   └── 表格处理代码/
│       ├── process_weibo_data.py ← CSV → 按成员/年份拆分的 Excel 语料
│       ├── process_excel.py      ← 评论 Excel 批处理（删内部列、图片列标记），argparse CLI
│       └── test_output.py        ← 导出结果抽查脚本（读回 Excel 打印样例）
└── 最终结果/
    └── 微博原文/
        └── 成员微博整理.zip       ← 交付语料：9 人 × 7 年，58 簿 1953 条
```

> 运行期生成的 `data/`（CSV）、`logs/`、`scan_details/`、`checkpoint_*.json`、`cookies.txt` 均在运行目录自动创建，仓库不包含这些文件，也**不要把含登录凭证的 `cookies.txt` 上传到公开仓库**（建议加入 `.gitignore`）。

---

## 八、注意事项与已知局限

- **登录态依赖**：游客模式下接口返回受限，评论抓取基本需要有效 Cookie；Cookie 过期或账号触发风控时需更换；
- **硬编码路径**：`process_weibo_data.py` / `process_excel.py` 默认路径为作者本机目录（`C:\Users\ThinkPad\Desktop\weibopachong\...`），换机器需修改；
- **采集边界**：仅采集原创微博（转发只记为跳过）；列表翻页上限 100 页、评论单条上限 500 页，超出部分不抓；
- **增量语义**：增量起点取本地上次记录的最新微博时间，修改过历史微博等情况不会被回溯；
- **接口时效**：微博移动端接口与反爬策略可能随官方调整而变化，代码基于 2026 年的接口结构，失效时需更新卡片类型与接口参数；
- 采集内容版权归原作者所有，本工具仅用于个人学习与语料研究。

---

> 📌 技术要点小结：这个项目的难点不在"发请求"，而在**长任务工程化**与**信噪比控制**——用断点 + 增量 + 重试 + UA/Cookie 轮换保证几天的采集任务可中断、可恢复；用 card_type 适配、长微博补全、相对时间归一化保证数据完整；更重要的是评论侧的"成员 UID 白名单 + 父子回复链 BFS"，把上万条粉丝噪音过滤成真正有研究价值的成员互动对话语料。
