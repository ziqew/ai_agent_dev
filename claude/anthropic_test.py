import anthropic
import os
from dotenv import load_dotenv

load_dotenv()
zenmux_key = os.environ["ZENMUX_API_KEY"]
print("zenmux_key", zenmux_key)
zenmux_base_url = os.environ["ZENMUX_BASE_URL"]

## 1. 初始化 anthropic 客户端
client = anthropic.Anthropic(
    # 替换为你从 ZenMux 用户控制台获取的 API Key
    api_key=zenmux_key, 
    # 3. 将基础 URL 指向 ZenMux 端点
    base_url=zenmux_base_url
)
message = client.messages.create(
    model="anthropic/claude-3.5-sonnet",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "生命的意义是什么？"}
    ]
)
print(message.content)