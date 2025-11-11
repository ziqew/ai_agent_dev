import os
import re
import json
import time
import csv
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
import asyncio
from pydantic import BaseModel, Field

from browser_use import Agent,Browser, ChatOpenAI

load_dotenv()
qwen_key = os.getenv("QWEN_API_KEY")
open_router_key = os.getenv("OPENROUTER_API_KEY")
deepseek_key = os.getenv("DEEPSEEK_API_KEY")
# ====== 1) 模型配置（OpenAI 兼容） ======
OPENAI_API_KEY = qwen_key
OPENAI_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'  # e.g. DashScope 兼容端点
# 推荐模型（OpenAI）："gpt-4o-mini" / "gpt-4.1-mini"
# 推荐模型（Qwen 兼容端点）："qwen2.5-32b-instruct" 或 "qwen2.5-7b-instruct"
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen-plus-2025-07-28")

if not OPENAI_API_KEY:
    raise RuntimeError("请先设置 OPENAI_API_KEY")

# https://dashscope.aliyuncs.com/compatible-mode/v1
# qwen-plus-2025-07-28
# https://openrouter.ai/api/v1
# openai/gpt-5
# https://api.deepseek.com/v1
# deepseek-reasoner

# qwen3-max qwen-plus-2025-07-28
# llm = ChatOpenAI(
#     model="qwen3-max",          
#     api_key=qwen_key, 
#     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
# )


llm = ChatOpenAI(
    model="deepseek-reasoner",          
    api_key=deepseek_key, 
    base_url="https://api.deepseek.com/v1"
)

# llm = ChatOpenAI(
#     model="openai/gpt-5",          
#     api_key=open_router_key, 
#     base_url="https://openrouter.ai/api/v1"
# )


# ====== 2) 输出数据结构（让代理按此结构吐 JSON） ======
class Job(BaseModel):
    title: str = Field(..., description="岗位名称，如 Java开发工程师/资深Java/后端工程师")
    company: str = Field(..., description="公司名称")
    salary: Optional[str] = Field(None, description="薪资区间，如 20-30K·14薪/25-40K")
    location: Optional[str] = Field(None, description="工作地点/城市/区县")
    experience: Optional[str] = Field(None, description="经验要求，如 3-5年/不限")
    education: Optional[str] = Field(None, description="学历要求，如 本科/大专/不限")
    source_page: Optional[str] = Field(None, description="抓取页面URL用于溯源")

# ====== 3) 抓取任务 Prompt（让代理在页面内操作、滚动并抽取） ======
def build_task(keyword: str, city_hint: str = "全国", max_jobs: int = 30, n: int = 1) -> str:
    schema = Job.model_json_schema()
    return f"""
你是一个网页采集代理。访问 https://www.zhipin.com/web/geek/jobs?ka=header-jobs （BOSS直聘），等待页面加载完成。
搜索结果页面结构：
- 搜索在 div class='job-search-form' , 搜索的输入在 (placeholder="搜索职位、公司")
- 职位结果列表 和 职位详细信息 是左右两列，搜索的职位结果列表 在 div class='job-list-container'，职位列表中每一个职位信息在 class='card-area' ，每个职位详细信息在 div class='job-detail-box'。

在搜索框输入“{keyword}”，城市选择“{city_hint}”（若无法选则默认当前显示城市），执行搜索。
构建一个JSON 数组**，数组元素的 JSON 结构严格遵循下面的 JSON Schema
搜索结果加载完成后，执行{max_jobs}次以下要求操作：
1) 点击职位结果列表中的第{n}个条职位信息，在职位结果列表的右边会加载职位的详细信息。
2) 对每条职位抽取字段：title, company, salary, location, experience, education。
3) 把每条职位提取到的数据放到已经构建的JSON 数组中。
4) n 的值 加1。

输出 JSON 数组。
{json.dumps(schema, ensure_ascii=False, indent=2)}

注意：
- 避免点击“聊天”“投递”等需要登录的操作。
- 尽量不跳转详情页，若需要也可以点开新标签读取信息后返回。
- 请务必输出 **纯 JSON**，不要带任何注释、额外文本或 Markdown。
- 最多抽取 {max_jobs} 条记录。
"""

# ====== 4) 运行代理并解析结果为 CSV ======
def extract_json(text: str) -> List[dict]:
    """
    代理经常会返回解释 + JSON，我们只保留第一个纯 JSON 数组。
    """
    # 尝试抓取第一个 JSON 数组
    m = re.search(r"(\[\s*\{.*?\}\s*\])", text, flags=re.S)
    if not m:
        # 也可能就是纯 JSON
        if text.strip().startswith("[") and text.strip().endswith("]"):
            return json.loads(text)
        raise ValueError("未在代理输出中发现 JSON 数组")
    return json.loads(m.group(1))

def save_csv(rows: List[dict], out_path: str):
    if not rows:
        print("没有数据需要保存")
        return
    keys = ["title", "company", "salary", "location", "experience", "education", "source_page"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in keys})
    print(f"✅ 已保存 CSV: {out_path} (共 {len(rows)} 条)")

async def main():
    keyword = "Java 开发"
    city = "全国"  # 也可用：北京/上海/深圳/杭州 等
    task = build_task(keyword, city, max_jobs=10)

    # 建议设置一个你的本地 Profile 目录，能显著降低被风控概率（已登录更稳）
    PROFILE_DATA_DIR = '/Users/gongwenwei/Library/Application Support/Google/Chrome/Profile 2'
    #os.makedirs(user_data_dir, exist_ok=True)

    # 5) 浏览器与上下文配置：中文、非无头、较大视口、持久化 Profile
    # browser = Browser(
    #     config=BrowserConfig(
    #         headless=False,  # 调试阶段建议可见
    #         chromium_port=None,  # 让 browser-use 自行管理
    #     ),
    #     context_config=BrowserContextConfig(
    #         user_data_dir=user_data_dir,
    #         locale="zh-CN",
    #         viewport={"width": 1440, "height": 900},
    #         geolocation=None,  # 如果需要可填中国城市经纬度
    #         timezone_id="Asia/Shanghai",
    #     ),
    # )

    # config = BrowserConfig(
    #     use_cloud=False,                     # ✅ 禁用云端模式
    #     headless=False,                      # 是否显示浏览器窗口
    #     browser_type="chromium",             # 可选: chromium / firefox / webkit
    #     user_data_dir=user_data_dir,   # 保存登录状态等
    #     viewport={"width": 1440, "height": 900},
    #     slow_mo=100                          # 每个操作之间延迟 (ms)
    # )
    # browser = Browser(config=config)
    # TimeoutError: Event handler browser_use.browser.watchdog_base.BrowserSession.on_BrowserStartEvent#
    # https://github.com/browser-use/browser-use/issues/3196
    # https://developer.chrome.com/blog/remote-debugging-port?hl=zh-cn
    browser = Browser(
        use_cloud=False,
        headless=False,                     # 显示浏览器窗口
        # user_data_dir='~/Library/Application Support/Google/Chrome',
        # profile_directory='Profile 2',
        # viewport={"width": 1440, "height": 900}
    )



    # 6) 创建代理
    agent = Agent(
        task=task,
        browser=browser,
        max_actions=50,          # 给足够的动作步数用于滚动和提取
        max_failures=5,          # 容错
        llm=llm,
        # 下面两个可以让动作更“像人类”，降低被风控风险
        action_delay=1.2,        # 每步之间停顿
        step_by_step=True,       # 让模型解释一步步操作（更稳）
        use_vision=False
    )

    print("🚀 开始任务：", keyword)
    result = await agent.run()  # 0.7.x 同步 API；若你用的是异步请改成 await agent.run()

    # 7) 解析输出
    final_text = result.final_result if hasattr(result, "final_result") else str(result)
    try:
        rows = extract_json(final_text)
    except Exception as e:
        print("❗解析失败，原始输出如下：\n", final_text[:2000])
        raise e

    # 8) 保存 CSV
    out_csv = f"zhipin_{keyword.replace(' ', '')}.csv"
    save_csv(rows, out_csv)

if __name__ == "__main__":
    asyncio.run(main())
