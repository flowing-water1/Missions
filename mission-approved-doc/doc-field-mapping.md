# Approved Doc -> CSV 字段映射

`mission-csv-execute/csv-schema.md` 是唯一固定 CSV schema。本文件只说明批准文档如何映射到那套 19 列表头，不定义第二套 CSV 表头。

## 适用输入

- `docs/superpowers/specs/*.md`
- `docs/superpowers/plans/*.md`
- 任何已获用户批准、且正文能清晰定义 scope / tasks / validation 的 Markdown 文档

## From design doc

| 章节 / 结构 | 提取内容 | CSV 字段 |
|-------------|----------|----------|
| `## Problem` / `## Why` / `## Goal` | 背景、目标 | 上下文理解（不直接入 CSV） |
| `## Scope` / `## Non-Goals` | 范围边界 | `description`, `notes` |
| `## Architecture` / `## Design` / `## Components` | 技术分层、关键模块 | `phase`, `area`, `refs` |
| `## Constraints` / `## Risks` | 关键约束与风险 | `priority`, `review_regression_requirements`, `notes` |
| `## Testing` / `## Validation` / `## Success Criteria` | 验收口径 | `acceptance_criteria`, `test_mcp` |

## From implementation plan

| 结构 | 提取内容 | CSV 字段 |
|------|----------|----------|
| `### Task N` / `## Task N` | 阶段分组 | `phase`, `id` 前缀 |
| `**Files:**` | 影响文件 | `refs`, `area` |
| `- [ ] Step ...` | 原子工作项 | `title`, `description` |
| `Run:` / `Expected:` | 验证命令 | `acceptance_criteria`, `review_initial_requirements` |
| Commit / Review 说明 | 提交和回归边界 | `review_regression_requirements`, `notes` |

## Granularity rules

1. 若计划文档已有 `Task` / `Step` 结构，优先按可独立提交的任务单元生成 issue
2. 若只有设计文档，没有显式任务结构，则按独立模块、独立验证路径拆分 3-10 条 issue
3. 一个 issue 只能对应一条清晰的验证路径；若两个工作项拥有不同失败路径或不同回归面，必须拆开
4. 普通 issue 生成完毕后，固定追加 `REVIEW-01`；后续 review 轮次只由 `mission-csv-execute` 在发现缺口时追加

## Claim / Evidence Ledger

生成 issue 前先抽取可验证 claim；CSV 生成质量以 claim 覆盖为准，不以 issue 数量为准。

| Spec 信号 | claim 类型 | 生成要求 |
|-----------|------------|----------|
| WHEN/MUST/SHALL/必需/必须 | 行为承诺 | 至少一个 issue 的 AC 显式覆盖 |
| 状态枚举/字段定义/API schema | 契约承诺 | AC 写字段、状态、错误码或 schema 验证 |
| 启动行为/注册/consumer/subscriber | 生产路径承诺 | 必须有接线 issue 或路径式 AC |
| 真实发送/同步/迁移/副作用/provider | 真实集成承诺 | `evidence_required` 至少为 `integration`，受限时必须写 `validation_limited` |
| mock/fake/dry-run/static 明确允许 | 受限证据承诺 | notes 写 `mock_allowed` / `limited_allowed`，review 不得升级声明 |
| non-goal/future/deferred | 范围边界 | 不生成实现 issue；notes 写 `out_of_scope:<section>;<reason>` |

每个普通 issue 的 `notes` 应压缩记录相关 claim，例如：

```text
claim_ledger:issues/<csv-basename>.claims.json; claims:CLAIM-001,CLAIM-004; evidence_level:integration; production_path:covered
```

`REVIEW-01` 的 `review_regression_requirements` 必须要求逐条读取 `<csv-basename>.claims.json`，检查三件事：claim 是否覆盖、生产路径是否接上、证据等级是否支撑交付声明。若 CSV notes 出现 `claims:CLAIM-*` 但没有 `claim_ledger:<path>`，该 CSV 不完整，必须先补 ledger 再执行。

### 闭环路径规则（HARD — 组件 issue 不能代替接线 issue）

组件 issue 实现的是独立模块的内部逻辑。但 spec 的愿景通常还要求这些模块**被连接到生产路径**。以下情形必须生成独立的"接线 issue"，不能把接线行为当作某个组件 issue 的隐含产出：

| 信号（在 spec 中看到） | 必须生成的独立 issue |
|----------------------|---------------------|
| "A 作为 B 的 consumer/handler/subscriber 运行" | 注册 A 到 B 的 dispatcher/registry |
| "应用启动时拉起 X worker/scheduler" | 在 main.py / lifespan 中启动 X |
| "agent 可调用 tool Y" | 把 Y 注册到 agent integration_tools |
| "组件 C 的输出注入到 flow D" | 在 D 的执行路径中调用 C |
| "真实 provider/adapter 替换 static placeholder" | 实现并注册真实 adapter（即使 mock 先行） |
| "从 A 到 Z 的完整路径可跑通" | 端到端路径验证（fake provider 可接受，但链路必须通） |

规则：
- 接线 issue 的 `priority` 不低于它所连接的组件 issue 中最高的那个
- 接线 issue 的 `acceptance_criteria` 必须是路径式的："WHEN production startup/flow runs THEN component X is reachable by its documented consumers"，而不是组件式的 "WHEN X input THEN Y output"
- 如果 spec 明确说"v1 不接线 / 骨架即可"，可以不生成接线 issue，但必须在对应组件 issue 的 `notes` 中写明 `scope:skeleton_only;wiring_deferred_to:<reason>`
- **REVIEW-01 的 regression requirements 必须包含至少一条路径级检查**："WHEN app starts / agent runs / flow executes THEN documented consumers can reach this component through the production path"

## Field inference rules

### `priority`

- 涉及破坏性变更、迁移、权限、删除：`P0`
- 公共基础能力或多个任务依赖项：`P1`
- 其他默认：`P2`

### `test_mcp`

- 后端逻辑 / API：`AUTOSERVER`
- 前端组件 / 页面：`AUTOFRONTEND`
- 多步流程 / 跨页面交互：`AUTOE2E`
- 契约 / schema / adapter：`CONTRACT`
- 迁移 / 数据修复：`MIGRATION`
- 难以自动化的体验验证：`MANUAL`

### `required_skills`

- 纯 backend / infra：留空
- 用户可见 UI：`ui-ux-pro-max`
- landing / hero / 强视觉页面：`ui-ux-pro-max;frontend-skill`

### `required_mcp`

- backend / infra：留空
- 用户可见 UI：`chrome-devtools`
- 多步交互：`chrome-devtools;playwright`
- 强视觉 / 动效 / 氛围：`chrome-devtools;screenpipe`
- 两者兼有：`chrome-devtools;playwright;screenpipe`

## Vision Review Rows

`REVIEW-N` 行用于审计交付结果是否达成批准文档愿景。

下列规则是 REVIEW 行的取值约束，不是完整 CSV schema。实际 CSV 仍必须包含 `csv-schema.md` 的全部 19 列；未列状态字段按标准默认值初始化。

- `area` 固定为 `review`
- `priority` 固定为 `P0`
- `test_mcp` 固定为 `MANUAL`
- `refs` 至少包含批准文档路径
- `notes` 必须包含 `review_kind:vision`
- 生成阶段的 `notes` 必须包含 `claim_ledger:<path>`、`claim_coverage:<covered>/<total>`、`claim_coverage_status:pending`、`review_agent_mode:pending`、`review_independence:pending`
- 执行阶段由 `mission-csv-execute` 回填 `review_actual_model:<model>`、`review_result:<result>`、`handoff:<path>` 等结果标签
- `review_agent:same-model-sub-agent` 只是兼容旧 CSV 的意图标签，不再作为新 CSV 的必填 schema 字段；实际执行方式以 `review_agent_mode` 为准
- `REVIEW-01` 由 CSV 生成阶段创建
- `REVIEW-02` 及之后由执行阶段在发现缺口时追加

## Acceptance Criteria 构建顺序

1. 文档中的 testing / validation / success criteria
2. task / step 附带的运行命令和预期结果
3. 设计文档中的 constraints / risks
4. 关键文件 `ref: path:line`
