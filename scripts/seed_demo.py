"""生成演示数据：批量用户 + 审查记录（直接写库，不调用 LLM，不花 token）。

用法：python scripts/seed_demo.py
注意：这是「演示数据」，不是真实审查结果，用于展示统计/看板。
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from src import auth  # noqa: E402

N_USERS = 8
N_REVIEWS = 120
PASSWORD = "demo123456"
CATEGORIES = ["买卖", "租赁", "承揽", "服务", "建设", "其他"]
FOCUS_POOL = ["关注付款与违约金", "关注责任上限", "关注保密与知识产权", "关注交付与验收", ""]


def main() -> None:
    auth.init_db()

    # 1) 用户
    user_ids: list[int] = []
    for i in range(1, N_USERS + 1):
        name = f"demo{i:02d}"
        try:
            u = auth.create_user(name, PASSWORD)
            user_ids.append(u["id"])
        except ValueError:
            existing = next((r for r in auth.list_users() if r["username"] == name), None)
            if existing:
                user_ids.append(existing["id"])

    # 2) 偏好（前 5 个用户随机设置）
    for uid in user_ids[:5]:
        auth.set_preferences(uid, random.choice(CATEGORIES), random.choice(FOCUS_POOL))

    # 3) 审查记录
    files = [f.name for f in config.RAW_DIR.glob("*.docx") if not f.name.startswith("~$")]
    if not files:
        print("没有合同文件，跳过")
        return
    now = time.time()
    with auth._db() as c:  # noqa: SLF001
        for _ in range(N_REVIEWS):
            c.execute(
                "INSERT INTO reviews(user_id, filename, high, mid, low, created_at) "
                "VALUES(?,?,?,?,?,?)",
                (
                    random.choice(user_ids),
                    random.choice(files),
                    random.randint(0, 6),
                    random.randint(0, 8),
                    random.randint(0, 6),
                    now - random.randint(0, 30 * 86400),
                ),
            )

    print(f"完成：{len(user_ids)} 个用户（密码 {PASSWORD}），{N_REVIEWS} 条演示审查记录")


if __name__ == "__main__":
    main()
