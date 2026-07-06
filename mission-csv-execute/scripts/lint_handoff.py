#!/usr/bin/env python3
"""结构 lint：检查 handoff.md 是否按 template 走通，而非审内容质量。

理念（对齐 superpowers verification-before-completion）：
不信产出者自报，用一道独立的机械检查卡产物骨架。
卡得宽松——只要出现规范化结构信号，基本就意味着 reviewer 走通了 template；
内容好不好是 reviewer 的事，这里只拦"压成三段摘要"这类明显脱模的残件。

退出码：
  0 = 通过（骨架齐全）
  1 = 不合格（打印缺哪几块到 stderr）
  2 = 用法/读文件错误
"""
import argparse
import re
import sys


# 审计黑话黑名单：这些属于 review.md，不该出现在面向人的 handoff 里
AUDIT_JARGON = [
    "scope checked",
    "evidence checked",
    "claim coverage",
    "vision_met",
]


def lint(text: str) -> list[str]:
    """返回缺失项列表；空列表表示通过。卡得宽松，只认硬信号。"""
    missing: list[str] = []

    # 1. 施工交工单标题（template 第一行特征）
    if "施工交工单" not in text:
        missing.append("标题缺 '施工交工单'（template 顶部标题）")

    # 2. 独立性头：独立性 / 日期 任一行
    if not re.search(r"独立性\s*[:：]", text):
        missing.append("缺独立性头（'独立性:' 行）")

    # 3. 五层骨架的 ## 标题——宽松：命中任意 2 个即认为按结构走了
    section_markers = ["总结", "对账", "施工细节", "验证情况", "后续"]
    hit = [m for m in section_markers if re.search(rf"^#{{1,3}}\s*.*{m}", text, re.M)]
    if len(hit) < 2:
        missing.append(
            f"五层骨架 ## 标题命中不足（{len(hit)}/5，至少 2 个）："
            f"命中 {hit or '无'}"
        )

    # 4. 第二层对账：有表格（| ... |）即可，不查表内容
    if "|" not in text or text.count("|") < 4:
        missing.append("缺对账表（第二层 spec 目标逐条对账的 | 表格）")

    # 5. 审计黑话黑名单
    lower = text.lower()
    hit_jargon = [w for w in AUDIT_JARGON if w in lower]
    if hit_jargon:
        missing.append(f"出现 review 审计黑话（应在 review.md 不在 handoff）：{hit_jargon}")

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="handoff.md 结构 lint（宽松）")
    parser.add_argument("path", help="handoff.md 路径")
    args = parser.parse_args()

    try:
        with open(args.path, encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        sys.stderr.write(f"lint_handoff: 读文件失败：{exc}\n")
        return 2

    missing = lint(text)
    if missing:
        sys.stderr.write(f"lint_handoff: {args.path} 不合格，缺以下骨架：\n")
        for m in missing:
            sys.stderr.write(f"  - {m}\n")
        return 1

    sys.stdout.write(f"lint_handoff: {args.path} 结构通过\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
