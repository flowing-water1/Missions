---
name: mission-doc-route
description: Use when the input is a markdown document and the agent must decide whether it belongs on the approved-doc execution path or the long-task execution path.
---

你现在是「文档路由器」。

# 目标

输入一个 `.md` 文档，判断应该走哪条执行路径，然后委托给对应的 skill。

# 流程

## Step 1：读取文档

完整读取用户传入的 `.md` 文件。

## Step 2：判断范围

评估文档是否涉及：

| 信号 | 路径 |
|------|------|
| 文档位于 `docs/superpowers/specs/` 或 `docs/superpowers/plans/` | → Approved Doc |
| 文档本身定义了明确 scope / tasks / acceptance / validation | → Approved Doc |
| 用户明确说“这个文档已经批准，直接执行” | → Approved Doc |
| 复杂任务说明 / 调查结论 / plan 文档 | → Long Task |
| 已有分析报告 / bug 调查 | → Long Task |

## Step 3：委托

### Approved Doc 路径
1. 确认该文档应作为正式执行输入，而不是普通调查材料
2. 确认用户已经批准该文档作为执行输入
3. 委托给 `mission-approved-doc`

### Long Task 路径
1. 委托给 `mission-long-task`，以文档为任务分解的上下文源

# 不确定时

如果无法明确判断，默认走 **Long Task 路径**（更轻量，风险更低）。
用户可以随时明确要求“把这个文档当批准后的执行文档处理”。
