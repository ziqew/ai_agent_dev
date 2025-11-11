import base64
import io
import time
import json
import requests
from PIL import Image
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
# ======== 通义千问配置 ========

load_dotenv()
qwen_key = os.getenv("QWEN_API_KEY")



QWEN_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-vl-plus"  # 或 "qwen-vl-max"

# ======== 调用 Qwen-VL 模型 ========
def call_qwen_vl(image_bytes: bytes, prompt: str, history=None):
    """
    调用 Qwen-VL 模型进行视觉理解
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {qwen_key}"
    }

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个智能网页操作助手。阅读截图后，告诉我应该点击哪个区域（以像素坐标表示），或者是否完成任务。"
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"}
                ]
            }
        ]
    }

    response = requests.post(f"{QWEN_ENDPOINT}/chat/completions", headers=headers, data=json.dumps(payload))
    result = response.json()
    text = result["choices"][0]["message"]["content"]
    print("🤖 Qwen-VL 输出：", text)
    return text

# ======== 浏览器代理循环 ========
def run_browser_agent():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # 打开测试网页
        page.goto("https://www.baidu.com")
        time.sleep(2)

        for step in range(3):
            print(f"\n=== Step {step+1} ===")
            # 截图
            screenshot_bytes = page.screenshot(full_page=False)

            # 构造指令
            #prompt = "请找到页面上的链接或按钮，告诉我点击哪个坐标可以进入下一页。"
            prompt = "请找到页面上的页面上的搜索框，告诉我点击哪个坐标可以进入搜索框。"
            # 调用 Qwen-VL
            answer = call_qwen_vl(screenshot_bytes, prompt)

            # 尝试解析坐标（假设模型输出格式为 “点击坐标 (x=xxx, y=yyy)”）
            import re
            match = re.search(r"x\s*=\s*(\d+).*?y\s*=\s*(\d+)", answer)
            if match:
                x, y = int(match.group(1)), int(match.group(2))
                print(f"👉 点击坐标: ({x}, {y})")
                page.mouse.click(x, y)
                time.sleep(3)
            elif "完成" in answer or "结束" in answer:
                print("✅ 任务完成")
                break
            else:
                print("❓ 模型未返回坐标，结束")
                break

        context.close()
        browser.close()

if __name__ == "__main__":
    run_browser_agent()
