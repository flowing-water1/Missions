# missions

> 一套给 agent 用的 skills 包，专治长任务：路由分流、CSV 四状态闭环、中断恢复，全自动跑到底。Codex 和 Claude Code 都能用。

把一个需求扔给 agent，它会自己拆成 CSV、按四状态闭环跑、用独立 review 对照源文档验收，发现差距就追加 follow-up，最后写出给人看的交接文档再交还给你。配合 codex 的 `/goal` 用，断联不停、可 resume。

**新版说明：**

- mission 产物现在改成目录化结构：approved doc 会生成到 `issues/<stem>/<stem>.csv`，long task 会生成到 `.mission/<stem>/<stem>.csv`。
- CSV 同目录会放 claim ledger、review log、handoff 文档和 reviewer 原始输出；`claim_ledger:<path>`、`handoff:<path>` 这类相对路径也优先按 CSV 所在目录解析。旧版 `issues/*.csv` / `.mission/*.csv` 仍然兼容恢复和显式输入。
- REVIEW 阶段不再只写“同模型 sub-agent”这一条路，而是按能力阶梯优先使用最强可用的独立 vision review，并记录 `review_agent_mode` 和 `review_independence`。
- handoff 现在有 contract check：必须生成同名前缀的 `.handoff.md`，CSV REVIEW notes 必须记录 `handoff:<path>`，通过后写入 `handoff_contract:passed`；否则不能把本轮 review 说成 `vision_met`。
- Codex 现在可以稳定从 spec 生成 CSV，并用 claim coverage 指标检查需求覆盖率；执行结束后直接看 handoff 就能知道做了什么、哪些完成了、哪里有限制。

## Features

- **统一入口，自动路由** — 不管你给的是 CSV、md 文档、自然语言任务，还是一句 "continue"，`mission` 会判断走哪条路径
- **CSV 四状态闭环** — 每条 issue 必须同时满足 `dev_state` / `review_initial_state` / `review_regression_state` / `git_state` 才算完，跳一步都不行
- **目录化 Artifact Root** — 每个任务有自己的 artifact 目录，CSV、claims、review log、handoff 和 reviewer 原始输出放在一起，恢复和审计都更稳
- **REVIEW 行 + 独立愿景验收** — CSV 末尾必有 `REVIEW-01`，优先用独立 reviewer 对齐源文档、CSV、claim ledger 和实际交付，发现差距追加 follow-up 和 `REVIEW-N+1`
- **Claim/Evidence Ledger** — approved doc 会先抽取可验证承诺，落盘为 `*.claims.json`，CSV 只引用 claim id，避免 review 时只靠印象对账
- **Human Handoff** — REVIEW 后生成 `<csv>.handoff.md`，用人能看懂的话说明做了什么、哪些目标兑现了、哪里降级了、怎么复现
- **Handoff Contract Check** — handoff 落盘后会机械检查文件名、CSV REVIEW notes 和 Markdown 骨架；`vision_met` 必须同时有 `handoff_contract:passed`
- **test_mcp + required_mcp 分离** — "怎么验证" 和 "用什么工具验证" 是两个维度；前者写策略，后者写执行合约，杜绝"跑个 smoke 就说通过了"
- **声明-证据一致性硬门禁** — 不允许用 mock / fixture / dry-run / 字符串检查包装成"真实集成 / 真实副作用 / E2E 通过"
- **受限验收机制** — 测试跑不起来不是免责卡，但客观不可达可以走受限验收，必须如实记录 `validation_limited` / `validation_gap` / `manual_test` / `mcp_evidence` / `risk`
- **反暂停护栏** — 完成一条立刻下一条；checkpoint、阶段总结、进度汇报都不构成停止理由
- **中断恢复** — 会话挂了、key 没了、重启了？回来一句 `continue`，自动扫描 `issues/` 和 `.mission/`，从断点接着跑

## Skills Overview

| Skill                  | 作用                                                 | 输入                                |
| ---------------------- | ---------------------------------------------------- | ----------------------------------- |
| `mission`              | 总入口，判断输入类型，分派给子 skill                 | CSV / md / 任务描述 / 空（=resume） |
| `mission-doc-route`    | 拿到 md 文档，判断走 approved-doc 还是 long-task     | `*.md`                              |
| `mission-approved-doc` | 已批准的设计/计划文档 → `issues/<stem>/<stem>.csv` → 闭环执行 | 已批准的 md                         |
| `mission-long-task`    | 复杂任务描述 → `.mission/<stem>/<stem>.csv` → 闭环执行（可恢复） | 自然语言任务                        |
| `mission-csv-execute`  | CSV 闭环执行引擎（强内核），四状态推到底             | `*.csv`                             |
| `mission-recovery`     | 扫描未完成 CSV，定位断点，转发给执行器               | 无                                  |

所有路径最终都汇聚到 `mission-csv-execute`，这是真正的执行引擎；其他 skill 都是它的"前菜"。

## Installation

把整个仓库里的 `mission*` skill 目录拷进你的 skills 路径。仓库根目录的 README、长文说明、AGENTS/CLAUDE 示例不用拷进 skills 目录。

**Codex CLI**：`~/.codex/skills/`
**Claude Code**：`~/.claude/skills/`（或项目级 `.claude/skills/`）

```bash
# macOS / Linux — Codex
git clone https://github.com/flowing-water1/Missions.git
cp -r Missions/mission* ~/.codex/skills/

# macOS / Linux — Claude Code
cp -r Missions/mission* ~/.claude/skills/
```

```powershell
# Windows — Codex
git clone https://github.com/flowing-water1/Missions.git
Copy-Item .\Missions\mission* "$env:USERPROFILE\.codex\skills\" -Recurse -Force

# Windows — Claude Code
Copy-Item .\Missions\mission* "$env:USERPROFILE\.claude\skills\" -Recurse -Force
```

完成后对应 skills 目录里应该长这样：

```
mission/
mission-doc-route/
mission-approved-doc/
mission-csv-execute/
  csv-schema.md
  test-mcp-mapping.md
  scripts/
    check_handoff_contract.py
    lint_handoff.py
    run_vision_review.py
    test_check_handoff_contract.py
    test_run_vision_review_paths.py
    test_validate_claim_ledger.py
    validate_claim_ledger.py
mission-long-task/
mission-recovery/
```

重启你的 agent，它会自动识别。

## Quick Start

mission 自己就是入口。给它你的输入，它会自动判断走哪条路径。下面四种姿势任选：

```text
# 1. 已经有 CSV
mission @issues/2026-05-22_10-00-00-add-login/2026-05-22_10-00-00-add-login.csv

# 2. 已经有批准的设计文档
mission @docs/superpowers/specs/2026-05-22-add-login-design.md

# 3. 只有一句话需求
mission 给登录页加上手机号验证码登录，要包含 60s 倒计时和重发逻辑

# 4. 上次断了想接着跑
mission continue
```

skill 触发方式因 agent 而异：

- **Codex CLI**：直接 `$mission xxx` 或在 prompt 里说"用 mission skill 处理 xxx"，命令前缀按你本地 codex 的 skill 触发约定来（很多人用 `$` 前缀）
- **Claude Code**：skill description 自动匹配触发，你可以直接说"使用 mission skill 执行 @xxx.csv"，或者 `@` 文件后直接描述需求

进入 `mission-csv-execute` 后会自动按四状态闭环跑到底，跑完独立愿景 review，发现差距追加 follow-up，并生成 handoff 交接文档。**反暂停护栏内置在 skill 里**，不依赖外部命令——`mission-csv-execute` 的 SKILL.md 明确写了"非终态 turn 必须以工具调用结尾"、"执行态优先于问答态"等十多条硬规则。

### Best Practice：Codex + `/goal` 跑长任务

实测下来跑长任务最稳的姿势是 Codex CLI 配合 `/goal`，强烈推荐：

```text
# 1. 启动 codex 后先发一句 hello（重要：第一条不能是 /goal，否则记录会丢，resume 找不回）
hello

# 2. 然后 /goal 包住 mission 输入
/goal @issues/2026-05-22_10-00-00-add-login/2026-05-22_10-00-00-add-login.csv
```

`/goal` 给 mission 加了三层 buff：

- **抗断联**：供应商挂了不会中断，恢复后接着跑（三方中转用户的刚需）
- **强反暂停**：比 SKILL.md 里的护栏更硬，不会中途偷停
- **可 resume**：终端关了、电脑重启了，`codex resume` 选回会话就接着跑——前提是开头发过 hello 占位

要跑几小时甚至跨天的长任务，闭眼用这个姿势就行。短任务或单条 CSV 直接 `mission @xxx` 也够。

> Claude Code 里没有 `/goal`，但 mission-csv-execute 自带的反暂停护栏 + 一句 `continue nonstop until done` 一般也能跑完，只是抗断联弱一些。

## Architecture

### 1. 路由层（mission）

```
你的输入
  │
  ├─ *.csv 且文件存在 ───────→ mission-csv-execute
  ├─ *.md 且文件存在 ────────→ mission-doc-route ─┬─ approved-doc 路径
  │                                                  └─ long-task 路径
  ├─ 空 / "continue" / "resume" → mission-recovery
  ├─ 自然语言任务描述 ────────→ mission-long-task
  └─ 简单任务 ────────────────→ 不用 mission，直接干
```

`mission` 只做判断，不执行任务。

### 2. CSV 生成层

两条路径，最终都生成标准 CSV 喂给执行器：

- **`mission-approved-doc`**：已批准的 design doc / plan → `issues/<stem>/<stem>.csv`，**随代码一起提交**
- **`mission-long-task`**：自然语言任务 → `.mission/<stem>/<stem>.csv`，**本地恢复用，不提交**

`mission-approved-doc` 会先确认执行范围，再从源文档抽取 Claim/Evidence Ledger，写到 CSV 同目录的 `<stem>.claims.json`。组件 issue 之外，还会为启动注册、consumer、agent tool、flow 注入点这类生产路径生成独立接线 issue，避免"模块写了但没人调用"。

两条路径都强制在 CSV 末尾追加 `REVIEW-01`。REVIEW 行不能只写通用模板；它必须能回读源文档、CSV、claim ledger、测试证据和交付 diff。

### 3. 执行层（mission-csv-execute）

这是整套包的硬核内核。每条 issue 必须跑完完整闭环：

```
Step 0  接收与现实检查
Step 1  补齐执行信息（acceptance / required_skills / required_mcp / refs ...）
Step 2  启动状态（dev_state=进行中、review_initial_state=进行中）
Step 3  上下文收集（最小必要，5-8 次工具调用预算）
Step 4  实现（按 acceptance 拆最小变更集合，KISS/YAGNI）
Step 5  Review（两段式：initial + regression）
Step 6  自我验收（管线 vs 模块判定 + 走 required_mcp）
Step 6.5 声明-证据一致性检查
Step 7  写回 CSV
Step 8  Git 提交（issues/ 含 CSV，.mission/ 只提交代码）
Step 9  立刻下一条（不问、不停、不礼貌停顿）
```

四状态闭环判定：

| 状态                             | 含义                                |
| -------------------------------- | ----------------------------------- |
| `dev_state=已完成`               | 代码写完                            |
| `review_initial_state=已完成`    | 初始审查（这条 issue 本身写对了吗） |
| `review_regression_state=已完成` | 回归审查（有没有搞坏别的）          |
| `git_state=已提交`               | 已提交                              |

四个全到位 + `required_mcp` 证据齐 = 闭环。少一个都不行。

### 4. Vision Review（REVIEW-* 行）

整批 issues 闭环后，按能力阶梯做愿景验收：

- 优先用 direct `spawn_agent`
- 其次用 `codex exec --ephemeral --json --skip-git-repo-check --sandbox read-only`
- `codex review` 只能作为 diff 补充，不能代替 spec / CSV / claim ledger 对账
- 最后才允许主会话 fallback；fallback 只能写 `limited_review`，不能伪装成 `vision_met`

review log 写到 `<csv-path-without-.csv>.review.md`，给人看的交接文档写到 `<csv-path-without-.csv>.handoff.md`。handoff 落盘后还会跑 `check_handoff_contract.py`：文件名、CSV REVIEW notes 里的 `handoff:<path>`、Markdown 骨架都通过后，才会记录 `handoff_contract:passed`。如果 contract 失败，本轮不能写成 `vision_met`。

结果分三类：

- `vision_met` → 关闭 CSV
- `gaps_found` → 追加 follow-up issue 和 `REVIEW-(N+1)`，继续跑
- `limited_review` → 记录独立 review 能力不足，追加等待更强 review 能力的 rerun 行，避免原地无限 review

### 5. 恢复层（mission-recovery）

优先扫描 `issues/*/*.csv` 和 `.mission/*/*.csv`，并兼容旧版平铺的 `issues/*.csv` / `.mission/*.csv`。找到任何不满足四状态闭环的行后，定位断点并转发给 `mission-csv-execute`。

会话挂了、context 被压缩、key 没额度、电脑重启，全都能 resume 回来。

## Skill Reference

### `mission`

总入口。路由优先级：现有 CSV > Markdown 文档 > 空/continue（resume）> 自然语言任务 > Fallback（直接执行）。

> 关键原则：mission 自己不执行任务；执行态有粘性，进入执行器后默认持续推进，不会因为 checkpoint 或阶段总结把控制权交回。

### `mission-doc-route`

拿到 `.md` 文档时判断走哪条路：

- 文档在 `docs/superpowers/specs/` 或 `docs/superpowers/plans/`，或本身定义了 scope/tasks/acceptance/validation → **Approved Doc**
- 复杂任务说明 / 调查结论 / 分析报告 → **Long Task**
- 不确定 → 默认 Long Task（更轻）

### `mission-approved-doc`

把已批准的 design doc → `issues/<stem>/<stem>.csv`。

- **批准门**：未明确批准 → 硬停，不写代码
- **原子性**：单 issue 必须可独立验证、独立提交；多个独立验收场景必须拆行
- **Claim ledger 强制**：从源文档抽出可验证承诺，写入 `*.claims.json`，每条 claim 都要能追到 issue / evidence / production path
- **接线 issue 强制**：启动注册、consumer、agent tool、flow 注入点不能藏在组件 issue 里，必须显式生成或标注 deferred
- **REVIEW-01 强制**：从源文档和 claim ledger 抽出任务专属验收条件
- **生成阶段就写全** `required_skills` / `required_mcp` / `refs`

### `mission-long-task`

把自然语言任务拆成 5-15 条 atomic issues → `.mission/<stem>/<stem>.csv`。

- 复杂 bug 先跑 `superpowers:systematic-debugging` 抓根因，再拆
- 可选维护 CSV 同目录的 `log.md` 做决策日志
- `.mission/` 默认 gitignored

### `mission-csv-execute`

四状态闭环执行引擎，整套包的强内核。**完整的 Step 0-9、反暂停护栏、受限验收、独立 review、handoff 生成规则都在这个 SKILL.md 里**，文件较长（600+ 行），如果你想深读机制建议直接看源文件。

关键设计：

- **CSV 是唯一状态源**：需求变更先写回 CSV 再改代码
- **非终态 turn 必须以工具调用结尾**：不允许纯文本结束 turn
- **执行态优先于问答态**：可以简短回答用户问题，但回答完同一 turn 必须继续工具调用
- **干净边界谬误**：partial completion（3/9）是最脏的状态，不要因为"前 N 条做完了"就想收口
- **声明-证据等级一致**：低等级证据不能支撑高等级声明（unit test ≠ 集成通过、dry-run ≠ 真实发送）
- **独立 review 能力阶梯**：强 review 不可用时可以降级，但必须写 `limited_review`，不能把自审包装成通过
- **handoff 是交工单**：`review.md` 给 reviewer 看，`handoff.md` 给人看，二者不能混成一份审计模板

### `mission-recovery`

扫描 → 校验状态一致性 → 选择恢复对象 → 转发给 `mission-csv-execute`。本身不执行 issue。

发现状态不一致时会自动修正：

- `git_state=已提交` 但代码未提交 → 重置为 `未提交`
- `dev_state=已完成` 但 `review_*=未开始` → 从 review 阶段恢复

## Recommended Configuration

### AGENTS.md 路由层

在你的 `AGENTS.md` / `CLAUDE.md` 顶部加一段路由矩阵，告诉 agent 什么时候走 mission。一个最小例子：

```markdown
# 路由矩阵

用户请求
├─ 新能力 / 架构变更 → brainstorming → spec.md → mission <spec-doc.md>
├─ 已批准的 design doc → mission <doc-path.md>
├─ 已有 CSV → mission <csv-path>
├─ 复杂 bug / 长 refactor → mission <任务描述>
└─ 简单小任务 → 直接干

任何代码变更后：测试 → code-review → commit
```

### 配合 superpowers

这套包不重复造 brainstorming / code-review 这些通用 skill，建议搭配 [obra/superpowers](https://github.com/obra/superpowers) 一起用。典型流程：

```
你的需求
  │
  ├─ Claude Code: brainstorming → spec.md（讨论方案）
  │        ↓
  ├─ Claude Code: 转 issues/<stem>/<stem>.csv（落 CSV）
  │        ↓
  └─ Codex 或 Claude Code: mission @csv（闭环执行）
```

方案讨论一般在 Claude Code 里做（Opus brainstorming 稳），执行哪边都行，看你的偏好和成本。

### 配合 codex /goal 跑长任务（最佳实践）

跑长任务最稳的姿势是 Codex CLI + `/goal` 包住 mission，详见上面 Quick Start 的 Best Practice 小节。简单复述一遍：

```text
hello                                      # 先占位，第一条不能是 /goal
/goal @issues/<stem>/<stem>.csv            # mission 自动路由到 csv-execute
```

抗断联 + 强反暂停 + 可 resume，闭眼跑长任务的推荐姿势。

## Directory Layout

跑起来后你的项目目录会长这样：

```
your-project/
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-22-<topic>-design.md     # 与 Claude 讨论的 spec（手动写）
│
├── issues/                                       # ← 提交到仓库
│   └── 2026-05-22_10-00-00-<topic>/
│       ├── 2026-05-22_10-00-00-<topic>.csv          # approved-doc 生成的任务状态源
│       ├── 2026-05-22_10-00-00-<topic>.claims.json  # 源文档承诺账本
│       ├── 2026-05-22_10-00-00-<topic>.review.md    # vision review 审计日志
│       ├── 2026-05-22_10-00-00-<topic>.handoff.md   # 给人看的施工交工单
│       └── reviews/                                  # reviewer 原始输出 / prompt / jsonl
│
└── .mission/                                     # ← gitignored
    └── 2026-05-22_10-00-00-<task>/
        ├── 2026-05-22_10-00-00-<task>.csv       # long-task 生成
        ├── 2026-05-22_10-00-00-<task>.review.md # vision review 审计日志
        ├── 2026-05-22_10-00-00-<task>.handoff.md # 给人看的施工交工单
        ├── log.md                               # 决策日志
        ├── reviews/                             # reviewer 原始输出 / prompt / jsonl
        └── raw/                                 # 缓存外部数据
```

## CSV Schema 速览

固定 CSV 表头只由 `mission-csv-execute/csv-schema.md` 定义。`mission-approved-doc/doc-field-mapping.md` 只说明批准文档如何映射到这套表头，不是第二套 schema。

路径规则：

- `claim_ledger:<path>`、`handoff:<path>`、review log、handoff 和兜底文档的相对路径，优先按 CSV 所在目录解析。
- 新任务默认使用目录化 artifact root：`issues/<stem>/` 或 `.mission/<stem>/`。
- legacy 平铺 CSV 仍兼容显式输入和 recovery，但新产物不再默认写成平铺文件。

关键字段：

| 字段                                                         | 说明                                                         |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| `acceptance_criteria`                                        | 必须机器可验证，或有明确复现步骤                             |
| `test_mcp`                                                   | 验证策略：`AUTOSERVER` / `AUTOFRONTEND` / `AUTOE2E` / `CONTRACT` / `MIGRATION` / `MANUAL` |
| `required_skills`                                            | 必须读取并遵循的 skill 列表（执行合同）                      |
| `required_mcp`                                               | 必须实际调用的 MCP 工具（验收合同）                          |
| `refs`                                                       | 至少 1 个 `path:line`                                        |
| `dev_state` / `review_initial_state` / `review_regression_state` / `git_state` | 四状态闭环                                                   |
| `notes`                                                      | `picked_reason` / `done_at` / `skills_used` / `mcp_used` / `claim_ledger:<path>` / `review_agent_mode:<mode>` / `review_independence:<level>` / `claim_coverage:<covered>/<total>` / `claim_coverage_status:<status>` / `review_result:<result>` / `handoff:<path>` / `handoff_contract:passed` / `handoff_contract:failed <reason>` / `evidence` / `risk` / `blocked` / `validation_limited` 等 |

## FAQ

**Q: 一定要配 /goal 用吗？**
A: 不用，但**强烈推荐**。mission-csv-execute 自带反暂停护栏，可以独立跑长任务；套一层 `/goal` 能拿到抗断联 + 强反暂停 + 可 resume，是跑几小时长任务的最佳实践。短任务或单条 CSV 直接 `mission @xxx` 也够。

**Q: Codex 和 Claude Code 都能用，有什么差别？**
A: 两边的 skills 一模一样，触发方式略不同。Codex 还能套 `/goal` 拿到额外的抗断联能力（**长任务推荐这条路**）；Claude Code 没有 `/goal`，但 skill 自带的护栏 + `continue nonstop` 提示词也够用。方案讨论一般在 Claude Code 做（Opus brainstorming 稳）。

**Q: 跟 superpowers 是什么关系？**
A: 不冲突。superpowers 提供通用过程 skill（brainstorming、TDD、code-review 等），missions 提供任务编排和执行内核。建议一起装。

**Q: 跟 openspec 比呢？**
A: openspec 生成的计划复杂，agent 容易跑偏。这套包用一个 spec 文档 → CSV 的直通路径，实测对前端尤其友好。

**Q: 为什么 `.mission/` 不提交？**
A: `.mission/` 是本地恢复工件，含 timestamp 噪声，commit 进去没价值。`issues/` 才是正式任务，跟代码一起 review。

**Q: REVIEW 行能跳过吗？**
A: 不能。这是这套包"少返工"的关键。每个 CSV 末尾的独立愿景 review 会拿源文档、CSV、claim ledger、测试证据和实际 diff 对账；发现差距就追加 follow-up，独立 review 不可用时只能写 `limited_review`，不能伪装成通过。

**Q: 受限验收会不会被滥用？**
A: SKILL.md 里有明确的判定 few-shots——缺依赖、本地服务没启动、E2E "太复杂" 这些都**不构成**受限验收理由；只有需要付费服务、外部凭证、人工审批这种客观不可达才行。

**Q: 5.5 远程压缩有问题，跑长任务卡？**
A: 当前已知 OpenAI 没添加 5.5-compact 的模型名字，长任务建议用 5.4。

## Related

- 📖 [完整使用心得 / 故事版教程](./codex-missions.md) — 推荐先读
- 🔗 [superpowers](https://github.com/obra/superpowers) — agentic skills framework，强烈推荐配套使用
- 🔗 前置阅读：
  - [【教程】如何让 codex 任劳任怨跑几个小时](https://linux.do/t/topic/1353223)
  - [【保姆级教程】结合 openspec，如何让 codex 变成核动力牛马替你做 8 小时班](https://linux.do/t/topic/1445627)

## License

MIT

---

有 bug 或想法 → 提 issue。
有改进 → 提 PR。
跑起来了 → 摸鱼喝茶。
