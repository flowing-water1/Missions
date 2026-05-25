# 指令优先级

1. 当前会话中用户的明确要求
2. 仓库自身的规则、文档与约定
3. 相关 skill / protocol 的流程定义（`mission` / superpowers）
4. 本 `AGENTS.md` 的硬门禁与偏好

若本文件某项规则标注为"硬门禁"，则无论使用哪个 skill 都必须满足。
仅涉及审查、分析、解释的任务可不进入实现流程，但推理须清晰可追溯。

---

# 双柱架构

本项目的工作流由两根柱子支撑，AGENTS.md 是它们之上的路由层与硬约束层。

| 柱子 | 职责 | 触发方式 |
|------|------|----------|
| **mission** | 自包含任务编排与执行引擎（批准文档转 CSV、闭环执行、持久化恢复） | `mission <doc-path\|csv-path\|描述>` |
| **superpowers** | 过程技能库（brainstorming, TDD, debugging, code-review 等） | 按 skill description 自动匹配 |

---

# 路由矩阵

```
用户请求
  │
  ├─ 新能力 / breaking / 架构变更？
  │   → brainstorming → 产出 `docs/superpowers/specs/*.md` → 用户批准 → mission <spec-doc.md>
  │
  ├─ 已批准的 design doc / plan doc？
  │   → mission <doc-path.md>
  │
  ├─ 已有 task CSV（`issues/*.csv` 或 `.mission/*.csv`）？
  │   → mission <csv-path>
  │
  ├─ 复杂 bug / 长时 refactor（需持久化/恢复）？
  │   → systematic-debugging → mission <任务描述>
  │
  ├─ 已有本轮 implementation plan，且用户要求按计划施工？
  │   → executing-plans 或 subagent-driven-development
  │
  ├─ 功能开发 / bug 修复 / 行为变更？
  │   → test-driven-development
  │
  ├─ 分析 / 审查 / 解释 / Q&A？
  │   → 直接回答
  │
  └─ 简单明确的小任务？
      → 直接执行 + update_plan

任何代码变更后：测试 → code-review → commit
```

- 需求模糊时先澄清目标、约束与验收标准，再选路由。
- 用户要求 `continue nonstop` 时持续推进直到验收或阻塞。
- 前端设计务必使用 `ui-ux-pro-max` 技能。
- 代码架构搜索优先用 `ace-tool`；`rg` 只用于已知字符串精确定位。
- 分析代码问题和修复 bug 时启用 `sequential-thinking`。

---

# 硬门禁

以下规则无论走哪条路由都不可违反。

## 验证（硬门禁）

- **测试是硬门禁**。commit/push/PR 前必须运行相关测试并如实报告。
- 功能开发、bug 修复、行为变更默认 TDD。
- 不得虚构命令、退出码或验证结果。缺少证据时不得声称"通过"。
- `pre-commit` 是推荐实践，非阻断项（除非用户/仓库明确要求）。


## 安全（硬门禁）

- 无用户授权不运行破坏性命令（`git reset`、危险删除等）
- 不硬编码密钥/凭证/API Key
- 参数化查询，不拼接不可信输入构造 shell/SQL
- 系统边界校验并清理外部输入
- 不终止非当前任务启动的进程

## 进程治理

- 长生命周期进程：最少新增、优先复用、结束即回收
- 启动前检查端口占用和可复用进程
- 启动后确认真实可访问，不把"已启动"等同于"成功"

---

# 提交约定

## 前置条件

- commit/push/PR 前满足硬门禁中的验证要求
- merge 前完成 `requesting-code-review` 或 `/review`

## 提交粒度

- 一个逻辑变更一个提交，边界清晰可审查
- 不混入无关格式化、调试痕迹
- 先 `git status` 确认改动范围，只 add 相关文件

## Commit Message

格式：`<emoji> <type>(scope): summary`

| 类型 | Emoji | 说明 |
|------|-------|------|
| init | 🎉 | 项目初始化 |
| feat | ✨ | 新功能 |
| fix | 🐞 | 错误修复 |
| docs | 📃 | 文档变更 |
| style | 🌈 | 代码格式化（不影响逻辑） |
| refactor | 🦄 | 代码重构 |
| perf | 🎈 | 性能优化 |
| test | 🧪 | 测试相关 |
| build | 🔧 | 构建系统或外部依赖 |
| ci | 🐎 | CI 配置 |
| chore | 🐳 | 辅助工具变动 |
| revert | ↩ | 撤销提交 |

- scope 用模块/目录，无明确范围可省略
- summary 中文、动词开头、≤ 50 字、不加句号
- **正文默认必写**，至少覆盖三点：
  - `Why:` 为什么要改
  - `Why this works:` 为什么这样改有效（验证证据 / 设计理由 / 根因修复）
  - `Remaining:` 还剩什么工作、已知限制、后续建议
- 破坏性变更：type 后加 `!` 或正文写 `BREAKING CHANGE: ...`

推荐正文模板：

```text
Why:
- <问题 / 目标>

Why this works:
- <设计理由 / 验证结果 / 根因修复依据>

Remaining:
- <后续 issue / 已知缺口 / 下一步>
```

---

# 沟通偏好

## 语言

- 默认简体中文，可混用英文术语
- 代码标识符英文，代码注释简体中文

## 输出风格

- **执行类任务**：进度优先 — 当前动作、已完成、下一步、风险/阻塞、`path:line` 引用
- **分析类任务**：结论优先 — 核心判断、依据与权衡、实施建议
- **简单查询**：直接回答，不加框架
- 多步任务用 `update_plan` 跟踪，不重复输出完整计划
- 复杂内容后附简短总结，结尾给出下一步建议

## 进度追踪

- 多步任务（≥ 3 步）维护可见任务列表
- 同一时刻仅一个 `in_progress`，完成即标记
- 总结变更并突出下一步，不重复完整计划

---

# 技能注册表

| 技能 | 用途 |
|------|------|
| `mission` | 复杂多步任务的编排与执行引擎（详见 `C:\Users\Flow_Water\.codex\skills\mission\SKILL.md`） |
| `ui-ux-pro-max` | 前端设计（必须用于前端 UI 任务） |
| superpowers 全系列 | brainstorming, writing-plans, executing-plans, TDD, systematic-debugging, code-review, etc. |

开始任务前优先判断是否有匹配的 skill。命中则读取其 `SKILL.md` 并按流程执行。


## Frontend tasks

When doing frontend design tasks, avoid generic, overbuilt layouts.

**Use these hard rules:**
- One composition: The first viewport must read as one composition, not a dashboard (unless it's a dashboard).
- Brand first: On branded pages, the brand or product name must be a hero-level signal, not just nav text or an eyebrow. No headline should overpower the brand.
- Brand test: If the first viewport could belong to another brand after removing the nav, the branding is too weak.
- Typography: Use expressive, purposeful fonts and avoid default stacks (Inter, Roboto, Arial, system).
- Background: Don't rely on flat, single-color backgrounds; use gradients, images, or subtle patterns to build atmosphere.
- Full-bleed hero only: On landing pages and promotional surfaces, the hero image should be a dominant edge-to-edge visual plane or background by default. Do not use inset hero images, side-panel hero images, rounded media cards, tiled collages, or floating image blocks unless the existing design system clearly requires it.
- Hero budget: The first viewport should usually contain only the brand, one headline, one short supporting sentence, one CTA group, and one dominant image. Do not place stats, schedules, event listings, address blocks, promos, "this week" callouts, metadata rows, or secondary marketing content in the first viewport.
- No hero overlays: Do not place detached labels, floating badges, promo stickers, info chips, or callout boxes on top of hero media.
- Cards: Default: no cards. Never use cards in the hero. Cards are allowed only when they are the container for a user interaction. If removing a border, shadow, background, or radius does not hurt interaction or understanding, it should not be a card.
- One job per section: Each section should have one purpose, one headline, and usually one short supporting sentence.
- Real visual anchor: Imagery should show the product, place, atmosphere, or context. Decorative gradients and abstract backgrounds do not count as the main visual idea.
- Reduce clutter: Avoid pill clusters, stat strips, icon rows, boxed promos, schedule snippets, and multiple competing text blocks.
- Use motion to create presence and hierarchy, not noise. Ship at least 2-3 intentional motions for visually led work.
- Color & Look: Choose a clear visual direction; define CSS variables; avoid purple-on-white defaults. No purple bias or dark mode bias.
- Ensure the page loads properly on both desktop and mobile.
- For React code, prefer modern patterns including useEffectEvent, startTransition, and useDeferredValue when appropriate if used by the team. Do not add useMemo/useCallback by default unless already used; follow the repo's React Compiler guidance.

Exception: If working within an existing website or design system, preserve the established patterns, structure, and visual language.

---




# 其他注意事项
1. 后端和前端自行拉起，前端调试可以用chrome-dev-tools, playwright去进行调试。
