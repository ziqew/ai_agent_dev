from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent
from langchain.tools import tool
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import os

load_dotenv()
qwen_key = os.getenv("QWEN_API_KEY")


async def buy_train_ticket(from_city, to_city, date, seat_class, passenger_name, passenger_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 调试时用 False，可以看到浏览器动作
        page = await browser.new_page()
        
        # 打开携程火车票页面
        await page.goto("https://trains.ctrip.com/")

        # 输入出发地
        await page.fill("#departCityName", from_city)
        await page.keyboard.press("Enter")

        # 输入目的地
        await page.fill("#arriveCityName", to_city)
        await page.keyboard.press("Enter")

        # 输入日期
        await page.fill("#departDate", date)
        await page.keyboard.press("Enter")

        # 点击搜索
        await page.click("button.searchbtn")

        # 等待结果加载
        await page.wait_for_selector(".search_table_box")

        # 选择第一趟符合条件的车次（这里只做示例，你可以根据 train_number/seat_class 过滤）
        await page.click("text=预订")

        # 登录携程账号（需要携程账号+密码，可能要验证码）
        await page.fill("#username", "你的账号")
        await page.fill("#password", "你的密码")
        await page.click("#loginBtn")

        # 填写乘客信息（实际需要处理动态弹窗）
        await page.fill("input[name='passengerName']", passenger_name)
        await page.fill("input[name='passengerID']", passenger_id)

        # 提交订单
        await page.click("button.submitOrder")

        await page.wait_for_timeout(5000)  # 等待订单页面加载
        await browser.close()
        return {"status": "success", "msg": "订单已提交到携程"}

llm = ChatOpenAI(
    model="qwen-plus-2025-07-28",          # 千问模型
    api_key=qwen_key, # 也可用环境变量
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# resp = llm.invoke("你好，我现在是不是在用千问？")
# print(resp)


@tool("ctrip_train_booking", return_direct=True)
def ctrip_train_booking(from_city: str, to_city: str, date: str, seat_class: str, passenger_name: str, passenger_id: str):
    """调用 Playwright 自动化在携程订购火车票"""
    return asyncio.run(buy_train_ticket(from_city, to_city, date, seat_class, passenger_name, passenger_id))


agent = initialize_agent(
    tools=[ctrip_train_booking],
    llm=llm,
    agent="chat-zero-shot-react-description",
    verbose=True,
)

agent.run("帮我订 2025年9月25日 北京到上海的二等座火车票，乘客张三，身份证 123456789")