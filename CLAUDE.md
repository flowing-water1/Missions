# 指令优先级

1. 当前会话中用户的明确要求
2. 仓库自身的规则、文档与约定
3. 相关 skill / protocol 的流程定义
4. 本文件的硬门禁与偏好

只做审查、分析、解释或问答时不进入实现流程。命中 skill 时先读对应 `SKILL.md`。

# 工作路由

- `mission <CSV>`：执行任意合法 CSV；执行态持续到终态，或用户明确暂停、取消、改变边界。
- `mission <approved spec>`：校验已提交且未改动后，由 `mission-approved-doc` 生成 `issues/<stem>/` 并执行。
- `mission <draft spec|Markdown|自然语言>`：由 `mission-spec` 讨论、写 draft、取得明确批准。
- `mission`、`continue`、`resume`、`继续`：由 `mission-recovery` 只扫描 `issues/`。
- 普通任务目标和验收清楚时直接执行；多步任务维护 plan。
- 分析、审查、解释、Q&A 直接回答。

需求未定时先澄清目标、约束和验收。`mission-spec` 每次只问一个仍会改变方案的问题；方案确定后尽快写 draft。未批准的 spec 禁止实现，批准后不再另写 implementation plan。

# 依赖

- Python 3.11+ 是脚本运行前提。
- `humanizer-zh` 必装；自然语言回复和 spec 正文在发送或提交前使用它处理，机器字段、代码、路径和命令不改写。
- `lite-arch` / `lite-arch-recall` 建议安装。已安装时在架构讨论和承重边界改动前使用；未安装时明确记录跳过，不阻断 mission。

# 实施纪律

- 改动紧贴批准范围和现有代码模式，不混入无关重构、格式化或调试痕迹。
- 先读即将修改的代码；使用结构化解析器处理 CSV、JSON、TOML 等格式。
- 系统边界校验外部输入；shell、SQL 使用安全参数传递。
- 不用 case 特化、固定答案或输出修补伪装 prompt、模型和测试能力。

# 测试与调试

- 可复现 bug 可行时先写失败回归测试。
- 新行为先明确验收和测试范围；核心逻辑优先 test-first。
- refactor 先依赖现有行为测试，只为实质覆盖缺口补测试。
- 文档、格式和机械配置不造假测试，但必须运行相关解析或人工验证。

测试是 commit、push、PR 前的硬门禁。只能报告实际运行的命令、退出码和结果；缺少证据时不得声称通过。代码变更后至少运行相关测试并检查 diff。

# Review

每个 mission 的 `REVIEW-N` 按顺序尝试：

1. 注册的只读 `reviewer` 子代理。
2. 只读 ephemeral `codex exec`。
3. 主代理按同一范围 self-review。

reviewer 不可用不应中断任务。self-review 可以闭环，但必须记录 `review_independence:false`。requested model、observed model、evidence source 分开记录；模型正文自报不算运行时证据。

普通代码变更在提交前也要 review，优先检查正确性、回归风险、安全和缺失测试。

# 安全与进程

- 未获授权不运行破坏性命令，不覆盖或丢弃用户改动，不使用 `git reset --hard`。
- 不硬编码、提交或输出密钥、凭证、API Key。
- 不终止非当前任务启动的进程。
- 长生命周期进程尽量少开，启动前检查可复用实例，结束即回收。

# Git 与提交

- 开始任务先记录 `git status` 和已暂存 patch，只 add 本任务路径。
- 同一路径有用户已暂存 patch，或 index delta 无法精确隔离时，停止提交并报告 blocker。
- 一个逻辑变更一个提交。提交前运行相关验证、检查 `git diff --check`、确认 staged 范围。
- 若仓库没有其他约定，使用 `<emoji> <type>(scope): 中文摘要`，正文写 `Why`、`Why this works`、`Remaining`。
- merge 前完成 review；push/PR 前再次确认测试证据和工作树边界。

# 沟通

- 默认简体中文，可混用英文术语。
- 执行任务优先报告当前动作、已完成、下一步和阻塞；分析任务先给结论，再给依据和权衡。
- 不编造事实、数字、日期、引用或验证结果。
- 多步任务维护可见计划，同一时刻只保留一个 `in_progress`。

# Skills

- `mission`：spec、CSV、执行与恢复的统一入口。
- `mission-spec`：需求讨论、canonical spec 和批准边界。
- `mission-approved-doc`：approved spec 到 issues 工件。
- `mission-csv-execute`：CSV 闭环执行、证据、review 与 handoff。
- `mission-recovery`：只扫描 `issues/` 的恢复入口。
- `humanizer-zh`：必装的自然语言处理 skill。
- `lite-arch` / `lite-arch-recall`：建议安装的 ADR 记录与召回 skills。
