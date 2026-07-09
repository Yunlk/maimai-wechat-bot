# maimaiDX WeChat Bot 🎮

基于 Gewechat + maimaiDX 的**微信舞萌 DX 查分机器人**，支持个人微信号、群聊、图片渲染。

## 特性

- ✅ 个人微信号登录，支持群聊和拉群
- ✅ B50 查分（水鱼 + 落雪双数据源）
- ✅ 用户绑定系统（每人可绑定自己的查分器 Token）
- ✅ 歌曲搜索（支持别名）、随机推荐
- ✅ Pillow 图片渲染（B50 成绩图）
- ✅ Docker Compose 一键部署

---

## 部署

### 环境要求

- Linux 服务器（推荐 Ubuntu 20.04+）
- Docker + Docker Compose
- 一个微信小号（不建议用主号）

### 1. 克隆项目

```bash
git clone https://github.com/Yunlk/maimai-wechat-bot.git
cd maimai-wechat-bot
```

### 2. 准备静态资源

把原始 [maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) 项目的 `static/` 目录复制过来：

```bash
cp -r /path/to/maimaiDX/static/* ./static/
```

必需的文件：
```
static/
├── font/                          # 4 个字体文件
│   ├── ResourceHanRoundedCN-Bold.ttf
│   ├── ShangguMonoSC-Regular.otf
│   ├── Torus SemiBold.otf
│   └── FOT-NewRodin Pro EB.otf
├── mai/
│   ├── pic/PRISM_PLUS/            # B50 主题素材
│   ├── cover/                     # 曲绘（可空，自动下载）
│   ├── plate/                     # 姓名框
│   ├── shougou/                   # 称号图标
│   ├── icon/                      # UI 图标
│   ├── plate_version/
│   ├── plate_table/
│   └── rating_table/
└── data/                          # 运行时数据（自动生成）
```

### 3. 配置

```bash
cp .env.example .env
nano .env
```

最少要填的：

```ini
# ── Gewechat（必填）──
GEWECHAT_TOKEN=          # 78位字符串，用于设置回调
# GEWECHAT_APP_ID 留空，首次登录自动生成

# ── 回调地址（Docker 内用服务名互访，不用改）──
GEWECHAT_CALLBACK_URL=http://maimai-bot:8080/webhook

# ── 水鱼查分器 Token（查 B50 需要）──
# 找水鱼申请: https://www.diving-fish.com/maimaidx/prober/
DIVINGFISH_TOKEN=
```

### 4. 启动

```bash
# 拉取 Gewechat 镜像
docker compose pull gewechat

# 构建并启动
docker compose up -d --build

# 查看日志
docker compose logs -f
```

### 5. 扫码登录

**获取登录二维码：**

```bash
curl -X POST http://localhost:2531/login/getLoginQrCode \
  -H "Content-Type: application/json" \
  -d '{}'
```

返回的 JSON 里 `data.qrImgUrl` 就是二维码（可能是 base64 或 URL），用浏览器打开，手机微信扫码。

**确认登录成功：**

```bash
curl -X POST http://localhost:2531/login/checkLogin \
  -H "Content-Type: application/json" \
  -d '{"appId": ""}'
```

当 `data.status` 为 `1` 时表示登录成功，同时会返回 `appId`，把它填到 `.env` 的 `GEWECHAT_APP_ID`。

### 6. 设置回调

登录成功后，让 Gewechat 把消息推给 bot：

```bash
curl -X POST http://localhost:2531/tools/setCallback \
  -H "Content-Type: application/json" \
  -d '{
    "token": "你的GEWECHAT_TOKEN",
    "callbackUrl": "http://maimai-bot:8080/webhook"
  }'
```

> bot 启动时也会自动尝试设置回调，但手动确认更稳。

### 7. 验证

微信里给机器人发 `/ping`，回复 `pong!` 即成功。

---

## 使用

在微信里给机器人发指令：

| 指令 | 说明 |
|------|------|
| `/bind <用户名> [token]` | 绑定水鱼查分器（绑定后 /b50 不用输名字） |
| `/unbind` | 解除绑定 |
| `/config` | 查看绑定信息 |
| `/b50 [用户名]` | 查 Best 50（不填用户名则用已绑定的） |
| `/搜歌 <关键词>` | 搜索歌曲（支持别名） |
| `/随` / `/来一首` | 随机推荐 |
| `/ping` | 检查状态 |
| `/帮助` | 命令列表 |

**绑定流程：** 进群/加好友 → `/bind yun5k` → 直接 `/b50` 即可

**个人 Token：** 如果群友有自己的水鱼开发者 Token，可以 `/bind yun5k <token>`，查分走个人配额不受全局限制。

---

## 架构

```
微信客户端 ──iPad协议──▶ Gewechat (:2531) ──HTTP回调──▶ maimai-bot (:8080)
                                                          │
                                                    ┌─────┴─────┐
                                                    │            │
                                               水鱼查分器    落雪 API
```

- **Gewechat**: 微信 iPad 协议容器，负责收发消息
- **maimai-bot**: FastAPI 服务，处理指令、调用查分 API、渲染图片

---

## 常见问题

| 问题 | 解决 |
|------|------|
| 数据初始化失败 | 网络问题，DivingFish API 被墙的话挂代理 |
| 字体/图片缺失 | `static/` 目录没拷全，从原始 maimaiDX 复制 |
| 收不到消息 | 确认回调 URL 设置正确，两个容器在同一 Docker 网络 |
| 二维码扫了没反应 | 微信版本过高被限制，Gewechat 文档有推荐版本 |
| B50 查询失败 | 检查 `DIVINGFISH_TOKEN` 是否填写 |
| 容器反复重启 | `docker compose logs maimai-bot` 看日志 |

---

## 项目结构

```
maimai-wechat-bot/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── handler.py            # 消息处理 & 指令路由
│   ├── gewechat_client.py    # Gewechat REST API 封装
│   ├── database.py           # SQLite 用户数据库
│   ├── query.py              # 查分查询封装
│   ├── config.py             # Pydantic Settings 配置
│   ├── models.py             # User 数据模型
│   ├── resources.py          # 静态资源路径
│   ├── log.py                # loguru 日志
│   └── core/                 # maimaiDX 核心逻辑（从 HoshinoBot 剥离）
│       ├── clients/          # API 客户端（水鱼/落雪/柚子）
│       ├── image/            # Pillow 图片渲染
│       ├── merge/            # 数据合并 & 模型
│       ├── service/          # 曲目/别名聚合
│       └── utils/            # 计算工具
├── static/                   # 静态资源
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## 鸣谢

- [maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) — HoshinoBot 插件
- [Gewechat](https://github.com/Devo919/Gewechat) — 微信个人号框架
- [Diving-Fish](https://www.diving-fish.com/maimaidx/prober/) — 水鱼查分器
- [LXNS](https://maimai.lxns.net/) — 落雪查分器

## 免责声明

本项目仅供学习和技术研究使用。使用个人微信号作为机器人存在被封禁风险，**请使用小号测试**。
