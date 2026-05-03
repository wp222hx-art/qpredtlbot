# 🤖 QPred Telegram Bot

> **7×24 小时超级运营官 + 客服 + 销售 + 保安**
> 调通 Telegram Bot API，建立专属群客服体系，接入最强推理模型 + 自主 RAG，
> 服务群内容 + 实时传递平台数据。

---

## ✨ 核心能力

| 模块 | 能力 |
| --- | --- |
| 🎯 业务播报 | `/predict` 热门预测市场 · `/price` JYC 实时行情 · 定时自动推送 |
| 🔗 推广体系 | 注册即生成专属链接 · 邀请奖励 · 5% 永久返佣 · 排行榜 |
| 🤖 AI 客服 | **多供应商可切换**：OpenAI / DeepSeek-R1 / OpenRouter (Claude) / 自定义兼容端点 |
| 🧠 自主 RAG | FAQ 知识库 + RapidFuzz 模糊匹配 + 平台实时数据自动注入上下文 |
| 🛡️ 群守卫 | CAPTCHA 验证 · 反刷屏 · 反诈骗关键词 · 外链白名单 · 三次警告自动禁言 |
| 📢 数据广播 | APScheduler 定时推送 JYC 行情 / 热门市场到所有已登记群组 |
| 📊 管理后台 | `/stats` 运营数据 · `/broadcast` 群发公告 · `/ban` `/unban` `/reload_faq` |

---

## 🚀 快速开始

### 1. 克隆 / 进入项目

```bash
cd qpred_bot
```

### 2. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
vim .env
```

必填项：

| 变量 | 获取方式 |
| --- | --- |
| `BOT_TOKEN` | 在 Telegram 搜索 [@BotFather](https://t.me/BotFather) → `/newbot` → 复制 Token |
| `ADMIN_IDS` | 给 [@userinfobot](https://t.me/userinfobot) 发消息 → 复制 User ID |
| `OPENAI_API_KEY` | 按所选 `AI_PROVIDER` 填入对应 Key |

> ⚠️ 在 BotFather 中执行 `/setprivacy` → **Disable**，让 Bot 能读到群消息。

### 4. 启动

```bash
python main.py
```

看到日志 `🚀 QPred Telegram Bot 启动成功!` 即为 OK。

### 5. 拉 Bot 进群

1. 把 Bot 加入目标群
2. 在群里把它**设为管理员**（授予「删除消息」「封禁成员」「禁言」权限）
3. 管理员在群里发送 `/register_group` → 该群即被纳入定时广播
4. 在群里 `@bot 怎么质押 JYC?` 测试 AI 客服

---

## 🤖 AI 模型可切换

`config.py` 通过 `AI_PROVIDER` + `OPENAI_BASE_URL` 控制供应商，全部使用 OpenAI 兼容协议：

| 供应商 | `AI_PROVIDER` | `OPENAI_MODEL` 推荐 | `OPENAI_BASE_URL` |
| --- | --- | --- | --- |
| OpenAI 综合最强 | `openai` | `gpt-4o` | （留空使用默认） |
| OpenAI 性价比 | `openai` | `gpt-4o-mini` | （留空） |
| OpenAI 推理模型 | `openai` | `o1-mini` / `o1` | （留空） |
| **DeepSeek-R1** ✨ | `deepseek` | `deepseek-reasoner` | `https://api.deepseek.com/v1` |
| DeepSeek-V3 | `deepseek` | `deepseek-chat` | `https://api.deepseek.com/v1` |
| Claude (经 OpenRouter) | `openrouter` | `anthropic/claude-3.5-sonnet` | `https://openrouter.ai/api/v1` |
| 自定义兼容端点 | `custom` | （任意） | 你的服务地址 |

> 代码内置推理模型适配 (o1/o3/deepseek-reasoner) ：自动改用 `max_completion_tokens`、跳过 `temperature`。

---

## 📋 命令列表

### 用户命令

| 命令 | 说明 |
| --- | --- |
| `/start` | 注册并领取专属推广链接 + 100 JYC 体验金 |
| `/predict` | 热门 TOP 5 预测市场 |
| `/price` | JYC 实时行情（市值 / 24h 浮动 / 成交） |
| `/ref` | 我的推广中心（链接 / 积分 / 邀请数） |
| `/rank` | 推广排行榜 TOP 10 |
| `/faq` | 常见问题列表 |
| `/ask <问题>` | 直接调用 AI 智能问答（带平台实时数据 RAG） |
| `/help` | 帮助菜单 |

### 管理员命令（仅 `ADMIN_IDS` 可用）

| 命令 | 说明 |
| --- | --- |
| `/stats` | 用户 / 活跃 / 警告 / AI 调用数据 |
| `/broadcast 内容` | 向所有已登记群组群发公告 |
| `/register_group` | 在某群发送 → 把该群纳入广播目标 |
| `/push_price` | 立即推送 JYC 行情到所有群 |
| `/push_markets` | 立即推送热门市场到所有群 |
| `/ban` (回复某人) | 封禁该用户 |
| `/unban <user_id>` | 解封 |
| `/reload_faq` | 热重载 FAQ 知识库（不重启） |

---

## 🛡️ 群守卫规则

- ✅ 新人入群 → CAPTCHA 验证（60s 未点击自动踢出）
- ✅ 10 秒内 > 5 条消息 → 自动禁言 30 分钟（反刷屏）
- ✅ 命中反诈关键词（私信客服 / 空投点击 / 微信联系等）→ 删除 + 警告
- ✅ 非白名单外链 → 删除 + 警告
- ✅ 三次警告 → 自动禁言 24 小时
- ✅ 管理员豁免

---

## 🧠 自主 RAG 工作流

```
用户问题
    │
    ▼
┌─────────────────────┐
│ 1. 关键词命中 FAQ?    │   ← 高置信直接返回 (省 token, 秒回)
└─────────────────────┘
    │ 否 / 低置信
    ▼
┌─────────────────────┐
│ 2. RapidFuzz 模糊检索  │   ← 取 top-3 FAQ
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 3. 注入平台实时数据    │   ← JYC 价格 / TVL / 用户数
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 4. 调用推理模型        │   ← gpt-4o / o1 / deepseek-reasoner …
└─────────────────────┘
    │
    ▼
   回复
```

扩展知识库：编辑 `knowledge_base/faq.json` → 管理员在 Bot 中执行 `/reload_faq`。

---

## 📁 目录结构

```
qpred_bot/
├── main.py                  # 主入口
├── config.py                # 多供应商配置中心
├── database.py              # SQLite 异步存储
├── logger_config.py         # 日志系统
├── requirements.txt         # 依赖
├── .env.example             # 环境变量模板
├── Dockerfile               # Docker 镜像
├── docker-compose.yml       # 一键起 (含挂载)
├── handlers/
│   ├── commands.py          # 用户命令
│   ├── admin.py             # 管理员命令
│   ├── guardian.py          # 群守卫
│   ├── faq_handler.py       # AI 客服路由
│   └── broadcaster.py       # 定时广播
├── services/
│   ├── ai_service.py        # AI 推理 + 自主 RAG
│   └── qpred_api.py         # QPred 平台数据 API
└── knowledge_base/
    └── faq.json             # FAQ 知识库
```

---

## 🐳 Docker 部署

```bash
# 1. 配置 .env
cp .env.example .env
vim .env

# 2. 一键起
docker compose up -d

# 3. 查看日志
docker compose logs -f
```

---

## 📝 License

MIT
