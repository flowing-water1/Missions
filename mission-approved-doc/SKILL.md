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

## Phase 2.5：确认执行范围

如果源文档包含多个 phase / block / stage / milestone 划分：

1. 检查用户触发时是否指定了范围（如"只做 phase 1"、"执行 Block A"、"先做到 worker 能跑"）
2. 若已指定 → 记录为 `execution_scope`，后续覆盖率扫描只检查该范围内的承诺
3. 若未指定 → `execution_scope` = 文档全文，覆盖率扫描检查整个 spec 的所有可验证承诺
4. 将确认的 `execution_scope` 写入 CSV 文件的第一个 issue 的 `notes` 字段：`execution_scope:<范围描述>`

覆盖率扫描的边界以此为准，不越界。

## Phase 2.6：抽取 Claim/Evidence Ledger

在生成 issue 前，先从 `execution_scope` 中抽取一张 claim/evidence 账本，并随 CSV 同目录落盘为 `issues/<csv-basename>.claims.json`。CSV notes 只保存 claim id 和 `claim_ledger:<path>` 引用；不得只写 `claims:CLAIM-*` 而不持久化定义。

每条 claim 至少包含：

| 字段 | 含义 |
|------|------|
| `claim_id` | `CLAIM-001` 递增 |
| `source_ref` | 源文档 `path:line` |
| `promise` | 可验证承诺本体 |
| `production_path_required` | 是否要求启动注册、API、worker、agent tool、consumer、真实 provider、E2E 等生产路径 |
| `covered_by` | 负责实现/验证的 issue id，生成后回填 |
| `evidence_required` | `real_e2e` / `integration` / `unit` / `static` / `mock_allowed` / `limited_allowed` |
| `status` | `pending` / `covered` / `gap` / `out_of_scope` |

只抽取可验证承诺：WHEN/MUST/SHALL、状态枚举、字段定义、启动行为、消费关系、错误处理、API 契约、真实副作用、显式 non-goal 边界。不要把背景、愿景口号、解释性段落当 claim。

`*.claims.json` 必须使用以下结构：

```json
{
  "source_doc": "<doc-path>",
  "csv": "<csv-file-name>",
  "execution_scope": "<scope>",
  "claim_coverage": {"covered": 0, "total": 0, "status": "pending"},
  "claims": [
    {
      "claim_id": "CLAIM-001",
      "source_ref": "<doc-path>:<line>",
      "promise": "<可验证承诺原文或忠实改写>",
      "covered_by": ["ISSUE-01"],
      "evidence_required": "integration",
      "production_path_required": true,
      "status": "pending"
    }
  ]
}
```

## Phase 3：生成 CSV

`mission-csv-execute/csv-schema.md` 是唯一固定 CSV schema。`mission-approved-doc` 只负责把批准文档映射成这套 19 列表头下的行数据，不定义第二套表头。

生成文件：`issues/<YYYY-MM-DD_HH-mm-ss>-<topic>.csv`

关键规则：

- 正式任务 CSV 固定放在 `issues/`
- 使用标准 CSV schema（见 `mission-csv-execute/csv-schema.md`）
- `acceptance_criteria` 优先从文档里的 validation / testing / success criteria 提取
- **原子性约束**：单个 issue 必须是一个可独立验证、独立提交的原子变更
- `required_skills` 与 `required_mcp` 必须在生成阶段显式写全
- `refs` 必须至少包含 1 个 `path:line`
- **闭环路径约束**：生成组件 issue 后，必须按 `doc-field-mapping.md` 闭环路径规则扫描跨模块消费关系、启动注册、工具注册、flow 注入点，为每个被文档承诺的连接点生成独立接线 issue
- 在普通执行 issue 之后，必须追加一条 `REVIEW-01` 作为首轮文档愿景验收；该行必须包含从源文档抽取的任务专属 claim/evidence 检查项，不能只写通用套话
- 初始化状态：`未开始` / `未提交`

### Claim 覆盖率扫描（HARD — 在追加 REVIEW-01 之前执行）

生成所有组件 issue 和接线 issue 后，执行以下覆盖率检查：

1. 回读 Phase 2.6 的 claim ledger
2. 对每条 claim，检查是否至少被一个 issue 的 `acceptance_criteria` 显式覆盖
3. 若 claim 要求生产路径，检查是否存在独立接线 issue 或该 issue 的 AC 明确覆盖生产路径
4. 检查每条 claim 的 `evidence_required` 是否能被对应 issue 的 `test_mcp` / `required_mcp` / review 条件支撑
5. 未覆盖的 claim 按以下规则处理：
   - 在 `execution_scope` 内 → **补 issue** 或追加到现有 issue 的 AC
   - 在 `execution_scope` 外（文档明确标注为 non-goal / future / deferred / 超出用户指定范围）→ 在 CSV 末尾 notes 记录 `out_of_scope:<doc-section>;<reason>`
   - 无法确定归属 → 补 issue 标 `P2`，交给 REVIEW-01 判断
6. 覆盖率扫描完成后，在生成摘要中报告：`Claim 覆盖: X/Y 条已覆盖，P 条生产路径已覆盖，Z 条标注 out_of_scope`
7. 将最终 claim/evidence ledger 写入 `<csv-basename>.claims.json`；若任何 CSV notes 出现 `claims:CLAIM-*`，同一 notes 必须包含 `claim_ledger:<path>`

在 CSV 中记录账本时使用压缩 notes，不要把整篇 spec 复制进 CSV。推荐格式：

```text
claim_ledger:issues/<csv-basename>.claims.json; claims:CLAIM-001,CLAIM-002; claim_coverage:X/Y; claim_coverage_status:pending; evidence_level:integration; production_path:covered
```

### `REVIEW-01` 行规则

`REVIEW-01` 是审计事件，不是普通实现任务。

下表只列 `REVIEW-01` 需要覆盖的字段取值，不是完整 CSV 表头。实际 CSV 仍必须包含 `csv-schema.md` 中的全部 19 列；未列出的状态字段按标准默认值初始化：`dev_state=未开始`、`review_initial_state=未开始`、`review_regression_state=未开始`、`git_state=未提交`、`owner=`。

生成 `REVIEW-01` 时，先从批准文档中抽取用户真正承诺的结果，并写进 review 条件：

- 若文档声明完成某个真实行为、真实副作用、真实集成、真实迁移、真实发送、真实同步、可见交互或端到端流程，review 条件必须检查证据是否支撑同等级声明
- 若交付只使用 mock、fixture、stub、dry-run、scaffold、字符串检查或静态验证，review 条件必须要求它被如实标注，且不得冒充真实完成
- 若测试或外部验证无法运行，review 条件必须检查是否记录 `validation_limited` / `manual_test` / `risk`，不得用替代假路径伪装通过
- `review_regression_requirements` 必须包含 2-4 条来自源文档的任务专属检查项，并要求逐条审查 claim/evidence ledger；如果无法抽取，至少写明要审查 claim/evidence 是否一致

建议字段：

| 字段 | 值 |
|------|----|
| `id` | `REVIEW-01` |
| `priority` | `P0` |
| `phase` | 最后阶段序号 |
| `area` | `review` |
| `title` | `Review documented vision against delivered work` |
| `description` | `Use the strongest available independent review to compare approved-doc claims with delivered behavior, evidence level, CSV state, validation evidence, and review log.` |
| `acceptance_criteria` | `WHEN all non-review issues before this row are closed THEN run the strongest available independent review against source-specific claim/evidence checks; WHEN gaps or overstated claims are found THEN append follow-up issues and REVIEW-02; WHEN review is limited THEN append REVIEW-02 for a later independent rerun, mark REVIEW-01 complete with review_result:limited_review, and do not close the CSV or mark vision_met; WHEN no gaps remain and review is not limited THEN close the CSV.` |
| `test_mcp` | `MANUAL` |
| `required_skills` | `superpowers:requesting-code-review` |
| `required_mcp` | 留空，除非文档本身要求浏览器或外部验证 |
| `review_initial_requirements` | `Verify all prior non-review rows are closed before running this review.` |
| `review_regression_requirements` | `Run strongest available independent vision review against approved doc goals, non-goals, claim/evidence ledger, acceptance criteria, delivered diff, validation evidence, prior review logs, and source-specific claim/evidence alignment checks.` |
| `refs` | `<doc-path>:1` |
| `notes` | `review_kind:vision; review_agent_mode:pending; review_independence:pending; source_doc:<doc-path>; claim_ledger:issues/<csv-basename>.claims.json; claim_coverage:<X/Y>; claim_coverage_status:pending` |

兼容旧 CSV 时可保留 `review_agent:same-model-sub-agent`，但它只是“优先使用同模型独立 reviewer”的意图标签。实际执行模式由 `mission-csv-execute` 写入 `review_agent_mode:<mode>`。

## Phase 4：生成后摘要

```
生成完成
- 快照: issues/<timestamp>-<topic>.csv
- 来源: <doc-path>
- Issues: N 条（含 REVIEW-01）
  - 组件 issue: X 条
  - 接线 issue: Y 条
- P0 任务: M 条
- Claim 覆盖: A/B 条 spec 承诺已覆盖，P 条生产路径已覆盖，C 条标注 out_of_scope
- Claim ledger: issues/<timestamp>-<topic>.claims.json
- 下一步: 进入闭环执行
```

## Phase 5：委托执行

直接进入 `mission-csv-execute` 模式，以刚生成的 CSV 为输入，开始闭环执行。
