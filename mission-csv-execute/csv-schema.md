# CSV Schema

固定表头（字段顺序固定）：

```
id,priority,phase,area,title,description,acceptance_criteria,test_mcp,required_skills,required_mcp,review_initial_requirements,review_regression_requirements,dev_state,review_initial_state,review_regression_state,git_state,owner,refs,notes
```

## 字段规格

| 字段 | 格式 | 规则 |
|------|------|------|
| `id` | `<GROUP>-<seq>` | 如 `SPEC-01`（approved doc）、`PLAN-01`（approved plan）或 `01`（long task） |
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

- `issues/*.csv`：已批准设计/计划文档生成的正式执行 CSV，默认随代码一起提交
- `.mission/*.csv`：长任务生成的本地执行 CSV，默认不提交，仅用于恢复和状态追踪

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
| `review_kind:vision` | `REVIEW-*` 行的文档愿景验收标记 |
| `review_agent:same-model-sub-agent` | 兼容旧 CSV 的意图标签：要求优先使用同模型独立 reviewer；实际执行方式以 `review_agent_mode` 为准 |
| `review_agent_mode:<mode>` | 实际 review 执行模式：`direct-spawn-agent` / `codex-exec-subagent` / `codex-exec-independent` / `codex-review-diff-only` / `main-session-fallback` / `pending` |
| `review_independence:<level>` | review 独立性：`strong` / `medium` / `weak` / `pending` |
| `review_actual_model:<model>` | reviewer 实际模型；无法确认时写 `unknown` 并同时写 `validation_limited:model parity unknown` |
| `claim_ledger:<path>` | 持久化 claim/evidence ledger JSON 路径；任何 `claims:CLAIM-*` 都必须能在该 JSON 中找到定义 |
| `claim_coverage:<covered>/<total>` | 源文档可验证 claim 覆盖率 |
| `claim_coverage_status:<status>` | review 对 claim 覆盖的判断：`pending` / `complete` / `gaps` / `unknown` |
| `claims:<CLAIM-001,CLAIM-002>` | 当前 issue 覆盖的 claim id 列表 |
| `evidence_level:<level>` | 当前 issue 最高证据等级：`real_e2e` / `integration` / `unit` / `static` / `mock_allowed` / `limited_allowed` |
| `mock_allowed:<reason>` | 源文档明确允许 mock/fake/dry-run/static 证据的原因 |
| `limited_allowed:<reason>` | 源文档明确允许受限验收的原因 |
| `production_path:<status>` | 是否覆盖生产路径：`covered` / `not_required` / `deferred` / `gap` |
| `out_of_scope:<section>;<reason>` | 源文档中明确不在本轮执行范围内的承诺或章节 |
| `review_result:<result>` | review 结论：`vision_met` / `gaps_found` / `limited_review` |
| `handoff:<path>` | 人类交接文档路径；`handoff:generation_failed <reason>` 表示自动生成失败、已用兜底渲染；`handoff:lint_failed <缺项>` 表示结构 lint 未通过、重生成后仍残缺、已留标记放行 |
| `source_doc:<path>` | 生成 CSV 的批准文档路径 |
| `pr:<id>` | 关联 PR |

### REVIEW notes 分阶段

`REVIEW-*` 行生成时只需要写入初始标签：`review_kind:vision`、`source_doc:<path>`、`claim_ledger:<path>`、`claim_coverage:<covered>/<total>`、`claim_coverage_status:pending`、`review_agent_mode:pending`、`review_independence:pending`。`review_agent:same-model-sub-agent` 可保留为兼容旧 CSV 的意图标签，但不能替代 `review_agent_mode`。

`review_actual_model`、`review_result`、`handoff`、`handoff_humanized`、`validation_limited` 等标签由 `mission-csv-execute` 执行 REVIEW 后回填。生成阶段不预填这些标签，不算 schema 缺失。
