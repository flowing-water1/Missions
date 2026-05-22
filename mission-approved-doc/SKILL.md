---
name: mission-approved-doc
description: Use when the input is a user-approved design doc or implementation plan and the agent needs to turn it into an executable issues CSV before handing off to CSV execution.
---

你现在是「批准文档执行器」。

# 目标

把一个**已获用户批准**的设计文档或计划文档转换为 `issues/*.csv`，然后交给 `mission-csv-execute` 闭环执行。

# 流程

## Phase 1：批准门验证（HARD STOP）

1. 确认输入文档存在
2. 完整读取文档
3. 确认用户已经明确批准该文档作为执行输入
4. 若未批准则硬停，只输出：
   ```
   文档 <path> 尚未获用户批准。
   请先明确批准后再执行。
   ```
5. 未经批准绝不执行任何代码变更

## Phase 2：读取与抽取

优先读取文档本体，再按需抽取以下信息：

| 来源 | 必须 | 提取内容 |
|------|------|----------|
| 设计文档 / 计划文档正文 | 是 | Goal, scope, constraints, affected files, task structure |
| 显式 testing / validation 章节 | 重要 | 验收口径、命令、风险点 |
| 与文档直接关联的 code/file refs | 重要 | `refs`, `area`, `required_mcp` 推断 |

字段抽取与拆分规则详见 `doc-field-mapping.md`。

## Phase 3：生成 CSV

生成文件：`issues/<YYYY-MM-DD_HH-mm-ss>-<topic>.csv`

关键规则：

- 正式任务 CSV 固定放在 `issues/`
- 使用标准 CSV schema（见 `mission-csv-execute/csv-schema.md`）
- `acceptance_criteria` 优先从文档里的 validation / testing / success criteria 提取
- **原子性约束**：单个 issue 必须是一个可独立验证、独立提交的原子变更
- `required_skills` 与 `required_mcp` 必须在生成阶段显式写全
- `refs` 必须至少包含 1 个 `path:line`
- 在普通执行 issue 之后，必须追加一条 `REVIEW-01` 作为首轮文档愿景验收；该行必须包含从源文档抽取的任务专属 claim/evidence 检查项，不能只写通用套话
- 初始化状态：`未开始` / `未提交`

### `REVIEW-01` 行规则

`REVIEW-01` 是审计事件，不是普通实现任务。

生成 `REVIEW-01` 时，先从批准文档中抽取用户真正承诺的结果，并写进 review 条件：

- 若文档声明完成某个真实行为、真实副作用、真实集成、真实迁移、真实发送、真实同步、可见交互或端到端流程，review 条件必须检查证据是否支撑同等级声明
- 若交付只使用 mock、fixture、stub、dry-run、scaffold、字符串检查或静态验证，review 条件必须要求它被如实标注，且不得冒充真实完成
- 若测试或外部验证无法运行，review 条件必须检查是否记录 `validation_limited` / `manual_test` / `risk`，不得用替代假路径伪装通过
- `review_regression_requirements` 必须包含 2-4 条来自源文档的任务专属检查项；如果无法抽取，至少写明要审查 claim/evidence 是否一致

建议字段：

| 字段 | 值 |
|------|----|
| `id` | `REVIEW-01` |
| `priority` | `P0` |
| `phase` | 最后阶段序号 |
| `area` | `review` |
| `title` | `Review documented vision against delivered work` |
| `description` | `Use a same-model sub-agent review to compare approved-doc claims with delivered behavior, evidence level, CSV state, validation evidence, and review log.` |
| `acceptance_criteria` | `WHEN all non-review issues before this row are closed THEN run same-model sub-agent review against source-specific claim/evidence checks; WHEN gaps or overstated claims are found THEN append follow-up issues and REVIEW-02; WHEN no gaps remain THEN close the CSV.` |
| `test_mcp` | `MANUAL` |
| `required_skills` | `superpowers:requesting-code-review` |
| `required_mcp` | 留空，除非文档本身要求浏览器或外部验证 |
| `review_initial_requirements` | `Verify all prior non-review rows are closed before running this review.` |
| `review_regression_requirements` | `Run same-model sub-agent review against approved doc goals, non-goals, acceptance criteria, delivered diff, validation evidence, prior review logs, and source-specific claim/evidence alignment checks.` |
| `refs` | `<doc-path>:1` |
| `notes` | `review_kind:vision; review_agent:same-model-sub-agent; source_doc:<doc-path>` |

## Phase 4：生成后摘要

```
生成完成
- 快照: issues/<timestamp>-<topic>.csv
- 来源: <doc-path>
- Issues: N 条（含 REVIEW-01）
- P0 任务: M 条
- 下一步: 进入闭环执行
```

## Phase 5：委托执行

直接进入 `mission-csv-execute` 模式，以刚生成的 CSV 为输入，开始闭环执行。
