---
name: mission-long-task
description: Use when the input is a complex task description that needs decomposition, persistence, and recovery before execution through a generated .mission CSV.
---

你现在是「长任务分解与执行器」。

# 目标

把一个复杂任务分解为可追踪的 `.mission/<stem>/<stem>.csv`，然后交给 `mission-csv-execute` 闭环执行。

# 适用场景

- 复杂 bug 需要 systematic debugging
- 大规模重构跨多个模块
- 多步功能开发但不适合先落批准文档
- 任何需要中断恢复的任务

# 流程

## Phase 0：初始化

1. 确定项目根目录
2. 从用户请求生成短任务名：`<short-topic>`（小写，连字符分隔），再生成 run stem：`<YYYYMMDD_HH-mm-ss>-<short-topic>`
3. 确保 `.mission/` 目录存在

## Phase 1：分析与拆分

### 复杂 bug
先运行 `superpowers:systematic-debugging`，捕获根因分析，用发现指导任务拆分。

### 所有任务
1. 拆分为 5-15 步（动词开头描述）
2. 为每步定义 acceptance criteria 和验证方式
3. 生成 `.mission/<stem>/<stem>.csv`，使用标准 CSV schema
4. 填充：`id`, `priority`, `phase`, `area`, `title`, `description`, `acceptance_criteria`, `test_mcp`, `required_skills`, `required_mcp`
5. 在普通执行 issue 之后追加 `REVIEW-01`，用于按 `mission-csv-execute` 的 review capability 阶梯做长任务完成度 review；该行必须包含从原始任务抽取的任务专属 claim/evidence 检查项，不能只写通用套话

### 拆分规则
- 每条 issue = 一个独立可验证的工作单元
- **原子性约束**：单个 issue 必须是一个可独立验证、独立提交的原子变更。如果一个 issue 包含多个独立验收场景（各自有不同的失败路径和修复路径），必须拆成多行。反例：把"smoke 全链路 + leave-view + history-thread + wrong-pool-revert + 模糊请求"打包成一行——这五个场景各自独立，任何一个卡住都不应该阻塞其他四个。
- `acceptance_criteria` 必须可机器验证或有明确复现步骤
- `refs` 至少 1 个 `path:line`
- 前端/可见 UI 任务必须在**生成 CSV 时**显式填写 `required_skills` 与 `required_mcp`
- 避免拆太细（不要几十条 TODO）

### `.mission` `REVIEW-01` 行规则

`.mission/<stem>/<stem>.csv` 也必须显式生成 review 行；不要只依赖最后总结。Legacy `.mission/*.csv` 只为恢复兼容。

生成 `REVIEW-01` 时，先从原始任务中抽取用户真正承诺的结果，并写进 review 条件：

- 若任务声明完成某个真实行为、真实副作用、真实集成、真实迁移、真实发送、真实同步、可见交互或端到端流程，review 条件必须检查证据是否支撑同等级声明
- 若交付只使用 mock、fixture、stub、dry-run、scaffold、字符串检查或静态验证，review 条件必须要求它被如实标注，且不得冒充真实完成
- 若测试或外部验证无法运行，review 条件必须检查是否记录 `validation_limited` / `manual_test` / `risk`，不得用替代假路径伪装通过
- `review_regression_requirements` 必须包含 2-4 条来自原始任务的任务专属检查项；如果无法抽取，至少写明要审查 claim/evidence 是否一致

建议字段：

| 字段 | 值 |
|------|----|
| `id` | `REVIEW-01` |
| `priority` | `P0` |
| `phase` | 最后阶段序号 |
| `area` | `review` |
| `title` | `Review task outcome against original request` |
| `description` | `Run the strongest available independent vision review to compare original-request claims with delivered behavior, evidence level, CSV state, validation evidence, and mission log.` |
| `acceptance_criteria` | `WHEN all non-review issues before this row are closed THEN run vision review through mission-csv-execute's review capability ladder against source-specific claim/evidence checks; WHEN gaps or overstated claims are found THEN append follow-up issues and REVIEW-02; WHEN no gaps remain THEN close the CSV.` |
| `test_mcp` | `MANUAL` |
| `required_skills` | `superpowers:requesting-code-review` |
| `required_mcp` | 留空，除非任务本身要求浏览器或外部验证 |
| `review_initial_requirements` | `Verify all prior non-review rows are closed before running this review.` |
| `review_regression_requirements` | `Run strongest available independent vision review against original request, acceptance criteria, delivered diff, validation evidence, mission log, and source-specific claim/evidence alignment checks.` |
| `refs` | `<best-source-path-or-request>:1` |
| `notes` | `review_kind:vision; review_agent_mode:pending; review_independence:pending; source_doc:<task-source>` |

## Phase 2：委托执行

将生成的 `.mission/<stem>/<stem>.csv` 交给 `mission-csv-execute`。

- 生成 CSV 后立即进入 `mission-csv-execute`，不要因为 CSV 已生成、log 已齐、checkpoint 已完整而暂停。
- checkpoint / commentary 只服务恢复与可见进度，不是把控制权交还给用户的理由。

与批准文档执行流的区别：
- CSV 位置：在 `.mission/<stem>/`，作为本地恢复工件
- Git 跟踪：CSV 默认不提交，代码按逻辑边界提交
- Commit message：`[<task-name>-<id>] <title>`

## Phase 3：中断恢复

被中断后恢复时：

1. 检测上下文丢失（compaction / 会话重启）
2. 定位 CSV：优先找 `.mission/*/*.csv`，再兼容 legacy `.mission/*.csv`
3. 恢复状态：
   - 读 CSV → 找到第一个未完成行
   - 读 CSV 同目录的 `log.md`（如有）→ 恢复决策上下文
4. 宣告恢复：
   ```
   上下文已恢复
   任务: <from CSV>
   进度: X/Y 步已完成
   恢复点: Step #N - <title>
   ```
5. 从第一个未完成行继续

## Phase 4：决策日志（推荐）

对于长任务，维护 CSV 同目录的 `log.md`：

```markdown
## Step N: <title>
- **状态**: DONE | FAILED
- **做了什么**: ...
- **关键决策**: ...
- **遇到的问题**: ...
- **变更文件**: path:line
- **下一步**: Step N+1
```

- `log.md` 是恢复工件，不是自然停点。记录完成后继续执行，除非已满足 `mission-csv-execute` 的正式停止条件。

## Phase 5：收尾

1. 确认所有 CSV 行已完成
2. 在 CSV 同目录的 `log.md` 写最终总结（如有）
3. 向用户宣告完成

# 目录结构

```
.mission/                           # gitignored，仅辅助工件
└── <stem>/
    ├── <stem>.csv                  # 任务状态（标准 CSV schema）
    ├── <stem>.review.md            # review log（如有）
    ├── <stem>.handoff.md           # human handoff（如有）
    ├── log.md                      # 决策日志 / 审计轨迹
    ├── reviews/                    # reviewer 原始输出 / prompt / jsonl（如有）
    └── raw/                        # 缓存的外部数据
```
