import asyncio
from browser_use import Agent, Browser, ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
qwen_key = os.getenv("QWEN_API_KEY")
async def main():

    # 1. 初始化浏览器（可见窗口，方便调试）
    browser = Browser(headless=False)
    # 在使用 browser_use 时，langchain-openai 和它不兼容
    # 初始化 LLM （可以换成千问/Qwen）
    llm = ChatOpenAI(
        model="qwen-plus-2025-07-28",          # 千问模型
        api_key=qwen_key, # 也可用环境变量
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )



    # 2. 定义任务
    task = """
    打开 https://trains.ctrip.com ，
    查询 2025年9月20日 北京 到 上海 的火车票，
    并把车次和票价列表提取出来返回给我。 
    """
    agent = Agent(task=task, browser=browser, llm=llm)
    result = await agent.run()
    print("任务结果：", result)

    await browser.close()


if __name__ == "__main__":
    asyncio.run(main())


