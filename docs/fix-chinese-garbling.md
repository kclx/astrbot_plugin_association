# 修复中文文本替换问题指南

## 问题现象

发布任务时，中文文本被替换成其他汉字：
- 输入：`"寻找失落的宝藏"`
- 实际保存：`"搜索失較的存货"`

## 问题原因

这是 **LLM 在生成工具调用参数时的 token 选择问题**，不是编码问题。LLM 将用户的原文改写成了近义词或形近字。

## 解决方案（按推荐顺序）

### ⭐ 方案1: 调整 LLM Temperature（最推荐）

**位置**: AstrBot 配置文件或 Dashboard 的 Provider 设置

**操作步骤**:
1. 打开 AstrBot Dashboard
2. 进入 `Provider 配置` 页面
3. 找到当前使用的 LLM provider
4. 修改以下参数：
   ```json
   {
     "temperature": 0.0,
     "top_p": 0.95
   }
   ```
5. 保存并重启 AstrBot

**原理**: Temperature = 0.0 会让 LLM 始终选择最高概率的 token，避免随机替换字词。

---

### 方案2: 添加 System Prompt 约束

**位置**: AstrBot 的 System Prompt 设置

**添加以下内容**:
```
重要规则：调用工具时，必须精确提取用户消息中的原文作为参数。
禁止改写、替换或使用近义词。
例如：用户说"寻找失落的宝藏"，你必须使用"寻找失落的宝藏"，而不是"搜索失較的存货"。

Important: When calling tools, you MUST extract parameters EXACTLY from the user's message.
Do NOT paraphrase, rewrite, or replace any words with synonyms.
```

---

### 方案3: 切换到更可靠的模型

如果以上方案无效，建议切换到对中文支持更好的模型：

**推荐模型**:
- ✅ OpenAI GPT-4 / GPT-4-turbo
- ✅ Anthropic Claude 3.5 Sonnet
- ✅ 阿里云通义千问 Qwen2.5-72B+
- ✅ DeepSeek V3

**不推荐**（可能存在中文 token 问题）:
- ❌ 部分开源小模型
- ❌ 非官方 API 服务
- ❌ 过时版本的模型

---

## 验证修复效果

### 测试步骤

1. 重启 AstrBot 应用修复
2. 注册为委托人（如果还没注册）
3. 发送测试消息：
   ```
   我想发布一个任务：标题是"寻找失落的宝藏"，描述是"去探索远古遗迹，把宝藏找回来"，奖励500金币。
   ```
4. 检查返回的任务信息是否正确

### 查看诊断日志

插件已添加诊断日志，可以在 AstrBot 日志中查看：

```
[INFO] 收到任务发布请求 - 标题: 寻找失落的宝藏, 描述: 去探索远古遗迹，把宝藏找回来
[INFO] 标题 UTF-8字节: b'\xe5\xaf\xbb\xe6\x89\xbe\xe5\xa4\xb1\xe8\x90\xbd\xe7\x9a\x84\xe5\xae\x9d\xe8\x97\x8f'
```

如果修复成功，标题和描述应该完全匹配用户输入。

---

## 技术细节（可选阅读）

### 为什么会发生文本替换？

LLM 的工作流程：
```
1. 理解用户意图 ✅
2. 决定调用工具 ✅
3. 生成工具参数 ❌ ← 问题出在这里
```

在第3步，LLM 需要生成 JSON 格式的参数：
```json
{
  "title": "寻找失落的宝藏",
  "description": "去探索远古遗迹..."
}
```

如果 temperature 过高或模型有 bug，LLM 可能会：
- 选择概率相近但错误的 token
- 将"寻找"替换成"搜索"（近义词）
- 将"落"替换成"較"（形近字）

### 字符替换分析

| 原字符 | 错误字符 | Unicode | 关系类型 |
|--------|----------|---------|----------|
| 寻 | 搜 | 0x5bfb → 0x641c | 近义 |
| 找 | 索 | 0x627e → 0x7d22 | 近义 |
| 落 | 較 | 0x843d → 0x8f03 | 形近 |
| 宝 | 存 | 0x5b9d → 0x5b58 | 形近 |
| 藏 | 货 | 0x85cf → 0x8d27 | 语义相关 |

这些都是完全有效的汉字，UTF-8 编码也正确，只是被 LLM 错误地选择了。

---

## 还需要帮助？

如果以上方案都无法解决问题，请：

1. 查看完整诊断报告：`docs/encoding-issue-diagnosis.md`
2. 提供以下信息以便调试：
   - 使用的 LLM 模型名称
   - Temperature 和 top_p 设置
   - AstrBot 完整日志（包含工具调用部分）
3. 在 GitHub Issues 中报告问题

---

## 已应用的修复

插件代码已更新：
- ✅ 工具 docstring 中添加"必须精确提取"的提示
- ✅ 添加编码诊断日志用于排查
- ✅ 创建完整的诊断和修复文档

**下一步由你操作**：调整 AstrBot 的 LLM temperature 设置。
