import os
import re
import requests
from openai import OpenAI

# 你可以直接在这里填写 API Key 和模型配置。
# 也可以保留为空，让程序继续从环境变量读取。
OPENAI_API_KEY = ""
OPENAI_API_BASE = "https://api.deepseek.com/v1"
OPENAI_MODEL = "deepseek-chat"
TAVILY_API_KEY = ""

#定义智能旅行助手的系统提示，指导模型如何分析用户请求并使用工具。
AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具:
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str)`: 根据城市和天气搜索推荐的旅游景点。

# 输出格式要求:
你的每次回复必须严格遵循以下格式，包含一对Thought和Action：

Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]

Action的格式必须是以下之一：
1. 调用工具：function_name(arg_name="arg_value")
2. 结束任务：Finish[最终答案]

# 重要提示:
- 每次只输出一对Thought-Action
- Action必须在同一行，不要换行
- 当收集到足够信息可以回答用户问题时，必须使用 Action: Finish[最终答案] 格式结束

请开始吧！
"""


def get_weather(city: str) -> str:
    """通过调用 wttr.in API 查询真实的天气信息。"""
    url = f"https://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']
        return f"{city}当前天气: {weather_desc}，气温 {temp_c} 摄氏度"
    except requests.exceptions.RequestException as e:
        return f"错误: 查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        return f"错误: 解析天气数据失败，可能是城市名称无效 - {e}"


def get_attraction(city: str, weather: str) -> str:
    """根据城市和天气，使用 Tavily Search API 搜索并返回优化后的景点推荐。"""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误: 未配置 TAVILY_API_KEY 环境变量。"

    try:
        from tavily import TavilyClient
    except ImportError:
        return "错误: 未安装 tavily 包，请通过 `pip install tavily` 安装。"

    tavily = TavilyClient(api_key=api_key)
    query = f"'{city}' 在 '{weather}' 天气下最值得去的旅游景点推荐及理由"

    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        if response.get("answer"):
            return response["answer"]

        formatted_results = []
        for result in response.get("results", []):
            title = result.get("title", "未知标题")
            content = result.get("content", "无内容")
            formatted_results.append(f"- {title}: {content}")

        if not formatted_results:
            return "抱歉，没有找到相关的旅游景点推荐。"

        return "根据搜索，为您找到以下信息:\n" + "\n".join(formatted_results)
    except Exception as e:
        return f"错误: 执行 Tavily 搜索时出现问题 - {e}"


available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}


class OpenAICompatibleClient:
    """一个用于调用任何兼容 OpenAI 接口的 LLM 服务的客户端。"""

    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        print("正在调用大语言模型...")
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
            )
            answer = response.choices[0].message.content
            print("大语言模型响应成功。")
            return answer
        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return "错误: 调用语言模型服务时出错。"


if __name__ == "__main__":
    api_key = OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
    base_url = OPENAI_API_BASE or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
    model_id = OPENAI_MODEL or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        raise RuntimeError("请先在 agent.py 中填写 OPENAI_API_KEY，或设置 OPENAI_API_KEY 环境变量。")

    if TAVILY_API_KEY:
        os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

    llm = OpenAICompatibleClient(model=model_id, api_key=api_key, base_url=base_url)

    # 这里是一个示例用户请求，你可以修改它来测试不同的场景。
    user_prompt = "你好，请帮我查询一下今天武汉的天气，然后根据天气推荐一个合适的旅游景点。"
    prompt_history = [f"用户请求: {user_prompt}"]

    print(f"用户输入: {user_prompt}\n" + "=" * 40)

    for i in range(5):
        print(f"--- 循环 {i+1} ---\n")
        full_prompt = "\n".join(prompt_history)
        llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)

        match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
        if match:
            truncated = match.group(1).strip()
            if truncated != llm_output.strip():
                llm_output = truncated
                print("已截断多余的 Thought-Action 对")
        print(f"模型输出:\n{llm_output}\n")
        prompt_history.append(llm_output)

        action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
        if not action_match:
            observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "=" * 40)
            prompt_history.append(observation_str)
            continue

        action_str = action_match.group(1).strip()
        if action_str.startswith("Finish"):
            finish_match = re.match(r"Finish\[(.*)\]", action_str)
            final_answer = finish_match.group(1) if finish_match else action_str
            print(f"任务完成，最终答案: {final_answer}")
            break

        tool_name_match = re.search(r"(\w+)\(", action_str)
        args_str_match = re.search(r"\((.*)\)", action_str)
        if not tool_name_match or not args_str_match:
            observation = "错误: 无效的 Action 格式。"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "=" * 40)
            prompt_history.append(observation_str)
            continue

        tool_name = tool_name_match.group(1)
        args_str = args_str_match.group(1)
        kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

        if tool_name in available_tools:
            observation = available_tools[tool_name](**kwargs)
        else:
            observation = f"错误: 未定义的工具 '{tool_name}'"

        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)
