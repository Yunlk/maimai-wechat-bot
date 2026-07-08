# maimaiDX WeChat Bot 🎮

基于 Gewechat + maimaiDX 的**微信舞萌 DX 查分机器人**。

## 特性

- ✅ 个人微信号登录，支持群聊
- ✅ B50/B40 查分（水鱼查分器 + 落雪查分器）
- ✅ 歌曲搜索（支持别名）
- ✅ 随机推荐
- ✅ 图片渲染（Pillow）
- ✅ Docker 一键部署

## 快速开始

### 1. 准备静态资源

```bash
# 下载 maimaiDX 静态资源（曲绘、字体、UI素材等）
# 放到 static/ 目录下
# 参考: https://github.com/Yuri-YuzuChaN/maimaiDX
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env 填写配置
```

### 3. 启动

```bash
docker compose up -d
```

### 4. 扫码登录

1. 访问 Gewechat API 获取登录二维码
2. 微信扫码登录
3. 在 Gewechat 控制台设置消息回调: `http://maimai-bot:8080/webhook`

## 指令列表

| 指令 | 说明 |
|------|------|
| `/b50 <用户名>` | 查看 Best 50 成绩图 |
| `/搜歌 <关键词>` | 搜索歌曲 |
| `/随` | 随机来一首 |
| `/ping` | 检查状态 |
| `/帮助` | 帮助 |

## 配置项

见 `.env.example`

## 项目结构

```
maimai-wechat-bot/
├── app/
│   ├── main.py              # FastAPI 服务入口
│   ├── handler.py            # 消息处理器
│   ├── gewechat_client.py    # Gewechat API 封装
│   ├── config.py             # 配置
│   ├── models.py             # 数据模型
│   ├── resources.py          # 资源路径
│   ├── log.py                # 日志
│   └── core/                 # maimaiDX 核心（API客户端/图片渲染/数据合并）
├── static/                   # 静态资源
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 鸣谢

- [maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) — HoshinoBot 插件
- [Gewechat](https://github.com/Devo919/Gewechat) — 微信个人号框架
- [Diving-Fish](https://www.diving-fish.com/maimaidx/prober/) — 水鱼查分器
- [LXNS](https://maimai.lxns.net/) — 落雪查分器

## 免责声明

本项目仅供学习和技术研究使用。使用个人微信号作为机器人存在被封禁风险，请使用小号测试。
