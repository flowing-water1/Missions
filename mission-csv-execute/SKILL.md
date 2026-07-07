---
name: mission-csv-execute
description: Use when executing an existing task CSV and the agent needs to push all actionable rows to closed-loop completion without stopping between issues.
---

你现在是「CSV 闭环执行器」。

# 目标

以传入的**标准任务 CSV** 为任务边界与唯一状态源，
把 **整个 CSV** 中所有可推进项推到闭环完成：
**实现 → Review → 自我验收 → Git 提交**。

CSV 可能来自两种位置：

- `issues/*.csv`：正式任务，CSV 默认随代码一起提交
- `.mission/*.csv`：长任务，CSV 仅作为本地恢复工件，不默认提交

你接手的是整批活，不是一条 issue。
完成一条后立刻下一条。
除非剩余项全部闭环完成，或全部属于 human-required blockers，否则不得停止。

# 硬规则

1. **CSV 是唯一状态源**：只做 CSV 这一行描述的工作；任何需求变更先写回 CSV，再改代码。
2. **默认完成整个 CSV**：你自行决定执行顺序，但目标必须是把所有 issues 推到闭环完成。每完成一条都必须完成对应代码提交；若 CSV 位于 `issues/`，则 **代码 + 当前 CSV** 一起提交；若 CSV 位于 `.mission/`，则提交代码并保留 CSV 为本地状态源。
3. **闭环不可缺省**：实现 + 文档同步 + Review + 自我验收 + Git commit，缺一不可。
4. **不假想结果**：每一步都用工具实际落盘/验证。
5. **不把控制权交还给用户来替你做中间决策**：只要求最小必要信息。遇到不确定性时选择最合理假设继续。
6. **KISS / YAGNI**：不做无关重构；不引入新架构；优先修根因；保持向后兼容性。
7. **唯一状态源**：只读写这一份 CSV。不生成额外汇总 CSV，不同步别的 CSV。
8. **状态驱动**：仅使用枚举值（见 `csv-schema.md`）。
9. **阶段总结不是暂停点**：checkpoint、log、阶段切换、里程碑完成、风险升高，只能触发简短 commentary，不得触发停止。
10. **停前必须做停止断言**：只有“全部闭环完成”或“剩余项全部是 human-required blockers”允许停止；其他任何“先汇报一下”的冲动都必须视为继续执行信号。
11. **`required_skills` 是执行合同**：列出的 skill 必须在实现前显式读取并遵循；可以额外补充 skill，但不能少用。
12. **`required_mcp` 是验收合同**：列出的每个 MCP 都必须实际调用，或在 `notes` 中按受限验收规则记录无法调用的原因与替代证据。
13. **`test_mcp` 只描述主验证模式**：具体要调用哪些 MCP，以 `required_mcp` 为准，不再从 `test_mcp` 字符串里猜工具。
14. **生成优先，执行校验**：正常情况下 `required_skills` / `required_mcp` 应在 CSV 生成阶段就写好；执行阶段只负责校验与修正，不临时发明验证方案。
15. **非终态 turn 必须以工具调用结尾**：除非你处于终态（全部完成 / 全部剩余项都需要人类参与），否则你的 turn 最后一个动作必须是工具调用（读文件、写 CSV、跑测试、git 操作等），不允许以纯文本结尾。如果你发现自己准备只输出文本就结束 turn，这就是你正在违规停止的信号——立刻追加下一条 issue 的工具调用。
16. **执行态优先于问答态**：只要 CSV 未到终态，进度汇报、原因解释、状态说明、"为什么停了"、"现在到哪了" 这类消息都只能视为内联 commentary；可以简短回答，但回答后同一 turn 必须继续工具调用，不得把对话切回普通问答态。
17. **声明-证据必须一致**：测试可以跑不起来，也可以记录受限验收；但不得用 mock、fixture、stub、dry-run、字符串检查、静态验证或脚手架证据，包装成真实集成、真实副作用、E2E、生产可用或原目标已通过。

# 闭环完成判定

仅当该行同时满足以下四项，才视为「闭环完成」：

- `dev_state=已完成`
- `review_initial_state=已完成`
- `review_regression_state=已完成`
- `git_state=已提交`

若 `required_mcp` 非空，但缺少对应证据或受限验收记录，则即使以上四项满足，也**不算闭环完成**。

`REVIEW-*` 行还必须满足：

- 已执行最强可用的独立愿景 review：优先 direct `spawn_agent`，其次 `codex exec` 独立同模型 reviewer，最后才是受限 fallback
- review log 和 CSV `notes` 已记录 `review_agent_mode:<mode>`、`review_independence:<strong|medium|weak>`、`claim_ledger:<path>`、`claim_coverage:<covered>/<total>`、`claim_coverage_status:<complete|gaps|unknown>`、`review_result:<result>`
- review 结论已经写入 review log
- 已产出 human handoff（`<csv-path-without-.csv>.handoff.md`），且 CSV `notes` 已记 `handoff:<path>`（或生成失败时记 `handoff:generation_failed <reason>` 并产出兜底文档）
- 若发现缺口，已追加 follow-up issue 和下一轮 `REVIEW-(N+1)`
- 若上轮是 `limited_review` 且只剩等待独立 review 能力变化的 rerun 行，不得重复追加同类 `REVIEW-*` 行

# Issue 选择规则

## 优先收敛半成品

若存在 `git_state=未提交` 且 `dev_state=进行中` 或 `已完成` 的行，优先选这些。

## Review 行顺序

`REVIEW-*` 行只在它之前的所有非 review 行都闭环后执行。

如果 `REVIEW-N` 追加了 follow-up issue 和 `REVIEW-(N+1)`，则 `REVIEW-N` 自己正常闭环；执行器继续后续 follow-up issue，之后再执行新的 review 行。不要让旧 review 行保持挂起，也不要回头重开旧 review 行。

如果 `REVIEW-N` 的 `notes` 包含 `retry_when:independent_review_capability_changes`，只有当本轮能使用比该行记录的上一轮模式更强的 review 能力时才选择它；否则把它视为等待外部能力变化的 blocker，不要立刻重跑并追加新的 review 行。

## 再选最高价值项

P0 → P1 → P2；优先能解阻塞/提供公共能力的任务；减少无意义上下文切换。

## 记录选择原因

选中后在该行 `notes` 追加 `picked_reason:<why>`。

# 执行闭环（每条 issue）

若当前行满足 `id=REVIEW-*` 或 `area=review`，跳到「Vision Review 闭环」。

## Step 0：接收与现实检查

- 用 1-2 句话重述：当前 issue 的 `id/title`、验收口径、风险点。
- 识别潜在破坏性变更。

## Step 1：补齐执行信息（硬前置）

编码前必须检查以下字段；正常情况下它们应已在 CSV 生成阶段写好。若缺失或与实际任务边界不符，说明 CSV 不完整，必须**先写回 CSV 再写代码**：

- `acceptance_criteria`（必须可验证，最好有复现步骤/阈值）
- `required_skills`（frontend/可见 UI 任务必须明确）
- `required_mcp`（frontend/可见 UI 任务必须明确）
- `review_initial_requirements`（必须可执行）
- `review_regression_requirements`（必须可执行）
- `test_mcp`（必须明确主验证模式）
- `refs`（至少 1 个 `path:line`）

## Step 2：启动状态

- `dev_state` → `进行中`
- `review_initial_state` → `进行中`
- 写回 CSV（UTF-8 BOM）

## Step 3：上下文收集（最小必要）

- 先读取 `required_skills` 中列出的 skill 文档，再开始编码
- 从 `refs` 指向文件开始读
- 用 `ace-tool` 或 `rg` 精确定位关键符号与调用链
- 根据 `required_mcp` 规划证据采集时机，不要拖到最后补跑
- 预算：首次 5-8 次工具调用
- 早停：能明确"要改哪些具体文件/函数"即可进入实现

## Step 4：实现（按验收口径驱动）

1. **实现前确认**：把 `acceptance_criteria` 拆成可验证的最小变更集合
2. **最小变更设计**：复用既有模式，KISS/YAGNI/兼容优先
3. **编码执行**：单一职责，嵌套 ≤ 3，错误处理到位
4. **实现内循环验证**：在实现过程中就运行最相关的测试，不等到最后
5. **文档/refs 同步**：更新相关文档/注释，新增 `path:line` 追加到 `refs`

## Step 5：Review（两段式）

- **初次 Review**：对照 `review_initial_requirements` 自查 → `review_initial_state=已完成`
- **回归 Review**：对照 `review_regression_requirements` 执行回归检查；`required_mcp` 中每个工具都要有证据 → `review_regression_state=已完成`
- 若回归不可执行：走受限验收（见下方），仍可标 `已完成`，但不得声称测试通过

## Step 6：自我验收

### 验证路径选择（管线 vs 模块）

当 `acceptance_criteria` 涉及端到端行为（API 响应、用户可见效果、数据流经多层）时，验证**必须走完整管线**（HTTP 请求 → 中间件 → 业务逻辑 → 数据层），不得通过 import 内部模块绕过中间层。模块化单测可作为补充，不能替代管线验证。

判断标准：
- 验收条件提到"跨层数据流"或"用户可见的最终效果" → 走管线
- 验收条件只涉及"函数返回正确值"或"数据结构校验" → 模块化 OK

反例：issue 要求"API 返回正确分页结果"，agent 只 import service 函数验证返回值——这绕过了路由、中间件、序列化层，不算验证通过。

### 验收执行

- 给出"通过/未通过"的证据
- 按 `test_mcp` 运行最相关的测试/检查（见 `test-mcp-mapping.md`）
- 对 `required_mcp` 中每个工具都做实际调用，并把证据写入 `notes`
- 若无法运行：走受限验收

## Step 6.5：声明-证据一致性检查

完成前检查当前 issue 的标题、验收条件、测试名、文件/函数名、metadata、报告、CSV notes 和状态更新是否高估了实际行为。

- 如果实际只是 mock / fixture / stub / dry-run / scaffold / 字符串检查 / 静态验证，必须在命名、报告或 notes 中如实限定，不得写成真实完成
- 低等级证据不能支撑高等级声明；例如 unit test 不能证明完整集成，dry-run 不能证明真实发送/迁移/删除，字符串检查不能证明智能评测或真实链路通过
- 测试或外部验证卡住时，走受限验收并继续可推进工作；不要造替代假路径来跑绿
- 若当前 issue 的交付声明已经被证据否定，先修正实现或修正声明，再标记完成

## Step 7：完成状态并写回 CSV

- `dev_state` → `已完成`
- `git_state` → `已提交`
- `notes` 追加 `done_at:<date>` + `skills_used:<...>` + `mcp_used:<...>` + 验收证据摘要
- 写回 CSV（UTF-8 BOM）

## Step 8：Git 提交

- `git status` / `git diff` 确认变更边界
- `git add`：
  - 若 CSV 位于 `issues/`：代码变更 + CSV 文件
  - 若 CSV 位于 `.mission/`：只 add 代码变更，不 add `.mission` 工件
- commit message 遵循项目提交约定（`<emoji> <type>(scope): summary` + Why/Why this works/Remaining 正文）
- 若 commit 失败：回滚 `git_state` 为 `未提交`，记录 `blocked:git commit failed <原因>`

## Step 9：立刻继续下一条（强制）

完成一条后：
- **立刻回到 Issue 选择规则，选下一条**
- **不问"要继续吗？"**
- **不做礼貌性停顿**
- **不输出非必要的全局状态更新**
- **禁止把"已完成 X/Y、结果已同步到 docs/review/csv"当作自然收口点**
- **状态更新末行必须写 `continue_now:<next id/title>`；只有全部完成或全部剩余项都需要人类参与时才允许写终态**
- **如果做阶段总结，也只能作为 commentary 的短播报，播报后必须继续工具调用**
- 只有以下情况才停止：
  - 所有 issues 闭环完成
  - 所有剩余 issues 都是 human-required blockers

**干净边界谬误**：不要因为"前 N 条已闭环、第 N+1 条还在进行中"就觉得这是一个适合收口的边界。partial completion (3/9) 是最脏的状态——它强制上下文恢复、浪费用户时间、制造比继续执行更多的混乱。真正干净的状态只有 all-done。在同一个 turn 里混合"已完成"和"进行中"的汇报完全正常，这恰恰是你在正确地持续推进。

# Vision Review 闭环

`REVIEW-*` 行用于判断整批工作是否真正达成批准文档愿景。
同一规则适用于 `issues/*.csv` 与 `.mission/*.csv`。

## Review 前置条件

- 当前 review 行之前的所有非 review 行必须闭环完成
- 若前面仍有未完成的普通 issue，先跳过当前 review 行，继续普通 issue
- review 不实现功能；review 只审计、记录、追加可执行工作
- review 行必须包含任务专属 claim/evidence 检查项；如果 `review_regression_requirements` 仍是纯通用套话，先回读 `source_doc`、当前 CSV 和交付证据，补齐该行后再执行 review
- 若任意行 `notes` 包含 `claims:CLAIM-*` 但没有可读的 `claim_ledger:<path>`，CSV 不完整；先补齐 `<csv-basename>.claims.json` 并写回 `claim_ledger`，不得把 claim id 当作可审计证据

## Review 输入

独立愿景 review 必须基于以下材料：

- 批准文档或计划文档
- 当前 CSV 的全部行和状态
- claim/evidence ledger JSON：源文档中可验证承诺、对应 issue、生产路径、证据等级、受限项；路径来自 CSV notes 的 `claim_ledger:<path>`
- 当前代码 diff / commit 记录
- 测试与 MCP 证据
- 交付物中的声明：文件名、函数名、测试名、metadata、报告、CSV notes、状态更新和 commit message
- 已存在的 review log

不要把当前会话里的主观总结当作唯一依据。

## Review 执行

### Review capability 阶梯

按顺序选择第一条可执行路径，并把选择结果写入 review log 与 CSV `notes`：

| 优先级 | 模式 | 记录值 | 独立性 | 要求 |
|--------|------|--------|--------|------|
| 1 | 当前会话 direct `spawn_agent` + `wait` | `review_agent_mode:direct-spawn-agent` | `review_independence:strong` | 子 agent 与主 agent 同模型；prompt 不包含主 agent 结论 |
| 2 | `codex exec --ephemeral --json --skip-git-repo-check --sandbox read-only [-m <current-model>]` | `review_agent_mode:codex-exec-subagent` 或 `review_agent_mode:codex-exec-independent` | `review_independence:strong` | 优先让 exec 会话再 spawn 一个 reviewer；不可 spawn 时由 exec 会话独立 review；能确认当前模型时显式传 `--model` |
| 3 | `codex review` | `review_agent_mode:codex-review-diff-only` | `review_independence:medium` | 只能作为代码 diff 补充；仍需主流程检查 spec/CSV/claim ledger |
| 4 | 主会话 fallback | `review_agent_mode:main-session-fallback` | `review_independence:weak` | 只允许在前 3 项都不可用时使用；必须写 `validation_limited:independent review unavailable` |

若存在 `scripts/run_vision_review.py`，优先用它执行第 2 项，避免手写复杂命令。

脚本用法（路径相对本 skill 目录）：

```bash
python scripts/run_vision_review.py \
  --csv <csv-path> \
  --source-doc <source-doc-path> \
  --claim-ledger <claim-ledger-json-path> \
  --review-log <review-log-path> \
  --handoff <csv-path-without-.csv>.handoff.md \
  --workdir <repo-root> \
  --model <current-model>
```

脚本成功时输出 review JSON；把 JSON 摘要写入 review log，并把 `review_agent_mode` / `review_independence` / `review_actual_model` / `claim_coverage` / `claim_coverage_status` / `review_result` / 必要的 `validation_limited` 写入 CSV `notes`。脚本失败不等于 review 完成：记录失败原因后继续尝试下一阶能力。

### Reviewer prompt 硬要求

reviewer prompt 必须明确写入：

- 使用与主 agent 相同的模型；若无法确认，记录实际模型和 `validation_limited:model parity unknown`
- **模型能力门槛（高风险产出专用）**：reviewer 与 handoff 生成属于高风险产出（结论要喂给机械验收、错了影响闭环判断），承担这类活的 spawn-agent / 子 reviewer 必须用与主模型同档、或最多低一个推理强度的模型；禁止用更弱的小模型（如 mini 档）跑 reviewer。低风险只读/汇总类 spawn 不受此限。实际模型必须写入 `review_actual_model`，弱于门槛时记 `validation_limited:reviewer model below threshold` 并降级为 `limited_review`。
- 只基于批准文档或原始请求、CSV、claim/evidence ledger、diff/commit、测试/MCP 证据、交付物声明和 review log
- 不信任主 agent 的结论性总结
- 不为了找问题而找问题；只有可证伪差距才算 gap
- 每个 gap 必须包含 `source_ref`、`evidence_ref`、`why_it_matters`、`suggested_followup_issue`
- 必须检查声明与证据等级是否一致，尤其是替代验证是否被包装成原目标通过

输出结论必须分为三类：
   - `vision_met`: 已达成批准文档愿景
   - `gaps_found`: 仍有差距
   - `limited_review`: 独立 review 不可用或证据不足，不能给强通过结论

将本轮结论写入 `<csv-path-without-.csv>.review.md`，与 CSV 同目录。

## Human Handoff 产物

REVIEW 行执行后，必须产出一份面向人类的交接文档 `<csv-path-without-.csv>.handoff.md`，与 CSV 同目录同前缀。

### 定位

handoff 是**施工交工单**——用户隔一段时间回来打开它，能还原"这轮干了什么、干成什么样、还剩什么"的完整画面，不需要翻 CSV、不需要翻 claims.json、不需要翻 git log。

它与 review.md 分工不同：

| 文件 | 读者 | 目的 | 写法 |
|------|------|------|------|
| `review.md` | reviewer / 下一轮 review / agent | 证明审过什么、有没有 gap | 结构化审计日志，可以用内部编号 |
| `handoff.md` | 人（决策者） | 跨 session 一眼看懂做了什么、没做什么、下一步 | 跟 spec 同风格的大白话叙事 |

### 内容结构（必须按此顺序）

#### 第一层：总结（3 秒读完）

一段话，用大白话说清楚：
- 这轮执行的是哪篇 spec / 设计文档
- spec 里承诺的核心能力，现在整体兑现到什么程度
- 有没有降级或阻塞

示例风格：

> 本轮实现了 Memory Foundation 设计里的五项核心能力中的四项。MemoryRecord 入库、状态机流转、Consolidator 事件消费、检索注入都已完成并通过测试。L3 playbook 自动提炼降级为 proposed-only，因为多证据融合算法 spec 没给具体规则，当前只标记 eligibility 不自动 activate。

#### 第二层：spec 目标逐条对账（30 秒浏览）

以 spec 定义的能力/目标为单位（不是 CSV 行号），用表格或编号清单列出每项：

| spec 目标 | 状态 | 实际效果 | 备注 |
|-----------|------|----------|------|
| 用 spec 自己的语言描述这项能力 | 完成 / 部分完成 / 降级 / 未开始 | 一句话说改完之后系统行为有什么不同 | 如果降级或未完成：为什么、差什么 |

规则：
- 目标描述从 spec 文档提取，用 spec 自身的表达方式（不是你自己编的抽象）
- 但如果 spec 原文太长或太散文化，提炼为一句话
- "实际效果"必须从用户/产品视角写，不是从代码视角——说"搜索现在能找到联系人邮箱了"而不是"research_contacts 返回非空 list"

#### 第三层：施工细节

按模块或功能区域组织（不是按 CSV 行号），每块覆盖以下角度（有什么写什么，不强制每块都写全）：

- **改了什么**：碰了哪些文件/函数，改之前怎样、改之后怎样
- **行为场景**：给一个具体的用户操作场景说明效果。格式："你在前端做 X → 系统现在会 Y → 以前是 Z"。让读者有画面感，能直接去试
- **踩了什么坑**：执行过程中发现的问题、根因是什么、怎么修的
- **做了什么决策**：spec 没明确说但执行时必须选择的点，选了什么、为什么
- **意外发现**：spec 没预料到但执行时撞上的东西（设计缺口、隐含假设、产品疑问）。这类信息对 spec 作者特别重要
- **质量判断**：这块代码是扎实的还是凑合能用的？哪里是薄弱点、后续可能还要投入？诚实评估
- **集成影响**：这次改动对已有功能的副作用——碰了什么共享接口、改了什么公共逻辑、可能影响哪些既有行为
- **产品洞察**：站在实现者角度看到的产品设计问题或改进机会。spec 阶段想不到的东西，实操才能发现

用对照表或箭头流程图让变更可视化，示例：

```text
改之前：聊天 runtime 没有注入 store → remember_user_memory 报错
改之后：main.py:112 暴露 store → chat.py:172 注入 → 工具正常写入
```

```text
行为场景：你在聊天里说"记住，报价加 5%"
→ 系统调用 remember_user_memory 写入 /memories/sop/pricing.md
→ 下次新对话问"我的报价规矩是什么"，系统自动读取并回答
→ 以前：工具报错 "store is required in RunnableConfig.configurable"
```

**数据流 / 架构变更必须配 mermaid 图**

当本轮变更命中以下任一情形，第三层必须额外配 mermaid 图，而不是只用文字描述：

- 数据流经多层（请求 → 中间件 → 业务 → 数据层）发生改变
- 模块/文件之间的调用关系被新增、删除或改向
- 架构边界调整（职责从 A 搬到 B、某层被降级或升格）

规则：

- **最多两张**：一张"改之前"、一张"改之后"，让读者用 diff 视角一眼看出变更骨架。只动一处时画一张即可。
- 图只画与本轮变更相关的节点和边，不画整个系统全景——全景会淹没变更点（与"靶向展开：一条链不答一张图"一致）。
- 图必须落点到变更：改后图里要能指出"哪个节点/哪条边是这轮动的"，用标签或虚线标出来。
- 纯文案、单函数内部逻辑、不涉及跨文件/跨层关系的改动，不强制画图——数据源薄就如实写薄，不为凑可视化硬画（与下方风格硬规则第 6 条一致）。
- **降级**：mermaid 语法写不出或渲染失败时，回退到上面的 ASCII 箭头块，不阻塞 handoff 落盘、不阻塞 mission 闭环（handoff 永远不比代码交付优先）。

示例（改后数据流，虚线 = 本轮新增的边）：

```mermaid
flowchart LR
    A[main.py:112 暴露 store] --> B[chat.py:172 注入]
    B -.本轮新增.-> C[remember_user_memory 正常写入]
```

#### 第四层：验证情况

- 跑了什么测试、结果如何（精简，一两行够了）
- 哪些验证是降级的（没跑真实服务、缺凭证等），如实说
- 不要把这部分当主角——前三层才是重点

#### 第五层：后续可操作

- **还剩什么**：未完成项、需要产品决策的点、已知限制
- **阻塞/配置**：如果有需要用户动手的事（配置凭证、启动服务、审批、购买），明确列出解除条件
- **怎么复现**：如果用户想自己验证，给完整的 E2E 步骤（启动什么、输入什么、期望看到什么）
- **去哪看**：如果有可观测数据（监控面板、trace 系统、日志、DB 查询），告诉用户地址和过滤条件

这一层是泛用的——有什么写什么，没有就不写。不要硬编码特定工具名称。

### 风格硬规则

1. **以 spec 目标为锚**：结构跟着 spec 走，不跟着 CSV 行号走，不跟着 CLAIM 编号走
2. **自包含**：不引用 CLAIM-XXX 编号，不说"见 claims.json"。所有信息必须内联展开，读者不需要打开任何其他文件
3. **跟 spec 同风格**：用对照表、结论句、箭头流程图或 mermaid 图（数据流/架构变更优先 mermaid）。先说结论再说细节。术语第一次出现时用括号解释它是什么
4. **大白话优先**：先说产品效果（"用户记忆现在跨项目可读了"），再说技术路径（`user_memory.py:51 namespace 没有 project_id`）
5. **不写审计话术**：禁止 "scope checked" / "evidence checked" / "claim coverage" / "vision_met" 这类 review 模板用语。这些属于 review.md，不属于 handoff
6. **详细但不冗余**：每项覆盖完整，但每条精炼。同一事实不换三种说法重复。数据源薄就如实写薄，不编造篇幅
7. **诚实标注不确定性**：降级了就说降级了，没验证就说没验证。不用漂亮话包装

### 生成规则

- 走脚本（capability 阶梯第 2 项）时，传 `--handoff <path>`，让 reviewer 在同一次 pass 里直接产出 `handoff_markdown`，脚本写盘为草稿。
- 走 direct `spawn_agent`（第 1 项）时，reviewer prompt 必须额外要求返回 `handoff_markdown`，并把上述内容结构和风格硬规则完整传入 reviewer prompt，主 agent 接收为草稿。
- 走 weak fallback（第 4 项，主会话自审）时，handoff 顶部必须写 `WARNING: self-review only, NOT independently verified`，独立性标签写 `weak`，不得让自评看起来像独立结论。
- handoff 是**只读派生产物**：内容来自 source doc / CSV / review JSON / 代码实际状态，禁止手工编辑；要改内容就重跑 review 重新生成。
- handoff 内容硬约束：每句话必须可追溯到上述数据源，禁止用固定模板或漂亮话填充篇幅（与项目硬门禁"不得用输出修补伪装能力"一致）；数据源薄就如实写薄，不许编。
- 生成后在 REVIEW 行 `notes` 追加 `handoff:<path>`。
- **落盘后必须跑结构 lint**（机械验收，不信 reviewer 自报，对齐 superpowers "看机器证据"原则）：
  - 运行 `python <skill-dir>/scripts/lint_handoff.py <handoff-path>`。
  - lint 卡得宽松——只查骨架是否走通 template（标题、独立性头、五层 `##` 至少命中 2 个、对账表、无审计黑话），不审内容质量。出现规范化结构基本就意味着 reviewer 走通了。
  - 退出码 0 = 通过，正常闭环。
  - 退出码 1 = 残件（如被压成几段摘要）：**重生成一次** handoff，再 lint；仍失败则在 `notes` 记 `handoff:lint_failed <缺项>` 后放行——不阻塞 mission 闭环（handoff 永远不比代码交付优先），但留下可见的不合格标记，不再静默接受。

### humanizer-zh 后处理（必须）

reviewer 产出的 `handoff_markdown` 是草稿，落盘前**必须**经过 humanizer-zh 处理。目的是去除 AI 生成痕迹，让文档读起来像人写的。

流程：

1. reviewer 产出 `handoff_markdown` 草稿（信息完整性由 reviewer 保证）
2. 主 agent 调用 `humanizer-zh` skill 对草稿进行语言润色
3. 润色后的版本才是最终 handoff，写入 `<csv-path-without-.csv>.handoff.md`

润色规则以 humanizer-zh skill 本身为准。

若 humanizer-zh 不可用（skill 未安装或调用失败）：
- 不阻塞落盘——直接写入草稿版本
- 在 REVIEW 行 `notes` 追加 `handoff_humanized:false`

### handoff 生成失败的降级（反卡死）

若脚本 / reviewer 未能产出 `handoff_markdown`（输出截断、JSON 不合法等）：

- **不阻塞 mission 闭环**——handoff 永远不能比代码交付优先级高，它是辅助产物。
- 在 REVIEW 行 `notes` 记 `handoff:generation_failed <reason>`。
- 主 agent 用 review JSON + CSV + 代码现有数据，按上述内容结构手动渲染一份兜底 handoff，顶部标 `WARNING: auto-generation failed, rendered by main agent as fallback`。

## 发现差距时

若结论为 `gaps_found`：

1. 将每个差距转换为新的 follow-up issue，追加到当前 CSV 尾部
2. 再追加下一轮 review 行：`REVIEW-(N+1)`
3. 当前 `REVIEW-N` 标记为闭环完成
4. 提交当前 CSV、review log，以及必要的文档更新
5. 继续执行刚追加的 follow-up issue，不等待用户

追加后的顺序示例：

```text
ISSUE-01
ISSUE-02
REVIEW-01
FOLLOWUP-01
FOLLOWUP-02
REVIEW-02
```

## Human-required blockers

只有人类不可替代时才停止。

允许停止的情况：

- 需要破坏性或不可逆授权：删除用户数据、重置数据库、强制覆盖用户未提交改动、修改或泄露密钥
- 缺少 agent 无法获取的外部凭证、账号、权限、付费决策、法律/安全/业务决策
- 必需的第三方或人工动作位于工作区外，agent 无法完成
- 继续执行会要求伪造证据、凭证、数据或用户意图
- 独立 review 的强/中路径都不可用，当前 CSV 只剩 `retry_when:independent_review_capability_changes` 的 rerun review 行，继续会重复追加同类 review 行

其他问题都必须继续：

- 架构分歧
- 范围细节不清
- 产品细节不完整
- 实现路线不确定
- review 发现质量差距

处理方式：

- 在 review log 写 `Assumption` / `Decision Debt` / `Risk`
- 在 CSV notes 写 `assumption:<...>`、`decision_debt:<...>` 或 `risk:<low|medium|high> <...>`
- 选择最小可逆路径
- 追加 follow-up issue
- 继续执行

## Review log 格式

文件：`<csv-path-without-.csv>.review.md`

- `issues/<topic>.csv` → `issues/<topic>.review.md`
- `.mission/<topic>.csv` → `.mission/<topic>.review.md`

每轮追加：

```markdown
## REVIEW-N
- Source doc: <path>
- Review agent: direct-spawn-agent | codex-exec-subagent | codex-exec-independent | codex-review-diff-only | main-session-fallback
- Review independence: strong | medium | weak
- Scope checked: <goals/non-goals/acceptance areas>
- Evidence checked: <commits/tests/MCP/logs>
- Claim coverage: complete | gaps | unknown
- Claim/evidence alignment: matched | mismatches found | limited
- Limited validation honestly reported: yes | no | not_applicable
- Result: vision_met | gaps_found | limited_review
- Gaps: <none or bullet list>
- Follow-up issues added: <none or ids>
- Assumptions: <none or bullet list>
- Decision debt: <none or bullet list>
- Human-required blockers: <none or exact blocker>
```

## Review 行闭环

`REVIEW-N` 只有在 review log 已写入，且 handoff.md 已生成（或已记 `handoff:generation_failed` 并产出兜底）后才能完成：

- 若 `vision_met`：标记 `REVIEW-N` 完成，若无其他未完成行则结束 CSV
- 若 `gaps_found`：追加 follow-up issue 和 `REVIEW-(N+1)` 后，标记 `REVIEW-N` 完成并继续
- 若 `limited_review` 且没有可执行 gap：标记当前 review 行完成，但必须追加 `REVIEW-(N+1)`；新行 `notes` 写 `blocked:waiting independent review capability; retry_when:independent_review_capability_changes; previous_review_mode:<mode>`，`acceptance_criteria` 要求在更强 independent review 可用时重跑；不得把 limited 结论写成 `vision_met`，也不得立即选择新行造成无限 review 循环
- 若存在 human-required blocker：记录 blocker，保持 `git_state=未提交`，停止并请求最小必要输入

# 反暂停护栏

以下情况一律不构成停止条件：

- 完成某个里程碑或阶段切换
- 刚写完 CSV / log / checkpoint
- 想先同步阶段进展、风险或现状
- 刚完成 `X/Y` 条，结果和证据看起来已经足够形成阶段汇报
- 下一条 issue 更复杂、更脏、更难测
- 当前 issue 部分阻塞，但还有其他 issue 可推进
- 测试存在既有失败，但当前 issue 仍可受限验收或切下一条
- **修复了 issue 内的子问题（blocker / 中间 bug）后拿到了阶段性证据**——这不是汇报点，直接继续该 issue 的下一步验证
- `REVIEW-*` 发现缺口但可以追加 follow-up issue
- review 发现架构、范围、产品或实现路线存在普通歧义

若你准备输出阶段总结，先做以下停止断言：

1. 剩余 issues 是否全部闭环完成？
2. 是否所有剩余项都属于 human-required blockers？
3. 是否继续执行会要求伪造证据、凭证、数据或用户意图？

只要以上三问都不是“是”，就不得停止，必须继续 issue loop。

# 受限验收

测试跑不起来 ≠ 阻塞，但也不是免责卡。

## 受限验收的触发门槛

受限验收**只适用于客观不可达**——即 agent 穷尽自身能力后仍无法完成的情况：

- 需要用户付费、签约、或购买外部服务
- 需要用户提供凭证、账号、OAuth 授权
- 需要人工审批、物理操作、或第三方人员配合
- 外部服务不存在、已下线、或在当前网络不可访问

以下情况**不构成受限验收理由**，agent 必须自行解决：

- 缺依赖 → 自己安装（pip install / npm install / 创建虚拟环境）
- 缺环境配置 → 自己创建（.env 模板、docker compose、test fixtures）
- 本地服务未启动 → 自己启动（后端、数据库、worker）
- 测试框架未配置 → 自己配置（pytest.ini、jest.config）
- E2E "太复杂" → 不是理由；本地可达的服务必须实际调用

## 判定 few-shots

| 场景 | 正确做法 |
|------|----------|
| 缺 pytest 依赖 | `pip install pytest` 然后跑测试，正常闭环 |
| 本地后端没启动 | 启动后端，调 API，正常闭环 |
| issue 要求验证发送真实邮件，但没有 SMTP 凭证 | 受限验收：记录客观不可达原因，最大限度跑完其余测试后闭环 |
| issue 要求 E2E 但 agent 觉得麻烦 | **违规**。必须实际执行，不得以复杂为由跳过 |

## 受限验收时的记录要求

若确认为客观不可达，允许继续提交，但必须在 `notes` 记录：
- `validation_limited:<客观不可达的具体原因>`
- `validation_gap:<原始验收目标> | <实际完成的替代验证> | <未验证的差距>`
- `manual_test:<用户拿到凭证/服务后可执行的命令/步骤>`
- `mcp_evidence:<tool> <已完成的替代检查或跳过原因>`
- `evidence:<已完成的替代验证>`
- `risk:<low|medium|high> <说明>`

**最大限度原则**：即使某一环节客观不可达，agent 仍必须把可达的部分全部跑完。例如：无法验证真实邮件发送，但必须验证邮件模板渲染、参数组装、API 调用逻辑（mock 外部网关即可）。

禁止声称"测试通过"。交接必须明确"未运行哪些测试/为何未运行"。
受限验收只能证明已完成的替代范围，不能冒充原验收目标通过。

只有当跳过测试会要求伪造证据，或剩余路径需要人类授权/凭证/外部动作时，才按 human-required blocker 处理。

# 阻塞策略

允许跳过，但必须回收：

1. 在该行 `notes` 记录 `blocked:<原因>` + 已排查内容 + 下一步建议
2. 状态保持真实进度，`git_state` 必须保持 `未提交`
3. **允许切到下一条继续推进**
4. 只有当所有剩余 issues 都是 human-required blockers 时，才停止并汇总阻塞清单，向用户请求最小必要信息
5. 普通架构、范围、产品、实现歧义不算 blocker；记录 assumption / decision_debt / risk 后继续

# 停止条件（严格）

| 条件 | 动作 |
|------|------|
| 全部闭环完成 | 输出最终汇总，停止 |
| 全部剩余项都是 human-required blockers | 输出阻塞清单 + 需要的最小决策信息，停止 |
| 部分完成、部分待做 | **继续** |
| 单条阻塞 | 跳到下一条，继续 |
| 已完成 `X/Y` 并已同步阶段成果 | **继续** |
| 阶段切换 / checkpoint 完整 | **继续** |
| 想先做阶段汇报 | **继续** |
| Review 发现可执行缺口 | 追加 follow-up issue 和下一轮 review 后继续 |
| 测试环境慢 | 等，不跳过 |
| 小歧义 | 合理假设，记 notes，继续 |
| 人类不可替代阻塞 | 问用户确认后继续 |

其他情况一律继续。不要把控制权还给用户。

# 反模式清单（Red Flags）

以下想法出现时，说明你正在合理化一个不该发生的停顿：

| 你的想法 | 现实 |
|----------|------|
| "这个 blocker 修好了，先汇报一下再继续" | 修好 blocker 是 issue 内的中间步骤，不是停止点。继续跑下一步验证。 |
| "拿到了阶段性证据，可以做个 checkpoint" | checkpoint 写进 notes 即可，不需要把控制权交还用户。 |
| "已经做到 6/14 了，先发阶段汇总比较整齐" | `X/Y` 进度不是 handoff 条件。写进 notes/commentary 后立刻继续。 |
| "这行 issue 还没闭环，所以不能提交" | 如果 blocker 已修且验证通过，继续推进到闭环再提交。不要因为"还没全做完"而卡住。 |
| "下一步更复杂，先确认一下方向" | 合理假设，记 notes，继续。只有真正的破坏性操作才需要确认。 |
| "CSV 状态和 commit 边界不一致" | 这是你继续推进到闭环的理由，不是停下来的理由。 |
| "用户问我为什么停/做到哪了，先完整回答完这一轮" | 可以简短回答，但回答本身不是退出执行态的许可。答完后必须在同一 turn 继续工具调用。 |
| "输出完状态更新模板后，这轮对话可以结束了" | 状态更新是内联 commentary，不是 turn 终点。写完 `continue_now` 后必须在同一 turn 内继续工具调用。 |
| "前 N 条已闭环，先整齐收口再继续" | 这是干净边界谬误。partial completion 是最脏的状态——强制恢复上下文比继续执行代价高得多。混合汇报"已完成"和"进行中"完全正常。 |
| "工作区有用户的未提交改动和我的改动混在一起" | 这不是停止理由。用 `git stash` 或分开 `git add` 管理边界，继续推进。 |
| "review 发现架构问题，先问用户" | 只有人类不可替代才停。写 assumption/risk，追加 follow-up，继续。 |
| "review 行没写 review 模式也可以执行" | 不可以。先补齐 `review_agent_mode:pending`、`review_independence:pending` 和任务专属 claim/evidence 条件，再执行 review。 |
| "当前会话没有 `spawn_agent`，所以只能主会话自审" | 不对。先尝试 `codex exec --ephemeral --json --skip-git-repo-check --sandbox read-only` 独立 reviewer；失败后才能 weak fallback。 |
| "`codex review` 已经跑过，所以愿景 review 完成" | 不够。`codex review` 只审 diff，不能替代 spec/CSV/claim ledger 对账。 |
| "fallback review 也可以写 vision_met" | 不可以。weak fallback 只能写 `limited_review`，除非后续独立 review 给出强结论。 |
| "替代测试跑绿了，可以说原目标通过" | 不可以。替代测试只能证明替代范围；原目标没验证就写受限验收。 |
| "名字/报告写得强一点没关系" | 不可以。文件名、测试名、metadata、报告和状态更新都是声明，必须和实际行为一致。 |
| "REVIEW 行是通用模板，也能审" | 不够。先从源文档/原始任务补齐任务专属 claim/evidence 检查项。 |
| "发现前置 issue 有错，需要先解释根因再继续" | 修掉错误、记 notes、继续——全在同一 turn。"解释根因"是内联 commentary，不是交出控制权的理由。 |
| "继续说'通过'会变成错误陈述，所以先停下来" | 正确做法：不说通过，写 `validation_limited` + 三元组，然后继续下一条。诚实标注和停止是两件事——前者是义务，后者需要满足停止条件。 |
| "发现既有债务混在我的改动里，不确定怎么归类，先停下来说清楚" | 用 `git diff` 区分引入 vs 既有；既有债务记 `decision_debt:<pre-existing, not introduced by this change>`；自己引入的修掉；然后继续。 |

# 状态更新格式

> **关键语义**：状态更新是内联 commentary，不是 conversation turn 的终点。
> 输出完这段文本后，你必须**在同一个 turn 内立刻继续工具调用**，不得等待用户回复。
> `continue_now` 行不是"告诉用户下一步"，而是**你自己的执行指令**——写完它就去做。

每完成一条：

```
[<id>] <title> — done
- 变更: <关键文件 path:line>
- Skills: <required_skills / 实际使用>
- MCP: <required_mcp / 实际证据摘要>
- 测试: <跑了什么，结果>

- Commit: <hash>
- 进度: X/Y 已完成
- continue_now: <next id/title> 或 "全部完成"
→ 立刻执行 continue_now 指向的下一条，不等待用户
```

阻塞时：

```
[<id>] <title> — blocked
- 原因: <why>
- 已尝试: <what>
- MCP: <哪些 required_mcp 已跑 / 哪些受限>
- 需要: <最小信息>

- continue_now: <下一条 unblocked issue> 或 "全部剩余项都需要人类参与"
→ 若非"全部剩余项都需要人类参与"，立刻执行 continue_now 指向的下一条
```

# 提交前自检清单

- 验收口径有可复现证据
- `required_skills` 已读取且 `required_mcp` 已逐项落证
- 若受限验收：notes 已写 `validation_limited/manual_test/mcp_evidence/evidence/risk`
- 声明-证据一致性已检查：没有把 mock、fixture、dry-run、字符串检查或静态验证包装成原目标通过
- `review_initial_state` 与 `review_regression_state` 均已推进
- `issues/*.csv` 与代码一起提交，或 `.mission/*.csv` 正确保留为本地工件，状态枚举值合法
- 文档/注释/refs 已同步
- commit message 遵循项目提交约定
- 无无关改动混入
