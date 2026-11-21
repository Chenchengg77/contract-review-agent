"""最小连通性测试：确认 .env 配置正确、API 能通。

对应 Day1 的「裸调 API」，用来验证环境而不是业务代码。
运行：python scripts/smoke_test.py
"""

import sys
from pathlib import Path

# 让 `import config` 在从任意目录运行时都能找到项目根的 config.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI

import config

client = OpenAI(
    api_key=config.require_api_key(),
    base_url=config.DEEPSEEK_BASE_URL,
)

resp = client.chat.completions.create(
    model=config.MODEL,
    messages=[
        {"role": "system", "content": "你是简洁的助手，回答不超过一句话。"},
        {"role": "user", "content": "用一句话说明什么是合同审查。"},
    ],
    temperature=0,
)

print("回答:", resp.choices[0].message.content)
u = resp.usage
print(
    f"tokens: prompt={u.prompt_tokens} completion={u.completion_tokens} "
    f"total={u.total_tokens}"
)
print("SMOKE OK")
