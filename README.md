# maimaiDX WeChat Bot 🎮

基于 [WeChatFerry](https://github.com/lich0821/WeChatFerry) + [maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) 的**微信舞萌 DX 查分机器人**。

支持私聊、群聊（自动 @），查分结果以图片返回。

## 特性

- ✅ 接入个人微信号，支持私聊 + 群聊
- ✅ B50 查分（Diving-Fish / LXNS 双数据源自动降级）
- ✅ 用户绑定系统（每人绑定自己的查分器账号 + Token）
- ✅ 歌曲搜索（支持别名）、随机推荐
- ✅ Pillow 图片渲染（B50 成绩图直接发微信）
- ✅ 纯 Python，本地跑无外部依赖

---

## 快速开始

### 环境

- **Windows** 10/11 或 Windows Server 2019+
- Python 3.11+
- 微信 **3.9.6.x**（与 wcferry v39.6.0.0 匹配）
- 一个微信小号（别用主号，有封号风险）

### 1. 安装依赖

```powershell
# 装 Python 3.11 和 Git（以 choco 为例）
choco install python311 git -y

# 克隆项目
git clone https://github.com/Yunlk/maimai-wechat-bot.git
cd maimai-wechat-bot

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 准备静态资源

从原始 [maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) 项目的 `static/` 目录复制过来：

```powershell
# 假设原始项目在 ../maimaiDX
robocopy ..\maimaiDX\static .\static /E
```

必需文件结构：

```
static/
├── font/                          # 字体文件
├── mai/
│   ├── pic/PRISM_PLUS/            # B50 主题素材
│   ├── cover/                     # 曲绘
│   ├── plate/                     # 姓名框
│   ├── shougou/                   # 称号
│   ├── icon/                      # UI 图标
│   ├── plate_version/
│   ├── plate_table/
│   └── rating_table/
└── data/                          # 运行时数据（自动生成）
```

### 3. 配置

```powershell
copy .env.example .env
notepad .env
```

最少要填：

```ini
# 水鱼查分器 Token（查 B50 需要，找水鱼申请）
DIVINGFISH_TOKEN=你的token

# 落雪查分器（可选）
LXNS_DEV_TOKEN=
```

### 4. 启动

```powershell
python -m app.main
```

首次启动会自动弹出微信登录窗口，手机扫码确认。

---

## 使用

在微信里给机器人发指令：

| 指令 | 说明 |
|------|------|
| `/bind <用户名> [token]` | 绑定水鱼查分器 |
| `/unbind` | 解除绑定 |
| `/config` | 查看绑定信息 |
| `/b50 [用户名]` | 查 Best 50 |
| `/搜歌 <关键词>` | 搜索歌曲（支持别名） |
| `/随` | 随机推荐 |
| `/ping` | 检查状态 |
| `/帮助` | 命令列表 |

**群聊**：@ 发指令即可，Bot 回复时自动 @ 你。

---

## 架构

```
微信 3.9.x 客户端
    ↕ DLL 注入（wcferry）
WcfBot (app/wcf_bot.py)
    ↕ 回调
MessageHandler (app/handler.py)
    ↕
查分 API + 图片渲染
```

与之前的方案对比：

| 方案 | 平台 | 群聊 | 稳定性 | 部署难度 |
|------|------|------|--------|----------|
| Gewechat | Linux/Docker | ❌ 封杀 | 差 | 高 |
| 企业微信自建应用 | 任意 | ❌ 不支持群聊 | — | 高 |
| **WeChatFerry** | **Windows** | **✅** | **中** | **低** |

---

## 项目结构

```
maimai-wechat-bot/
├── app/
│   ├── main.py              # 入口
│   ├── wcf_bot.py           # WeChatFerry 异步封装
│   ├── handler.py           # 消息处理 & 指令路由
│   ├── database.py          # SQLite 用户数据库
│   ├── query.py             # 查分查询
│   ├── config.py            # Pydantic Settings 配置
│   ├── models.py            # 数据模型
│   ├── log.py               # loguru 日志
│   └── core/                # maimaiDX 核心
│       ├── clients/         # API 客户端（水鱼/落雪）
│       ├── image/           # Pillow 图片渲染
│       ├── merge/           # 数据合并模型
│       └── service/         # 曲目/别名聚合
├── static/                  # 静态资源
├── requirements.txt
├── .env.example
└── README.md
```

## 常见问题

| 问题 | 解决 |
|------|------|
| `module 'wcferry' not found` | `pip install wcferry` |
| 微信版本不匹配 | wcferry v39.6.0.0 匹配微信 3.9.6.x，去 WeChatFerry Releases 确认 |
| 数据初始化失败 | DivingFish API 被墙，挂代理 |
| 字体/图片缺失 | `static/` 目录没拷全 |
| B50 查询失败 | 检查 `DIVINGFISH_TOKEN` 或用户名是否正确 |
| 扫码后没反应 | 等几秒，微信登录需要时间 |

## 鸣谢

- [WeChatFerry](https://github.com/lich0821/WeChatFerry) — 微信底层 hook 框架
- [maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) — HoshinoBot 插件
- [Diving-Fish](https://www.diving-fish.com/maimaidx/prober/) — 水鱼查分器
- [LXNS](https://maimai.lxns.net/) — 落雪查分器

## 免责声明

本工具仅供学习和技术研究。使用个人微信号作为机器人**存在封号风险**，请使用小号测试。开发者不对账号安全承担任何责任。
