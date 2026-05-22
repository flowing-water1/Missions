# Approved Doc -> CSV 字段映射

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

- `area` 固定为 `review`
- `priority` 固定为 `P0`
- `test_mcp` 固定为 `MANUAL`
- `refs` 至少包含批准文档路径
- `notes` 必须包含 `review_kind:vision`
- `REVIEW-01` 由 CSV 生成阶段创建
- `REVIEW-02` 及之后由执行阶段在发现缺口时追加

## Acceptance Criteria 构建顺序

1. 文档中的 testing / validation / success criteria
2. task / step 附带的运行命令和预期结果
3. 设计文档中的 constraints / risks
4. 关键文件 `ref: path:line`
