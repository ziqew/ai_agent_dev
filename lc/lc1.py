import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI  # ✅ 改成 ChatOpenAI
from langchain_community.utilities import SerpAPIWrapper  # ✅ 0.3.29 正确导入路径
from langchain_community.utilities import WikipediaAPIWrapper

from langchain.chains import LLMMathChain
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.prompts import PromptTemplate

load_dotenv()
openrouter_key = os.environ["OPENROUTER_API_KEY"]
openrouter_base_url = os.environ["OPENROUTER_BASE_URL"]
print(openrouter_key)
serpapi_api_key = os.environ["SERPAPI_API_KEY"]
# === 初始化模型 ===
llm = ChatOpenAI(
    base_url=openrouter_base_url,
    api_key=openrouter_key,
    temperature=0
)

# === 搜索与数学工具 ===
search = SerpAPIWrapper(serpapi_api_key=serpapi_api_key)
math = LLMMathChain.from_llm(llm=llm, verbose=True)
wiki = WikipediaAPIWrapper(lang="en")
tools = [
    Tool(
        name="Wikipedia Search",
        func=wiki.run,
        description="搜索维基百科获取事实性信息"
    ),
    Tool(name="Calculator", func=math.run, description="数学计算")
]
# tools = [
#     Tool(
#         name="Search",
#         func=search.run,
#         description="用于搜索信息"
#     ),
#     Tool(
#         name="Calculator",
#         func=math.run,
#         description="用于数学计算"
#     ),
# ]
template = """
你是一个知识严谨的足球专家。
请严格基于2010年FIFA世界杯（南非举办）相关信息回答问题。
忽略任何其他年份（如1930、1950等）内容。
{input}
"""

prompt = PromptTemplate.from_template(template)
# === 初始化 ReAct Agent ===
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # ✅ 新枚举方式
    verbose=True,
    prompt=prompt,
    prompt_prefix="请严格依据年份过滤结果，只返回2010年相关内容。"
)

# === 执行 ===
response = agent.run("2010年世界杯冠军是谁的主教练？")
print(response)





