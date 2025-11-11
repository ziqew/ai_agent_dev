import asyncio
from pathlib import Path
from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
qwen_key = os.getenv("QWEN_API_KEY")
open_router_key = os.getenv("OPENROUTER_API_KEY")
deepseek_key = os.getenv("DEEPSEEK_API_KEY")

# 初始化 LLM （可以换成千问/Qwen）
# qwen3-max qwen-plus-2025-07-28 qwen3-vl-plus
llm = ChatOpenAI(
    model="qwen3-vl-plus",          
    api_key=qwen_key, 
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


# llm = ChatOpenAI(
#     model="deepseek-reasoner",          
#     api_key=deepseek_key, 
#     base_url="https://api.deepseek.com/v1"
# )

# llm = ChatOpenAI(
#     model="openai/gpt-5",          
#     api_key=open_router_key, 
#     base_url="https://openrouter.ai/api/v1"
# )

chromium_path = Path.home() / "Library/Caches/ms-playwright/chromium-1169/chrome-mac/Chromium.app/Contents/MacOS/Chromium"


async def main():

    # 1. 初始化浏览器（可见窗口，方便调试）
    browser = Browser(headless=False,
                      highlight_elements=True,
                      channel ="chromium",
                      executable_path=chromium_path)
    # 在使用 browser_use 时，langchain-openai 和它不兼容
    #print("正在使用的浏览器路径:", browser.executable_path)



    # 2. 定义任务
    task = """
        任务目标：
        在携程官网查询 2025年10月20日 从上海到广州的火车票信息，
        并提取所有可用车次、出发时间、到达时间、历时、票价，保存为 JSON。

        页面结构说明：
        - 顶部导航栏有 “机票 / 火车票 / 酒店” 等选项。
        - 火车票查询区包括三个主要输入框：
        1. 出发城市（placeholder='出发地'）
        2. 到达城市（placeholder='到达地'）
        3. 出发日期（有日期选择器）
        - 右侧有 “搜索” 按钮（class 名类似于 search-btn）。
        - 搜索后会跳转到火车票结果页，列表中每一行包含：
        - 车次号（如 G1303）
        - 出发时间、到达时间、历时
        - 票价（显示在“二等座 / 一等座”等后面）

        操作步骤：
        1. 打开 https://trains.ctrip.com/
        2. 确认页面加载完成
        3. 在出发地输入框中输入 “上海”
        4. 在到达地输入框中输入 “广州”
        5. 选择出发日期 “2025-10-20”
        6. 点击 “搜索” 按钮
        7. 等待搜索结果加载完成（列表出现后再继续）
        8. 提取前 10 条火车信息，包括：
        - 车次号
        - 出发时间
        - 到达时间
        - 历时
        - 最低票价（如有）
        9. 将这些数据保存为 train_tickets.json
        10. 截图并保存结果页面为 ctrip_train.png
        """
    # task = """打开 https://www.baidu.com
    #     搜索 “上海到广州火车票,把搜索结果转成JSON格式”
    # """
    agent = Agent(task=task, 
                  browser=browser, 
                  llm=llm,
                  use_vision=True)
    result = await agent.run()
    print("任务结果：", result)

    await browser.stop()


if __name__ == "__main__":
    asyncio.run(main())


