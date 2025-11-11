# zhipin_qwen_vl.py
import asyncio
import csv
import json
import re
from playwright.async_api import async_playwright
import dashscope
from dashscope import MultiModalConversation
import base64
import os
from dotenv import load_dotenv

load_dotenv()
dashscope.api_key = os.getenv("QWEN_API_KEY")
PROFILE_PATH = "/Users/gongwenwei/gitrepo/ai_agent_dev/playwright_profiles/my_chrome_profile"

def image_to_data_url(image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"

async def qwen_vl_extract_jobs(image_path: str) -> list[dict]:
    """调用 Qwen-VL 从截图中提取岗位信息"""
    data_url = image_to_data_url(image_path)
    prompt = (
        "请从图中提取所有前端工程师岗位信息，包括：公司名称、职位名称、薪资范围（如 15-25K）、工作地点。"
        "只输出标准 JSON 数组，不要任何解释。格式：[{\"company\": \"...\", \"position\": \"...\", \"salary\": \"...\", \"location\": \"...\"}]"
    )
    messages = [
        {
            "role": "user",
            "content": [
                {"image": data_url},
                {"text": prompt}
            ]
        }
    ]
    response = MultiModalConversation.call(
        model="qwen-vl-max",
        messages=messages,
        temperature=0.1  # 降低随机性，提高结构化输出稳定性
    )
    if response.status_code == 200:
        text = response.output.choices[0].message.content[0]["text"]
        # 尝试提取 JSON
        try:
            # 清理可能的 Markdown 代码块
            text = re.sub(r"```json?\s*", "", text)
            text = re.sub(r"```", "", text)
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"JSON 解析失败: {e}")
            print("原始输出:", text)
            return []
    else:
        raise Exception(f"Qwen-VL API 错误: {response}")

async def main():
    async with async_playwright() as p:
        # browser = await p.chromium.launch(headless=False)  # 调试时设为 False
        # context = await browser.new_context()
        screen_size = (1440, 900)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            args=[
                "--disable-extensions",
                "--disable-file-system",
                "--disable-plugins",
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
                # No '--no-sandbox' arg means the sandbox is on.
            ],
            headless=bool(os.environ.get("PLAYWRIGHT_HEADLESS", False)),
            viewport={"width": screen_size[0], "height": screen_size[1]}, 
        )

        page = await context.new_page()

        print("正在打开 BOSS 直聘...")
        await page.goto("https://www.zhipin.com", timeout=60000)
        await page.wait_for_timeout(3000)

        # 检查是否跳转到验证码页
        if "captcha" in page.url or await page.query_selector(".slider"):
            print("⚠️ 检测到验证码，请手动处理后按回车继续...")
            input()
        else:
            print("页面加载正常")

        # 定位搜索框（根据 zhipin.com 实际结构）
        try:
            search_box = await page.wait_for_selector("input[name='query']", timeout=10000)
            await search_box.fill("前端工程师")
            await page.keyboard.press("Enter")  # 或点击搜索按钮
            print("已输入“前端工程师”并触发搜索")
        except Exception as e:
            print("搜索框定位失败:", e)
            await page.screenshot(path="error.png")
            await context.close()
            return

        # 等待结果加载
        await page.wait_for_selector(".job-card", timeout=15000)
        print("搜索结果已加载")

        # 滚动加载更多（可选）
        for _ in range(2):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

        # 截图结果区域
        await page.screenshot(path="jobs_screenshot.png")
        print("已保存截图: jobs_screenshot.png")

        await browser.close()

    # 调用 Qwen-VL 提取数据
    print("正在调用 Qwen-VL 分析截图...")
    jobs = await qwen_vl_extract_jobs("jobs_screenshot.png")

    # 保存为 CSV
    if jobs:
        with open("jobs.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["company", "position", "salary", "location"])
            writer.writeheader()
            writer.writerows(jobs)
        print(f"✅ 已保存 {len(jobs)} 条岗位到 jobs.csv")
    else:
        print("❌ 未提取到有效岗位数据")

if __name__ == "__main__":
    asyncio.run(main())