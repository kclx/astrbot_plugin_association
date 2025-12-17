# 中文乱码问题诊断报告

## 问题描述

用户输入：`"寻找失落的宝藏"`
LLM 解析后：`"搜索失較的存货"`

## 问题分析

### 1. 不是编码问题

通过编码测试发现：
- 乱码字符都是有效的汉字（Unicode: 0x641c, 0x7d22 等）
- 不是乱码符号或非法字符
- UTF-8 编码完全正常

### 2. 是文本替换问题

| 原文 | 乱码 | Unicode对比 | 关系 |
|------|------|-------------|------|
| 寻找 | 搜索 | 0x5bfb,0x627e → 0x641c,0x7d22 | 近义词 |
| 失落 | 失較 | 0x5931,0x843d → 0x5931,0x8f03 | 形近字 |
| 宝藏 | 存货 | 0x5b9d,0x85cf → 0x5b58,0x8d27 | 语义相关 |
| 探索 | 探究 | 0x63a2,0x7d22 → 0x63a2,0x7a76 | 近义词 |
| 远古 | 广轨 | 0x8fdc,0x53e4 → 0x5e7f,0x8f68 | 形近字 |
| 遗迹 | 道色 | 0x9057,0x8ff9 → 0x9053,0x8272 | 形近字 |

### 3. 根本原因

这是 **LLM Token 生成问题**，发生在以下环节：

```
用户输入 → LLM理解 → LLM生成工具调用JSON → JSON解析 → 插件接收
                        ↑ 问题出在这里
```

LLM 在生成工具调用的 JSON 参数时，选择了错误的 token。

## 可能的触发因素

### 1. Temperature 过高
- Temperature > 0.7 会导致 token 选择更随机
- 工具调用应该使用 temperature ≈ 0.0-0.3

### 2. 采样参数不当
- Top-p 过高允许低概率 token
- Top-k 设置不合理

### 3. 模型特定问题
- 某些模型的中文 tokenizer 可能存在 bug
- 特定模型版本可能有中文处理缺陷

### 4. Tool Calling 实现问题
- 部分模型的 function calling 实现不完善
- 中文参数可能被模型"改写"而非"提取"

## 解决方案

### 方案 1: 降低 LLM Temperature（推荐）

在 AstrBot 的 provider 配置中设置：
```json
{
  "model_config": {
    "temperature": 0.0,
    "top_p": 0.95
  }
}
```

### 方案 2: 修改 Tool Schema 强调精确性

更新工具的 docstring，强调参数必须精确提取：

```python
@filter.llm_tool(name="publish_request")
async def llm_tool(
    self,
    event: AstrMessageEvent,
    title: str,
    description: str,
    reward: float = 0.0,
    deadline: str | None = None,
) -> str:
    """向冒险家工会发布一份委托任务。

    **重要**: 必须精确提取用户提供的 title 和 description，不得改写或替换任何字词。

    Args:
        title(string): 委托任务标题，必须从用户消息中精确提取，不得改写
        description(string): 委托任务详细描述，必须从用户消息中精确提取，不得改写
        reward(number): 奖励金额，默认为 0.0
        deadline(string): 任务截止时间，ISO 格式字符串，例如 "2025-12-31T23:59:59"
    """
```

### 方案 3: 在 System Prompt 中添加约束

在 AstrBot 的 system prompt 中添加：

```
When calling tools, you MUST extract parameters EXACTLY as they appear in the user's message.
Do NOT paraphrase, rewrite, or replace any Chinese characters with similar ones.
For example, if user says "寻找失落的宝藏", you must use "寻找失落的宝藏" exactly, not "搜索失較的存货".
```

### 方案 4: 切换到更可靠的模型

如果当前使用的模型是：
- 某些开源模型（如部分 Qwen/ChatGLM 版本）
- 非官方的模型服务

建议切换到：
- OpenAI GPT-4/GPT-4-turbo
- Anthropic Claude 3.5 Sonnet
- 最新版本的 Qwen2.5 或 DeepSeek

### 方案 5: 使用 JSON Schema 约束（如果支持）

如果 LLM 支持 JSON Schema 约束，可以使用 `pattern` 来限制参数格式。

## 验证方法

在 `handlers/llm_handlers.py` 中已添加诊断日志：

```python
logger.info(f"收到任务发布请求 - 标题: {title}, 描述: {description}")
logger.info(f"标题 UTF-8字节: {title.encode('utf-8')}")
```

如果应用修复后，日志应显示正确的文本。

## 临时 Workaround（不推荐）

虽然已经在代码中尝试了 latin1→utf-8 的编码修复，但这对 token 替换问题无效。

唯一的临时方案是在插件中添加"反向替换"字典，但这不是根本解决方案：

```python
FIX_DICT = {
    "搜索": "寻找",
    "失較": "失落",
    "存货": "宝藏",
    "探究": "探索",
    "广轨": "远古",
    "道色": "遗迹",
}
```

**不推荐使用此方案**，因为：
1. 无法覆盖所有可能的替换
2. 可能误伤正确的文本
3. 治标不治本

## 结论

这是 **LLM 层面的问题**，不是插件代码问题。最有效的解决方案是：

1. **立即**：降低 LLM 的 temperature 到 0.0-0.3
2. **短期**：在 system prompt 和 tool docstring 中强调精确提取
3. **长期**：如果问题持续，考虑切换到更可靠的模型或模型服务商

## 相关文件

- 问题位置: AstrBot 核心 `astrbot/core/agent/runners/tool_loop_agent_runner.py:241`
- 诊断代码: `handlers/llm_handlers.py:62-76`
- 测试脚本: `test_encoding.py`, `analyze_garbled.py`
