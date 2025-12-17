# 探险家协会 | Adventurer Guild

<div align="center">
  <img src="logo.png" alt="Logo" width="200"/>
  <p>一个用于 AstrBot 的冒险者公会任务管理插件</p>
</div>

## 项目简介

探险家协会是一个基于 AstrBot 框架的插件，实现了类似游戏中公会任务系统的完整功能。用户可以注册为**冒险者**（接取任务）或**委托人**（发布任务），通过跨平台消息系统（支持 Telegram、QQ）完成任务发布、接取、提交、确认的完整生命周期。

## 核心特性

- **双角色系统**：用户可以注册为冒险者或委托人，不可以同时拥有两种身份
- **完整任务流程**：发布 → 接取 → 提交 → 确认，支持任务状态跟踪
- **跨平台支持**：通过统一消息对象（UMO）支持 Telegram、QQ 等多平台
- **智能推送**：新任务自动推送给空闲状态的冒险者
- **LLM 集成**：通过 `@filter.llm_tool()` 装饰器，让 AI 助手可以调用任务操作
- **状态管理**：冒险者支持 IDLE、WORKING、REST、QUIT 四种状态
- **历史记录**：完整的任务分配历史和系统日志记录

## 任务生命周期

```
┌─────────────┐
│  PUBLISHED  │  委托人发布任务，自动推送给空闲冒险者
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  ASSIGNED   │  冒险者接取任务，状态变为 WORKING
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  COMPLETED  │  冒险者提交任务，等待委托人确认
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   CLOSED    │  委托人确认完成，冒险者状态恢复为 IDLE
└─────────────┘
```

## 架构设计

项目采用三层架构设计：

### 1. 插件层 (`main.py`)
- `AssociationPlugin` 类处理事件过滤和消息路由
- 通过 `@filter.command()` 注册命令处理器
- 通过 `@filter.llm_tool()` 暴露工具给 LLM
- 使用 `send_message_to_users()` 实现跨平台消息推送

### 2. 业务逻辑层 (`engine/association_client.py`)
- `AssociationClient` 类实现核心业务逻辑
- 处理注册、接取任务、提交任务、确认任务等工作流
- 协调状态转换和数据验证

### 3. 数据访问层 (`engine/supa_client.py`)
- `SupabaseClient` 类封装所有数据库操作
- 提供统一的 CRUD 接口
- 使用 `_get_records()` 和 `_get_single_record()` 辅助方法

### 领域模型 (`domain/`)
- **值对象** (`vo.py`)：`Adventurer`、`Clienter`、`Quest` 数据类
- **状态枚举** (`status.py`)：`AdventurerStatus`、`QuestStatus`

详细的数据库表结构请参阅 [数据库表结构文档](docs/database-schema.md)。

## 快速开始

### 1. 环境要求

- Python 3.8+
- AstrBot 框架
- Supabase 账号和项目

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置插件

在 `_conf_schema.json` 中配置以下参数：

```json
{
  "supabase_url": "你的 Supabase 项目 URL",
  "supabase_key": "你的 Supabase API Key",
  "aiocqhttp_id": "QQ 平台 ID（机器人名称）",
  "telegram_id": "Telegram 平台 ID（机器人名称）"
}
```

### 4. 数据库初始化

在 Supabase 中创建所需的数据库表，表结构详见 [docs/database-schema.md](docs/database-schema.md)。

### 5. 启动插件

插件通过 `@register()` 装饰器自动注册到 AstrBot，配置完成后重启 AstrBot 即可。

## 使用指南

### 冒险者操作

- **注册冒险者**：通过 LLM 工具或命令注册
- **查看可用任务**：`fetch_quests_published` 工具
- **接取任务**：`accept_task` 工具 + 任务 ID
- **提交任务**：`submit_quest` 工具
- **状态管理**：
  - `adventurer_idle`：设置为空闲状态
  - `adventurer_rest`：设置为休息状态（不接收新任务）
  - `adventurer_quit`：退出系统

### 委托人操作

- **注册委托人**：通过 LLM 工具或命令注册
- **发布任务**：`publish_request` 工具，需提供标题、描述、报酬、截止时间
- **确认任务**：`confirm_quest` 工具，确认冒险者提交的任务

### LLM 工具集成

本插件大量使用 LLM 工具装饰器，用户可以通过自然语言与 AI 助手交互来完成任务操作。例如：

```
用户：我想发布一个任务，标题是"寻找失落的宝石"，报酬 100 金币，截止时间下周五
AI：（调用 publish_request 工具）
```

## 跨平台消息系统

插件通过 `send_message_to_users()` 方法实现跨平台消息推送：

1. 根据用户的 `contact_way` 和 `contact_number` 构建统一消息对象（UMO）
2. 格式：`{platform_id}:FriendMessage:{contact_number}`
3. 支持任务通知自动发送到用户所在的平台（Telegram 或 QQ）

## 用户身份识别

系统通过消息事件中的以下信息识别用户：

- `name`：来自 `event.get_sender_name()`
- `contact_way`：平台名称，如 "telegram"、"aiocqhttp"
- `contact_number`：平台用户 ID

所有数据库查询使用 `(contact_way, contact_number)` 作为复合键。

## 开发指南

### 目录结构

```
.
├── main.py                 # 插件主文件（插件层）
├── engine/
│   ├── association_client.py  # 业务逻辑层
│   └── supa_client.py         # 数据访问层
├── domain/
│   ├── vo.py               # 值对象定义
│   └── status.py           # 状态枚举
├── docs/
│   └── database-schema.md  # 数据库表结构文档
├── metadata.yaml           # 插件元数据
├── _conf_schema.json       # 配置模板
└── requirements.txt        # Python 依赖
```

### 开发注意事项

- 始终在同一事务中更新任务状态和相关实体状态（如冒险者状态）
- 使用 `Quest.format_quests()` 进行统一的任务列表格式化
- 业务验证在 `AssociationClient` 层完成，`SupabaseClient` 层只负责数据操作
- 错误日志使用 `astrbot.api.logger`，不使用标准 Python logging
- 所有 ID 使用 `uuid.uuid4()` 生成
- 时间字段使用 `datetime.fromisoformat()` 解析和 `.strftime('%Y-%m-%d %H:%M:%S')` 序列化

## 许可证

本项目采用 [LICENSE](LICENSE) 许可证。

## 作者

Orlando

## 相关文档

- [数据库表结构](docs/database-schema.md)