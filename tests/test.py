"""
示例脚本：模拟一次失败的业务逻辑，方便触发 auto-bug CLI。

运行方式：
    python test.py --data missing.json

脚本会尝试读取 JSON 文件、计算订单总额。若文件缺失或字段不合法，
它会抛出异常并打印堆栈，供 auto-bug ingest 命令生成缺陷记录。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List


def load_orders(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(f"订单文件不存在: {path}")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def calc_total(orders: List[dict]) -> float:
    total = 0.0
    for idx, order in enumerate(orders, start=1):
        if "amount" not in order:
            raise KeyError(f"第 {idx} 条订单缺少 amount 字段: {order}")
        if order["amount"] < 0:
            raise ValueError(f"第 {idx} 条订单金额为负: {order}")
        total += float(order["amount"])
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="订单金额合计示例脚本")
    parser.add_argument("--data", type=Path, required=True, help="订单数据 JSON 文件路径")
    args = parser.parse_args()

    orders = load_orders(args.data)
    total = calc_total(orders)
    print(f"订单总额: {total:.2f}")


if __name__ == "__main__":
    main()
