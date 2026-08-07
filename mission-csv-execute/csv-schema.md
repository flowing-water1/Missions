# CSV Schema

固定表头（字段顺序固定）：

```
id,priority,phase,area,title,description,acceptance_criteria,test_mcp,required_skills,required_mcp,review_initial_requirements,review_regression_requirements,dev_state,review_initial_state,review_regression_state,git_state,owner,refs,notes
```

## 字段规格

| 字段 | 格式 | 规则 |
|------|------|------|
| `id` | `<GROUP>-<seq>` | 如 `SPEC-01` 或外部兼容 CSV 的既有 id |
| `priority` | `P0\|P1\|P2` | |
| `phase` | `1\|2\|3...` | 执行阶段序号 |
| `area` | `backend\|frontend\|both\|infra\|review` | `REVIEW-*` 行固定使用 `review` |
| `title` | 一句话标题 | 动词开头，简洁 |
| `description` | 1-2 句 | 边界说明，不写实现细节 |
| `acceptance_criteria` | 分号分隔 | 可验证条件；格式 `WHEN X THEN Y; ref: file:line` |
| `test_mcp` | `PRIMARY` | 主验证模式：`AUTOSERVER\|AUTOFRONTEND\|AUTOE2E\|CONTRACT\|MIGRATION\|MANUAL`（大写）。这里只描述验证类型，不再内嵌具体工具 |
| `required_skills` | `skill(;skill)*` | 执行前必须显式读取并遵循的 skill 名称列表；使用 skill 注册表中的精确名称；无则留空，如 `ui-ux-pro-max;frontend-skill` |
| `required_mcp` | `tool(;tool)*` | 执行与验收阶段必须实际调用的验证工具 id 列表；字段名沿用既有命名，优先填写 MCP，也可填写 `playwright` 这类交互驱动工具；不填 `pytest`、`npm test` 这类通用 runner；无则留空，如 `chrome-devtools;playwright;screenpipe` |
| `review_initial_requirements` | 文本 | 开发过程 Review 要点 |
| `review_regression_requirements` | 文本 | 回归 Review 要点 |
| `dev_state` | 枚举 | `未开始\|进行中\|已完成` |
| `review_initial_state` | 枚举 | `未开始\|进行中\|已完成` |
| `review_regression_state` | 枚举 | `未开始\|进行中\|已完成` |
| `git_state` | 枚举 | `未提交\|已提交` |
| `owner` | 文本 | 默认留空 |
| `refs` | `path:line; path:line` | 入口文件与关键文件 |
| `notes` | 自由文本 | 阻塞信息、决策、元数据 |

## 状态枚举（严格，禁止百分比）

| 字段 | 允许值 | 默认 |
|------|--------|------|
| `dev_state` | `未开始`, `进行中`, `已完成` | `未开始` |
| `review_initial_state` | `未开始`, `进行中`, `已完成` | `未开始` |
| `review_regression_state` | `未开始`, `进行中`, `已完成` | `未开始` |
| `git_state` | `未提交`, `已提交` | `未提交` |

## 编码与文件规则

- 编码：**UTF-8 with BOM**
- 所有字段双引号包裹，内部 `"` 用 `""` 转义
- 换行：CRLF 或 LF，文件内一致

## 路径约定

- `issues/<stem>/<stem>.csv`：approved spec 生成的正式执行 CSV，随完整证据集一起提交
- `issues/*.csv`：legacy 平铺格式，只为恢复和显式输入兼容；新产物不得继续写平铺 CSV
- 显式传入的合法外部 CSV 可位于任意目录；artifact root 是其父目录，是否提交取决于它是否已跟踪或明确属于 `issues/`

## Notes 字段标签约定

| 标签 | 含义 |
|------|------|
| `blocked:<reason>` | 阻塞 |
| `picked_reason:<why>` | 选择原因 |
| `done_at:<date>` | 完成时间 |
| `validation_limited:<reason>` | 测试无法运行 |
| `manual_test:<command>` | 后续手动测试 |
| `skills_used:<skill;skill>` | 实际采用的 skills |
| `mcp_used:<tool;tool>` | 实际调用的 MCP 工具 |
| `mcp_evidence:<tool> <summary>` | MCP 证据摘要，可重复记录 |
| `evidence:<what>` | 替代验证证据 |
| `risk:<low\|medium\|high> <note>` | 风险评估 |
| `assumption:<note>` | 为继续闭环而采用的合理假设 |
| `decision_debt:<note>` | 未阻塞执行、但需要在 review log 中留痕的决策债 |
| `deferred_ledger:<path>` | Deferred Findings 证据台账路径，默认 `<stem>.deferred.json`；台账不控制 issue 状态，相对路径优先按 CSV 所在目录解析 |
| `deferred_findings:<DF-001,DF-002>` | 当前 CSV 行发现或引用的待讨论项；每个 id 必须存在于 deferred ledger |
| `deferred_coverage:<covered>/<open>` | 最终 handoff 已覆盖的开放待讨论项数量；只在最新 REVIEW notes 回填 |
| `review_kind:vision` | `REVIEW-*` 行的文档愿景验收标记 |
| `review_agent_mode:<mode>` | closing review 模式：`reviewer-subagent` / `codex-exec-independent` / `self-review` / `pending` |
| `review_independence:<value>` | `true` / `false` / `pending`；self-review 固定为 `false` |
| `review_requested_model:<model>` | 独立 review 请求的模型，默认 `gpt-5.6-sol` |
| `review_observed_model:<model>` | 仅由 host/session metadata、CLI event stream 或可信 parent runtime 记录；无证据写 `unknown` |
| `review_model_evidence:<source>` | `session-metadata` / `event-stream` / `parent-runtime` / `unknown` |
| `claim_ledger:<path>` | 持久化 claim/evidence ledger JSON 路径；任何 `claims:CLAIM-*` 都必须能在该 JSON 中找到定义。相对路径优先按 CSV 所在目录解析 |
| `claim_coverage:<covered>/<total>` | 源文档可验证 claim 覆盖率 |
| `claim_coverage_status:<status>` | review 对 claim 覆盖的判断：`pending` / `complete` / `gaps` / `unknown` |
| `claims:<CLAIM-001,CLAIM-002>` | 当前 issue 覆盖的 claim id 列表 |
| `evidence_level:<level>` | 当前 issue 最高证据等级：`real_e2e` / `integration` / `unit` / `static` / `mock_allowed` / `limited_allowed` |
| `mock_allowed:<reason>` | 源文档明确允许 mock/fake/dry-run/static 证据的原因 |
| `limited_allowed:<reason>` | 源文档明确允许受限验收的原因 |
| `production_path:<status>` | 是否覆盖生产路径：`covered` / `not_required` / `deferred` / `gap` |
| `out_of_scope:<section>;<reason>` | 源文档中明确不在本轮执行范围内的承诺或章节 |
| `review_result:<result>` | review 结论：`vision_met` / `gaps_found` / `limited_review` |
| `handoff:<path>` | 人类交接文档路径；相对路径优先按 CSV 所在目录解析；`handoff:generation_failed <reason>` 表示自动生成失败、已用兜底渲染，但仍应同时记录兜底文档路径 |
| `handoff_contract:passed` | handoff 已通过 `scripts/check_handoff_contract.py`；该检查包含 `.handoff.md` 命名、同名前缀 CSV、REVIEW notes 的 `handoff:<path>`、以及 markdown 骨架 lint |
| `handoff_contract:failed <reason>` | handoff contract check 重试后仍失败；允许代码交付继续收口，但不得把 review 结论写成 `vision_met`，最终回复必须明说 handoff 不合格 |
| `source_doc:<path>` | 生成 CSV 的批准文档路径 |
| `pr:<id>` | 关联 PR |

### REVIEW notes 分阶段

`REVIEW-*` 行生成时写入：`review_kind:vision`、`source_doc:<path>`（兼容 CSV 可改为 `source_csv:<path>`）、存在的 sidecar 路径、`claim_coverage:<covered>/<total>` 或 `unknown`、`claim_coverage_status:pending`、`review_agent_mode:pending`、`review_independence:pending`、`review_requested_model:gpt-5.6-sol`、`review_observed_model:unknown`、`review_model_evidence:unknown`。

实际 mode、独立性、模型证据、`review_result`、`handoff`、`handoff_contract`、`handoff_humanized`、`deferred_coverage`、`validation_limited` 等标签由 `mission-csv-execute` 执行 REVIEW 后回填。

## Deferred Findings sidecar

`<artifact-root>/<stem>.deferred.json` 只保存执行中发现、但不属于当前批准范围的证据。CSV 仍是唯一任务状态源；sidecar 不得决定 issue 是否完成，也不得用来延期当前验收。

```json
{
  "schema_version": 1,
  "csv": "<stem>.csv",
  "findings": [
    {
      "id": "DF-001",
      "kind": "deferred_improvement",
      "status": "open",
      "title": "自然语言标题",
      "summary": "观察到的现象",
      "source_issue_ids": ["DEV-01"],
      "evidence_refs": ["trace/test/path:line"],
      "why_deferred": "为什么不影响当前批准范围",
      "discussion_question": "任务结束后需要用户决定什么"
    }
  ]
}
```

- `kind` 只允许 `deferred_improvement`（范围外的质量或架构改进）和 `future_decision`（当前范围完成后的产品或架构选择）。
- `status` 只允许 `open`、`promoted`、`dismissed`。`promoted` 表示用户讨论后已转成正式任务；本轮 mission 不自动创建该任务。
- 当前 scope 或 acceptance gap、失败验收、缺失接线、错误声明都不得写进 sidecar，必须现在修复或追加正式 follow-up issue。
- machine ledger 保留 id、trace、路径和结构化字段原文，不经过 `humanizer-zh`。最终 handoff 的可见正文才做人话润色。
- 运行 `python scripts/validate_deferred_ledger.py <csv-path> --workdir <repo-root>` 校验路径、引用、分类和覆盖计数。
