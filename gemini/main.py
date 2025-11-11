# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import os

from agent import BrowserAgent
from computers import BrowserbaseComputer, PlaywrightComputer

from dotenv import load_dotenv

load_dotenv()
PLAYWRIGHT_SCREEN_SIZE = (1440, 900)

os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")

# def main() -> int:
#     parser = argparse.ArgumentParser(description="Run the browser agent with a query.")
#     parser.add_argument(
#         "--query",
#         type=str,
#         required=True,
#         help="The query for the browser agent to execute.",
#     )

#     parser.add_argument(
#         "--env",
#         type=str,
#         choices=("playwright", "browserbase"),
#         default="playwright",
#         help="The computer use environment to use.",
#     )
#     parser.add_argument(
#         "--initial_url",
#         type=str,
#         default="https://www.google.com",
#         help="The inital URL loaded for the computer.",
#     )
#     parser.add_argument(
#         "--highlight_mouse",
#         action="store_true",
#         default=False,
#         help="If possible, highlight the location of the mouse.",
#     )
#     parser.add_argument(
#         "--model",
#         default='gemini-2.5-computer-use-preview-10-2025',
#         help="Set which main model to use.",
#     )
#     args = parser.parse_args()

#     if args.env == "playwright":
#         env = PlaywrightComputer(
#             screen_size=PLAYWRIGHT_SCREEN_SIZE,
#             initial_url=args.initial_url,
#             highlight_mouse=args.highlight_mouse,
#         )
#     elif args.env == "browserbase":
#         env = BrowserbaseComputer(
#             screen_size=PLAYWRIGHT_SCREEN_SIZE,
#             initial_url=args.initial_url
#         )
#     else:
#         raise ValueError("Unknown environment: ", args.env)

#     with env as browser_computer:
#         agent = BrowserAgent(
#             browser_computer=browser_computer,
#             query=args.query,
#             model_name=args.model,
#         )
#         agent.agent_loop()
#     return 0
def main() -> int:
    
    highlight_mouse = False
    model ='gemini-2.5-computer-use-preview-10-2025'
    query = """
    任务目标：
        在携程官网查询 2025年10月25日 从苏州到南京的火车票信息，
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
        2. 确认页面加载完成,检查用户是否登录，如果用户没有登录，等待用户登录
        3. 在出发地输入框中输入 “苏州”
        4. 在到达地输入框中输入 “南京”
        5. 选择出发日期 “2025-10-25”
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
    initial_url = 'https://trains.ctrip.com/'
    env = PlaywrightComputer(
            screen_size=PLAYWRIGHT_SCREEN_SIZE,
            initial_url=initial_url,
            highlight_mouse=highlight_mouse,
        )
    with env as browser_computer:
        agent = BrowserAgent(
            browser_computer=browser_computer,
            query=query,
            model_name=model,
        )
        agent.agent_loop()
    return 0   

if __name__ == "__main__":
    main()
