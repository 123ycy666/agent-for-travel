# 智能旅行助手示例

这是一个基于提示工程和工具调用的简单智能体示例。它通过真实 LLM 决策，并使用 `wttr.in` 查询天气、使用 `Tavily` 搜索景点。

## 主要文件

- `agent.py`: 智能体实现，包括系统提示、工具函数、LLM 客户端和执行循环。
- `requirements.txt`: 运行所需依赖项。

## 运行方式

1. 安装依赖:

```bash
pip install -r requirements.txt
```

2. 配置 API Key:

- 你可以直接在 `agent.py` 顶部填写：
  - `OPENAI_API_KEY`
  - `OPENAI_API_BASE`
  - `OPENAI_MODEL`
  - `TAVILY_API_KEY`（如果要使用 `get_attraction` 工具）
- 也可以继续使用环境变量配置：
  - `OPENAI_API_KEY`
  - `OPENAI_API_BASE` （可选，默认使用 OpenAI 官方服务）
  - `OPENAI_MODEL` （例如 `gpt-4o-mini`）
  - `TAVILY_API_KEY`（如果要使用 `get_attraction` 工具）

3. 运行:

```bash
python agent.py
```

## 说明

- `AGENT_SYSTEM_PROMPT` 定义了智能体的角色、可用工具和输出格式。
- 智能体在每轮中生成 `Thought` 和 `Action`。
- 当能给出最终答案时，智能体会使用 `Finish[...]` 结束任务。
