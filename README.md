# Missions

Missions 是一套面向 Codex 和 Claude Code 的任务编排 skills。它把自然语言需求整理成可批准的 canonical spec，再生成 CSV 执行工件，按开发、初审、回归、提交四个状态持续推进，最后用独立 review 和 handoff 对照最初目标交工。


  ## 版本更新：从 Superpowers 配套模式迁移

  旧版 Missions 采用 Missions + Superpowers 的双柱结构：Superpowers 负责 brainstorming、计划编写、TDD、调试和 code
  review，Missions 负责把批准后的文档转换成 CSV 并持续执行。

  新版不再要求 Missions 配合 Superpowers。需求讨论、spec 批准、任务生成、CSV 执行、review 和 handoff 现在由 Missions 自
  己串成一条完整流程。
  
  ### 工作流变化

  - 需求讨论：`superpowers:brainstorming` → `mission-spec`
  - Spec 位置：`docs/superpowers/specs/` → `docs/specs/{YYYY-MM-DD}-{topic}.md`
  - Markdown 路由：`mission-doc-route` 根据路径和内容判断 → `mission` 根据 canonical frontmatter 路由
  - 长任务入口：`mission-long-task` → 自然语言需求先进入 `mission-spec`
  - 执行方式：Superpowers 计划技能配合 Missions → approved spec 直接生成 CSV 执行工件
  - Review：`superpowers:requesting-code-review` → 只读 reviewer、ephemeral review、self-review 三级回退
  - 工件目录：`.mission/{stem}/` 或 `issues/` → 统一使用 `issues/{stem}/`
  - 恢复范围：扫描 `.mission/` 和 `issues/` → 只扫描 `issues/`
    
  ### 迁移注意事项

  - mission-doc-route 和 mission-long-task 已删除，新增 mission-spec。
  - 旧的 .mission/ 任务不会再被自动恢复。需要继续执行的 CSV 应迁移到 issues/<stem>/，也可以通过完整路径显式执行。
  - 旧的 docs/superpowers/specs/ 和 plans/ 文档不再根据路径自动识别。需要继续使用的 spec 应迁移到 docs/specs/，并补充
    mission: spec frontmatter。

  - 新版不再生成单独的 implementation plan。spec 获批后，由 mission-approved-doc 生成执行工件，再交给 mission-csv-
    execute。

  - Superpowers 仍可作为通用开发技能单独使用，但已经不是 Missions 主流程的依赖。
  - 新版要求 Python 3.11+，必须安装 humanizer-zh；lite-arch 是建议依赖。

## 当前工作流

```text
自然语言 / 普通 Markdown / draft spec
  -> mission-spec
  -> 用户批准 canonical spec
  -> mission-approved-doc
  -> issues/<stem>/ 完整工件
  -> mission-csv-execute
  -> REVIEW-N + handoff
```

已有合法 CSV 可以直接进入执行器；`continue` / `resume` 由恢复器只扫描 `issues/`。旧版 `mission-doc-route`、`mission-long-task` 和默认 `.mission/` 流程已经移除。

## Skills

| Skill | 职责 |
|---|---|
| `mission` | 统一入口，按输入类型路由，不在入口内讨论或执行 |
| `mission-spec` | 逐项澄清需求、写 canonical spec、取得对精确内容的明确批准 |
| `mission-approved-doc` | 把已提交且未改动的 approved spec 映射成 `issues/<stem>/` 工件 |
| `mission-csv-execute` | 执行 CSV 状态机、验证证据、review、handoff 和提交 |
| `mission-recovery` | 在 `issues/` 中寻找未完成 CSV 并转回执行器 |

## 运行要求

- **Python 3.11 或更高版本。** 配置注册脚本使用标准库 `tomllib`，不支持 Python 3.10 及更早版本。
- **必须安装 [`humanizer-zh`](https://github.com/op7418/Humanizer-zh)。** `mission-spec` 用它处理自然语言正文，不改写 frontmatter、路径、命令或机器字段。
- **建议安装 [`lite-arch`](https://github.com/flowing-water1/lite-arch)。** 安装后，架构讨论会召回并记录 ADR；未安装时 mission 会明确跳过这道可选门禁，不阻断主流程。

`humanizer-zh` 上游推荐安装方式：

```bash
npx skills add https://github.com/op7418/Humanizer-zh.git
```

## 安装 Skills

先克隆仓库：

```bash
git clone https://github.com/flowing-water1/Missions.git
```

macOS / Linux：

```bash
# Codex
mkdir -p ~/.codex/skills
cp -r Missions/mission* ~/.codex/skills/

# Claude Code
mkdir -p ~/.claude/skills
cp -r Missions/mission* ~/.claude/skills/
```

Windows PowerShell：

```powershell
# Codex
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item .\Missions\mission* "$env:USERPROFILE\.codex\skills\" -Recurse -Force

# Claude Code
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item .\Missions\mission* "$env:USERPROFILE\.claude\skills\" -Recurse -Force
```

安装完成后，目标 skills 目录应包含：

```text
mission/
mission-spec/
mission-approved-doc/
mission-csv-execute/
mission-recovery/
```

重启 agent，让宿主重新发现 skills。

## 注册 Codex Reviewer

Missions 自带一个只读 `reviewer` 配置，固定使用 `gpt-5.6-sol` 和 high reasoning。注册它能让 `REVIEW-N` 优先走独立子代理；不注册也能继续使用后备的 ephemeral review 或 self-review。

macOS / Linux：

```bash
mkdir -p ~/.codex/agents
cp Missions/agents/reviewer.toml ~/.codex/agents/reviewer.toml
python Missions/config-fragments/register_reviewer.py \
  --config ~/.codex/config.toml \
  --fragment Missions/config-fragments/reviewer.toml \
  --backup ~/.codex/config.toml.pre-missions-reviewer
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\agents" | Out-Null
Copy-Item .\Missions\agents\reviewer.toml "$env:USERPROFILE\.codex\agents\reviewer.toml" -Force
python .\Missions\config-fragments\register_reviewer.py `
  --config "$env:USERPROFILE\.codex\config.toml" `
  --fragment .\Missions\config-fragments\reviewer.toml `
  --backup "$env:USERPROFILE\.codex\config.toml.pre-missions-reviewer"
```

注册脚本先保留原始备份，再原子写入并回读验证。已有不一致的 `[agents.reviewer]` 配置会报错，不会覆盖。

## 快速开始

```text
# 已有 CSV
mission @issues/2026-08-07-add-login/2026-08-07-add-login.csv

# 已批准且已提交的 canonical spec
mission @docs/specs/2026-08-07-add-login.md

# 自然语言需求，先讨论并生成 draft spec
mission 给登录页增加手机号验证码登录，包含 60 秒倒计时和重发逻辑

# 恢复 issues/ 中未完成的任务
mission continue
```

普通任务如果目标和验收已经清楚，不必强行进入 mission；直接实现并维护普通 plan 即可。

## Canonical Spec

`mission-spec` 默认写入 `docs/specs/<YYYY-MM-DD>-<topic>.md`。draft 的最小 frontmatter：

```yaml
---
mission: spec
status: draft
created: YYYY-MM-DD
---
```

正文至少包含 `Goal`、`Scope`、`Design` 和 `Acceptance Criteria`。用户批准后才会写入 `status: approved` 与带时区的 `approved_at`。

批准只对用户看到的那一版精确内容有效。批准后正文再有任何变化，都必须退回 draft 并重新批准。执行前，校验器还会确认 spec 已进入 `HEAD` 且工作副本没有改动。

## 执行工件

approved spec 会生成一个独立 artifact root：

```text
issues/<stem>/
├── <stem>.csv
├── <stem>.claims.json
├── <stem>.outcomes.json
├── <stem>.deferred.json
├── <stem>.review.md
├── <stem>.handoff.md
└── reviews/
```

- `claims.json`：逐条记录 spec 中可验证的承诺、覆盖 issue 和所需证据等级。
- `outcomes.json`：记录最终读者需要回答的问题、决定成败的结果和当前不可声称的结论。
- `deferred.json`：保存不属于当前范围的改进和未来决策，避免把它们误做成当前 follow-up。
- `review.md`：审查过程、模型证据和 finding 分类。
- `handoff.md`：给人看的交工单，说明做成了什么、没做成什么，以及怎样复现。

## CSV 闭环

CSV 固定使用 `mission-csv-execute/csv-schema.md` 定义的 19 列。普通 issue 只有同时满足以下状态才算关闭：

| 状态 | 终态 |
|---|---|
| `dev_state` | `已完成` |
| `review_initial_state` | `已完成` |
| `review_regression_state` | `已完成` |
| `git_state` | `已提交` |

执行器还会检查 `required_skills`、`required_mcp`、claim coverage 和证据等级。mock、fixture、dry-run、静态检查不能冒充真实集成或真实副作用。

CSV 末尾必须有 `REVIEW-01`。review 按以下顺序尝试：

1. 注册的只读 `reviewer` 子代理。
2. 只读 ephemeral `codex exec`。
3. 主代理按同一范围 self-review。

独立 reviewer 不可用不会中断任务，但必须如实记录实际 review 模式和独立性。发现当前范围缺口时追加 follow-up issue 与下一条 `REVIEW-N`；只有当前范围缺口清零后才能关闭任务。

## 恢复规则

`mission-recovery` 只扫描：

```text
issues/*/*.csv
issues/*.csv  # legacy 平铺格式
```

用户显式给出的任意合法外部 CSV 仍可执行，但不会被自动恢复器扫描。存在多个未完成任务时，恢复器会让用户选择，不会擅自并行推进。

## 验证

```bash
# mission-spec
python -m unittest discover -s mission-spec/scripts -p "test_*.py"

# CSV 执行器
python -m unittest discover -s mission-csv-execute/scripts -p "test_*.py"

# reviewer 注册
python -m unittest discover -s config-fragments -p "test_*.py"
```

## 配置模板

仓库根目录的 [AGENTS.md](./AGENTS.md) 和 [CLAUDE.md](./CLAUDE.md) 是可选的宿主路由示例，不需要复制进 skills 目录。更完整的使用流程见 [codex-missions.md](./codex-missions.md)。

## License

MIT
