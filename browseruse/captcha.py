"""
Goal: Automates CAPTCHA solving on a demo website.


Simple try of the agent.
@dev You need to add OPENAI_API_KEY to your environment variables.
NOTE: captchas are hard. For this example it works. But e.g. for iframes it does not.
for this example it helps to zoom in.
"""

import asyncio
import os
import sys
from browser_use import Agent, ChatOpenAI

from dotenv import load_dotenv
load_dotenv()
qwen_key = os.getenv("QWEN_API_KEY")
open_router_key = os.getenv("OPENROUTER_API_KEY")
deepseek_key = os.getenv("DEEPSEEK_API_KEY")


llm = ChatOpenAI(
    model="openai/gpt-5",          
    api_key=open_router_key, 
    base_url="https://openrouter.ai/api/v1"
)


async def main():

	agent = Agent(
		task='go to https://captcha.com/demos/features/captcha-demo.aspx and solve the captcha',
		llm=llm,
	)
	await agent.run()
	input('Press Enter to exit')


if __name__ == '__main__':
	asyncio.run(main())