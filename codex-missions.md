# 让长任务可控、坚韧：mission + /goal 让 codex 变成"牛马完全体"

## 前言

之前写过两个帖子，介绍了怎么使用 csv 然后来让 codex 一直跑，佬友们反馈也都不错：

- [【教程】如何让 codex 任劳任怨跑几个小时](https://linux.do/t/topic/1353223)
- [【保姆级教程】结合 openspec，如何让 codex 变成核动力牛马替你做 8 小时班](https://linux.do/t/topic/1445627)

但是在 5.4、5.5 出来后，我发现用这套流程，codex 经常跑一会就停了，并且当时看佬友们偶尔也会遇到这个问题，就觉得可能流程需要改进。在这期间逛论坛，也看到不少佬友有自己的流程，但是基本上是基于 cc 的，而且将流程嵌到 cc 里总觉得太贵了，A/罪大恶极，于是投身 codex 这个性价比拉满的工具中研究流程。最终改来改去，出来这套自己觉得过得去的流程。昨天试了一下，发现跑完 6h 之后竟然没有出错，没有偷懒，属实有点高兴，于是想着是时候分享出来给大伙了。

> 这套流程说到底跟之前一样，仍然是"讨论方案" + "csv 执行"，只是改良了而已，变成 Claude Code 和 Codex 协同作业。方案由 Claude 产生，csv 由 Codex 执行。

不嵌入太多其他功能，因为我觉得其他的功能，superpower、b-mad，或者论坛里其他佬友的都已经创造出很多覆盖全流程的 skills 包了，没必要再搞一套。实际上我自己用的就是 superpower + 我自己的这套 skills 包就完事了。现在主力就是这两套。superpower 中，其实我用最多的是 brainstorming、design spec 生成这两个 skill，write plan 一开始还会用，后来也觉得没必要了，反而会限制发挥。

为什么抛弃 openspec 和 plan 文档？因为我发现，不是"越详细越好"，反而是一个文档，然后生成 csv 的形式效果最好。openspec 人难读，然后生成的计划很复杂，甚至可能过了火，经常完成不好，对，就是越详细反而越难完成。这点在前端更是！

So, 言归正传，我会一边介绍流程，一边说说自己的心得，抛砖引玉，供佬友们参考。

---

## 1. /goal：让 codex 真正跑到底

这套流程的执行入口，我用的是 codex 的 `/goal`。它解决了几个长任务里很关键的问题：自从出了5.4，在执行csv的时候，总是会莫名其妙停下，没有任何来由地停下，就像claude code一样，不知道是降智了还是怎么样，无论是给csv excute加各种MUST，还是给生成的csv加条件，都不行，但是/goal一出来就变天了，哪来那么多花里胡哨的，一个/goal就完事了，就算是api供应商掉线了，他也会挂着，直到你让供应商恢复，他就会自动resume了，就算你不小心关机了，再回来也自动resume，完全不用担心！所以我们的任务不再是“怎么跑得久”，而是“怎么跑得好”！于是接下来的流程就应运而生了。

下面是完整的流程，AGENTS.md、superpowers、mission skills、CSV 四状态闭环——执行那一下交给 `/goal`，其余照旧。

---

## 2. AGENTS.md 和 CLAUDE.md 配置

这是我的 AGENTS.md 和 CLAUDE.md，**建议去第4章的 github 地址中复制，这里只是给大伙看一下**：

<details>
<summary>AGENTS.md（对于 CLAUDE，也就是把 AGENTS 换成 CLAUDE，然后目录换一下就行）</summary>

> # 指令优先级
>
> 1. 当前会话中用户的明确要求
> 2. 仓库自身的规则、文档与约定
> 3. 相关 skill / protocol 的流程定义（`mission` / superpowers）
> 4. 本 `AGENTS.md` 的硬门禁与偏好
>
> 若本文件某项规则标注为"硬门禁"，则无论使用哪个 skill 都必须满足。
> 仅涉及审查、分析、解释的任务可不进入实现流程，但推理须清晰可追溯。
>
> ---
>
> # 双柱架构
>
> 本项目的工作流由两根柱子支撑，AGENTS.md 是它们之上的路由层与硬约束层。
>
> | 柱子            | 职责                                                         | 触发方式                      |
> | --------------- | ------------------------------------------------------------ | ----------------------------- |
> | **mission**     | 自包含任务编排与执行引擎（批准文档转 CSV、闭环执行、持久化恢复） | `mission <doc-path>`           |
> | **superpowers** | 过程技能库（brainstorming, TDD, debugging, code-review 等）  | 按 skill description 自动匹配 |
>
> ---
>
> # 路由矩阵
>
> ```
> 用户请求
> │
> ├─ 新能力 / breaking / 架构变更？
> │   → brainstorming → 产出 `docs/superpowers/specs/*.md` → 用户批准 → mission <spec-doc.md>
> │
> ├─ 已批准的 design doc / plan doc？
> │   → mission <doc-path.md>
> │
> ├─ 已有 task CSV（`issues/*.csv` 或 `.mission/*.csv`）？
> │   → mission <csv-path>
> │
> ├─ 复杂 bug / 长时 refactor（需持久化/恢复）？
> │   → systematic-debugging → mission <任务描述>
> │
> ├─ 已有本轮 implementation plan，且用户要求按计划施工？
> │   → executing-plans 或 subagent-driven-development
> │
> ├─ 功能开发 / bug 修复 / 行为变更？
> │   → test-driven-development
> │
> ├─ 分析 / 审查 / 解释 / Q&A？
> │   → 直接回答
> │
> └─ 简单明确的小任务？
>    → 直接执行 + update_plan
>
> 任何代码变更后：测试 → code-review → commit
> ```
>
> * 需求模糊时先澄清目标、约束与验收标准，再选路由。
> * 用户要求 `continue nonstop` 时持续推进直到验收或阻塞。
> * 前端设计务必使用 `ui-ux-pro-max` 技能。
> * 代码架构搜索优先用 `ace-tool`；`rg` 只用于已知字符串精确定位。
> * 分析代码问题和修复 bug 时启用 `sequential-thinking`。
>
> ---
>
> # 硬门禁
>
> 以下规则无论走哪条路由都不可违反。
>
> ## 验证（硬门禁）
>
> * **测试是硬门禁**。commit/push/PR 前必须运行相关测试并如实报告。
> * 功能开发、bug 修复、行为变更默认 TDD。
> * 不得虚构命令、退出码或验证结果。缺少证据时不得声称"通过"。
> * 声明与证据等级必须一致：unit test、mock、fixture、dry-run、字符串检查等低等级证据，不得包装成真实集成、真实副作用、E2E 或生产可用结论。
> * **测试或外部验证可以受限，但必须如实写明；不得为了让流程跑绿而造替代路径、假数据或假测试来冒充原目标通过。**
> * `pre-commit` 是推荐实践，非阻断项（除非用户/仓库明确要求）。
>
> ## 安全（硬门禁）
>
> * 无用户授权不运行破坏性命令（`git reset`、危险删除等）
> * 不硬编码密钥/凭证/API Key
> * 参数化查询，不拼接不可信输入构造 shell/SQL
> * 系统边界校验并清理外部输入
> * 不终止非当前任务启动的进程
>
> ## 进程治理
>
> * 长生命周期进程：最少新增、优先复用、结束即回收
> * 启动前检查端口占用和可复用进程
> * 启动后确认真实可访问，不把"已启动"等同于"成功"
>
> ---
>
> # 提交约定
>
> ## 前置条件
>
> * commit/push/PR 前满足硬门禁中的验证要求
> * merge 前完成 `requesting-code-review` 或 `/review`
>
> ## 提交粒度
>
> * 一个逻辑变更一个提交，边界清晰可审查
> * 不混入无关格式化、调试痕迹
> * 先 `git status` 确认改动范围，只 add 相关文件
>
> ## Commit Message
>
> 格式：`<emoji> <type>(scope): summary`
>
> | 类型     | Emoji | 说明                     |
> | -------- | ----- | ------------------------ |
> | init     | 🎉     | 项目初始化               |
> | feat     | ✨     | 新功能                   |
> | fix      | 🐞     | 错误修复                 |
> | docs     | 📃     | 文档变更                 |
> | style    | 🌈     | 代码格式化（不影响逻辑） |
> | refactor | 🦄     | 代码重构                 |
> | perf     | 🎈     | 性能优化                 |
> | test     | 🧪     | 测试相关                 |
> | build    | 🔧     | 构建系统或外部依赖       |
> | ci       | 🐎     | CI 配置                  |
> | chore    | 🐳     | 辅助工具变动             |
> | revert   | ↩     | 撤销提交                 |
>
> * scope 用模块/目录，无明确范围可省略
> * summary 中文、动词开头、≤ 50 字、不加句号
> * **正文默认必写**，至少覆盖三点：
>   * `Why:` 为什么要改
>   * `Why this works:` 为什么这样改有效（验证证据 / 设计理由 / 根因修复）
>   * `Remaining:` 还剩什么工作、已知限制、后续建议
> * 破坏性变更：type 后加 `!` 或正文写 `BREAKING CHANGE: ...`
>
> 推荐正文模板：
>
> ```text
> Why:
> - <问题 / 目标>
>
> Why this works:
> - <设计理由 / 验证结果 / 根因修复依据>
>
> Remaining:
> - <后续 issue / 已知缺口 / 下一步>
> ```
>
> ---
>
> # 沟通偏好
>
> ## 语言
>
> * 默认简体中文，可混用英文术语
> * 代码标识符英文，代码注释简体中文
>
> ## 输出风格
>
> * **执行类任务**：进度优先 --- 当前动作、已完成、下一步、风险/阻塞、`path:line` 引用
> * **分析类任务**：结论优先 --- 核心判断、依据与权衡、实施建议
> * **简单查询**：直接回答，不加框架
> * 多步任务用 `update_plan` 跟踪，不重复输出完整计划
> * 复杂内容后附简短总结，结尾给出下一步建议
>
> ## 进度追踪
>
> * 多步任务（≥ 3 步）维护可见任务列表
> * 同一时刻仅一个 `in_progress`，完成即标记
> * 总结变更并突出下一步，不重复完整计划
>
> ---
>
> # 技能注册表
>
> | 技能               | 用途                                                         |
> | ------------------ | ------------------------------------------------------------ |
> | `mission`          | 复杂多步任务的编排与执行引擎（详见 `C:\Users\Flow_Water\.codex\skills\mission\SKILL.md`） |
> | `ui-ux-pro-max`    | 前端设计（必须用于前端 UI 任务）                             |
> | superpowers 全系列 | brainstorming, writing-plans, executing-plans, TDD, systematic-debugging, code-review, etc. |
>
> 开始任务前优先判断是否有匹配的 skill。命中则读取其 `SKILL.md` 并按流程执行。
>
> ## Frontend tasks
>
> When doing frontend design tasks, avoid generic, overbuilt layouts.
>
> **Use these hard rules:**
>
> * One composition: The first viewport must read as one composition, not a dashboard (unless it's a dashboard).
> * Brand first: On branded pages, the brand or product name must be a hero-level signal, not just nav text or an eyebrow. No headline should overpower the brand.
> * Brand test: If the first viewport could belong to another brand after removing the nav, the branding is too weak.
> * Typography: Use expressive, purposeful fonts and avoid default stacks (Inter, Roboto, Arial, system).
> * Background: Don't rely on flat, single-color backgrounds; use gradients, images, or subtle patterns to build atmosphere.
> * Full-bleed hero only: On landing pages and promotional surfaces, the hero image should be a dominant edge-to-edge visual plane or background by default. Do not use inset hero images, side-panel hero images, rounded media cards, tiled collages, or floating image blocks unless the existing design system clearly requires it.
> * Hero budget: The first viewport should usually contain only the brand, one headline, one short supporting sentence, one CTA group, and one dominant image. Do not place stats, schedules, event listings, address blocks, promos, "this week" callouts, metadata rows, or secondary marketing content in the first viewport.
> * No hero overlays: Do not place detached labels, floating badges, promo stickers, info chips, or callout boxes on top of hero media.
> * Cards: Default: no cards. Never use cards in the hero. Cards are allowed only when they are the container for a user interaction. If removing a border, shadow, background, or radius does not hurt interaction or understanding, it should not be a card.
> * One job per section: Each section should have one purpose, one headline, and usually one short supporting sentence.
> * Real visual anchor: Imagery should show the product, place, atmosphere, or context. Decorative gradients and abstract backgrounds do not count as the main visual idea.
> * Reduce clutter: Avoid pill clusters, stat strips, icon rows, boxed promos, schedule snippets, and multiple competing text blocks.
> * Use motion to create presence and hierarchy, not noise. Ship at least 2-3 intentional motions for visually led work.
> * Color & Look: Choose a clear visual direction; define CSS variables; avoid purple-on-white defaults. No purple bias or dark mode bias.
> * Ensure the page loads properly on both desktop and mobile.
> * For React code, prefer modern patterns including useEffectEvent, startTransition, and useDeferredValue when appropriate if used by the team. Do not add useMemo/useCallback by default unless already used; follow the repo's React Compiler guidance.
>
> Exception: If working within an existing website or design system, preserve the established patterns, structure, and visual language.
>
> ---
>
> # 其他注意事项
>
> 1. 后端在 8222 端口，前端在 3463 端口，前端调试可以用 chrome-dev-tools、playwright、screenpipe 去 localhost:3463 进行调试。

</details>

这是我之前从一些佬友的经验中摘取出来的。但是我发现，其实没必要给太多的限制，给太多限制反而发挥不好（codex 会很遵守 AGENTS.md，但是 Claude Code 不一定），所以放宽了一些规则。佬友们可以看着加，看着改。**关键就是在 AGENTS.md / CLAUDE.md 中，有"路由"的概念**。

这是我参考 superpower 和 skills 的思路来改的。"路由"这个思路很好。实际上这样子的话，AGENTS.md / CLAUDE.md 能在自由发挥最大能力的同时又能知道：我该在什么时候干什么。更具体的就像 skills 的概念一样，渐进式披露给 Agent 执行。

最后的 Frontend tasks 纯粹是因为 codex 前端太差了想要加上去看看能不能好一点，实际上也好不了多少。（但是我自己也摸索出一套前端的流程，之后再写出来分享给大伙。）

最后的"其他注意事项"，我建议佬友们根据自己的项目来加，比如说有啥账号密码，还有哪些库应该用什么，端口在哪，不然每次跑，他都有可能去查，这样就会浪费时间了。

---

## 3. 安装 Superpowers（可选）

如果你不想动脑了，就想着照着我的流程来，那么这里是告诉你去安装 superpower。如果你有自己的工程 skills 包，那你可以略过，不影响后续使用。

superpower 我觉得应该不用过多介绍，从 superclaude -> b-mad -> superpower，为什么就 superpower 火得一塌糊涂，我觉得还是有原因的。首先一点是，他介于"麻烦、复杂"和"太简单了"之间。我记得一开始 superclaude 要用的时候，还得去看各种命令有什么用，这样子不亚于学一门新语言，非常麻烦。b-mad 也同理。后来出了 skills，agent 能按需触发，superpower 这种就火了。

但是，superpower 也有他的弊端，就是太啰嗦了，经常一个小问题就要问很多遍。但是我不知道为什么，不知道是不是开了记忆功能，还是改了 AGENTS.md，现在他问的反而是"刚刚好"，这点我也不知道。**如果他问得太多，太啰嗦了，你可以叫他别问了，直接开始 xxx 就行。**

也就是，我们在流程中需要的是 brainstorming、写 spec，这两个 skills 可以主动选择触发，其他的什么都不用管即可！

SuperPower 的地址：[obra/superpowers: An agentic skills framework & software development methodology that works.](https://github.com/obra/superpowers)

安装非常方便，不会的话就让 AI 帮你吧。记得，Claude Code 和 Codex 都需要安装。

---

## 4. 安装$mission 



**$mission 的地址： [flowing-water1/Missions](https://github.com/flowing-water1/Missions)，把mission 包复制到对应地址就行了，不然就让claude code 和codex帮你。**



`$mission` 是任务路由器，下面这些触发方式都成立。最终执行那一下，统一走 `/goal @xxx.csv`。

`$mission` 其实是一个统一入口，会自动路由：

- `$mission issues/xxx.csv` -> 直接执行已有的 CSV
- `$mission docs/superpowers/specs/xxx.md` -> 识别为文档，判断走 approved-doc 还是 long-task
- `$mission 一段复杂的任务描述` -> 自动拆解成 CSV 再执行（走 mission-long-task）
- `$mission`（空输入）或 `$mission continue` -> 恢复上次中断的任务（走 mission-recovery）

也就是说，你甚至不需要先写 spec 再转 CSV。如果你的需求已经很清晰了，直接丢一段描述给 `$mission`，它会自己拆解成 5-15 条 atomic issues 的 CSV，然后开始执行。这条路径就是 **mission-long-task**（推荐让claude code来完成任务，codex对于文档任务效果很差）。

那什么时候走 spec -> CSV 的路径（mission-approved-doc）？当你的需求比较复杂、需要跟 Claude 反复讨论对齐的时候。你就可以用brainstroming先跟codex/ claude code讨论，然后用superpower的spec写成文档，然后再让他用 `$mission`转成csv，详细看之后的流程。 

---

## 5. 安装 Mission Skills 包

也是很简单，拉下来之后只把 `mission*` 这些 skill 目录放到 `C:\Users\用户名\.codex\skills` 中就行。仓库根目录的 README、`codex-missions.md`、AGENTS/CLAUDE 示例不用拷进 skills 目录。

整个 skills 包同样是参考 superpower 的路由思路：

- **mission、mission-doc-route** 负责路由
- **mission-approved-doc** 负责生成 csv 文件
- **mission-csv-execute** 负责执行 csv 文件
- **mission-recovery** 负责恢复执行（因为在执行过程中，可能因为各种原因中断，所以有了这个恢复，就算 key 额度不够，或者不稳定也不用太担心）

其中 `mission-csv-execute/scripts/` 现在也属于包的一部分，里面有三个辅助脚本：`run_vision_review.py` 跑独立愿景 review，`validate_claim_ledger.py` 校验 claim ledger，`lint_handoff.py` 检查交工单骨架。安装时不要漏掉这个目录。

这里面我觉得需要提一点，这也是"少返工"的关键点：**在 csv 的末尾加一条 review 的 issue**。对！就这么简单！但是现在这条 review 已经不只是"看一眼有没有做完"了。

新版本会在 spec 转 CSV 时先抽一份 `*.claims.json`，把源文档里能验证的承诺逐条记下来：这条承诺来自哪一行、由哪个 issue 覆盖、需要什么证据、有没有生产路径。执行完之后，REVIEW 行会拿源文档、CSV、claim ledger、测试证据和代码 diff 一起对账。这样就不太容易出现"写了组件，但没接进启动流程"或者"跑了 mock，却说真实链路通了"这种情况。

还有一个变化是 `handoff.md`。以前跑完主要看 `review.md`，但 `review.md` 更像审计日志，过几天再看其实挺累。现在 REVIEW 后会额外产出一份交工单，把这轮做了什么、哪些目标兑现了、哪里降级了、怎么复现，用人话写出来。

> **注意**：现在 5.5 的远程压缩是有问题的，本质原因似乎是因为 OpenAI 没添加 5.5-compact 的模型名字，直到现在都没修。所以只能用 5.4 来执行长任务。我试过在 cch 中添加模型映射，但是无济于事，添加 `stream_idle_timeout_ms = 9000000` 也没有用。如果有懂的佬友可以分享解决办法。

在此之外，你还可以准备别的 MCP 工具，比如说 chrome-dev-tool 调试浏览器、数据库工具什么的，这里就看自己了。

---

## 6. 开始执行流程

现在基本上都准备完了，就可以开始流程了。

### 步骤一：用 Claude 讨论方案

我强烈建议用 Opus 4.6 来讨论方案，4.7 也可以，但是 4.7 偶尔会说黑话，4.6 说黑话少，便于理解。流程如下：

> 你提一大段要求 -> 他用 brainstorming 问你细节（如果没问就主动提及） -> 觉得差不多了，就让他落成 spec 文档

他在最后可能会说"要不要落成 plan 文档？"，但是我不建议，问就是我觉得效果不好，我觉得落成 plan 文档再转换成 csv 执行的效果，还不如直接从 spec 转成 csv 的效果好。我觉得可能还是 spec 文档中，Claude 的发挥空间能更大。

示例：

![image](https://cdn3.ldstatic.com/original/4X/2/d/e/2de655b1cc69f4b5b5d53129d1d91bb498b6751d.png)

以上应该触发 superpower 的 brainstorming 和 spec skills。

### 步骤二：让 Claude 转成 CSV

这里也建议让 Claude 转，而不是 Codex，因为 Codex 倾向于"少"，经常会漏东西，Claude 就会转得很详细，虽然 issues 条数很多，经常十几二十条，执行时间会很长，但是也是时间换准确率了。起码我觉得会好很多。

示例：

![image](https://cdn3.ldstatic.com/original/4X/e/4/6/e460519df47150805544cd5b1ed0408bcccc3b18.png)

以上应该触发 missions 的 mission-approved-doc skill。

### 步骤三：切到 Codex 执行

切到 Codex：

1. **先发一句 `hello`（随便什么都行），等 codex 回一句。这一步不能省——如果第一条就是 `/goal`，那条记录会消失，resume 时找不回上下文。**
2. 然后 `/goal @你的csv文件`。
3. 你就可以去摸鱼喝茶了，等。

中途供应商抖了、key 没额度了不用慌，`/goal` 不会中断，等你恢复供应商就接着跑。要是终端要关、电脑要重启，放心退出，回来 `codex resume` 找到这次会话，它会自动继续——前提是开头发过 hello。

`$mission` 是任务路由器（spec → CSV、long-task 拆解、recovery 等路由都走它），下面这些章节都成立；最终执行那一下走 `/goal`。

示例：

![image-20260522155829924](C:\Users\Flow_Water\AppData\Roaming\Typora\typora-user-images\image-20260522155829924.png)

所以说你就不需要记那么多东西，只需要思考怎么对齐要求，然后生成文档，生成 csv，然后开始跑，就 OK 了！你就可以在旁边摸鱼喝茶了，让 5.4 跑个几小时，然后应该就 OK 了，效果应该也是过得去的，起码在我自己这是 OK 的。他会自己去测试，跑通，遇到跑不通的，也是先继续完成，并且在之后提醒你，很少骗人。之前我发现 codex 很容易做什么 smoke 测试，然后假装跑通，用假数据骗人。但是用这一套新流程之后，很明显就是史诗级牛马，只玩真的了。  

### 步骤四：等结果，然后看他跑得怎么样

跑完之后，先看同目录下的三类产物：

- `*.review.md`：给 reviewer / agent 看的审计日志，里面会写本轮 review 怎么跑、有没有 gap、证据够不够。
- `*.handoff.md`：给人看的交工单，重点看这份。它会按 spec 目标对账，说清楚做成了什么、没做成什么、哪里降级了。
- `*.claims.json`：源文档承诺账本。一般不用你手动看，除非你怀疑某个目标漏了，可以拿它反查 claim 有没有被 issue 覆盖。

现在不太需要你再手动开新 session 做一次泛泛的 review。更有用的做法是：打开 `handoff.md`，按它给的复现步骤自己试一遍；如果你发现产品预期不对，再把那条预期补回 spec 或 CSV。

![image-20260522160235428](C:\Users\Flow_Water\AppData\Roaming\Typora\typora-user-images\image-20260522160235428.png)



---

## 7. 目录结构

你应该会有这样的文件目录：****

```
docs/
└── superpowers/
    └── specs/
        └── 你和 claude 讨论的 spec 文档

issues/
├── 2026-xx-xx_xx-xx-xx-xxx.csv          # approved-doc 生成的任务状态源
├── 2026-xx-xx_xx-xx-xx-xxx.claims.json  # 源文档承诺账本
├── 2026-xx-xx_xx-xx-xx-xxx.review.md    # 给 reviewer/agent 看的审计日志
└── 2026-xx-xx_xx-xx-xx-xxx.handoff.md   # 给人看的施工交工单

.mission/
├── 2026-xx-xx-xxx.csv                    # long-task 生成，本地恢复用，不默认提交
└── xxx/
    ├── log.md                            # 可选决策日志
    └── raw/                              # 可选外部数据缓存
```

---

## 8. 为什么"少返工"？—— CSV 的四状态闭环机制

为什么能“少返工”，主要是 csv 的四个状态字段和最后的愿景验收。四个状态字段跟之前差不多，只有 4 条尽量都完成了，才会进入下一步。遇到客观跑不通的情况，不是静默跳过，而是写清楚受限验收、风险和后续动作。

现在跑完不只会产出 `review.md`。如果是从 approved doc 生成的任务，还会有 `claims.json` 和 `handoff.md`：

- `claims.json` 管"源文档承诺有没有被覆盖"。
- `review.md` 管"审查过程和证据够不够"。
- `handoff.md` 管"人回来之后能不能看懂这轮到底干了什么"。

就像这样：

![image-20260525100029471](C:\Users\Flow_Water\AppData\Roaming\Typora\typora-user-images\image-20260525100029471.png)

| 状态字段                  | 含义                                | 枚举值                     |
| ------------------------- | ----------------------------------- | -------------------------- |
| `dev_state`               | 开发状态                            | 未开始 -> 进行中 -> 已完成 |
| `review_initial_state`    | 初始审查（这条 issue 本身写对了吗） | 未开始 -> 进行中 -> 已完成 |
| `review_regression_state` | 回归审查（有没有搞坏别的东西）      | 未开始 -> 进行中 -> 已完成 |
| `git_state`               | 提交状态                            | 未提交 -> 已提交           |

只有四个状态全部到位，这条 issue 才算关闭。这就是为什么"少返工"——不是靠 review issue 一条命令解决的，而是每一条 issue 都自带了"写完 -> 自查 -> 回归 -> 提交"的完整闭环。Codex 不能跳过任何一步就声称完成。

加上 CSV 末尾的 REVIEW 行（整体验收），就形成了"微观闭环 + 宏观验收"的双保险。新版本又多了一层 claim ledger，对照的是 spec 里的原始承诺，不是 agent 跑完后自己总结出来的漂亮话。

---

## 9. CSV 核心字段一览

完整的 CSV 有 19 个字段，固定表头只由 `mission-csv-execute/csv-schema.md` 定义。`mission-approved-doc/doc-field-mapping.md` 只是把 spec 映射到这 19 列，不是另一套 schema。

这里列出最关键的几个，帮助你理解执行过程：

```
id, priority, phase, area, title, description, acceptance_criteria, test_mcp,
required_skills, required_mcp, review_initial_requirements, review_regression_requirements,
dev_state, review_initial_state, review_regression_state, git_state, owner, refs, notes
```

重点字段说明：

- **acceptance_criteria**：验收标准，必须是机器可验证的（比如"运行 xxx 测试通过"），不能是模糊的"看起来对了"
- **refs**：相关文件引用，至少包含一个 `path:line` 格式的定位，让 Codex 知道从哪里开始
- **required_skills**：执行这条 issue 需要触发哪些 skill（比如前端任务填 `ui-ux-pro-max`）
- **required_mcp**：验收时需要调用哪些 MCP 工具（前端必须有 `chrome-devtools`）
- **notes**：执行过程中的标签记录，比如 `blocked:<原因>`、`evidence:<证据>`、`risk:<等级>`
- **claim_ledger / claims**：从 approved doc 抽出来的承诺账本和当前 issue 覆盖的 claim id
- **review_agent_mode / review_independence**：本轮 REVIEW 实际用了哪种独立审查能力，独立性强不强
- **review_result / review_actual_model**：REVIEW 执行后回填的结论和实际模型；生成 CSV 时通常还是空或 pending
- **handoff**：给人看的交工单路径，通常是 `<csv>.handoff.md`

---

## 10. 测试字段设计 —— test_mcp + required_mcp 分离

这是我觉得这套 CSV 设计中最巧妙的一点：**test_mcp 和 required_mcp 是分开的**。

**test_mcp** 描述的是"主要验证模式"，告诉 Codex 这条 issue 的验证思路是什么：

| test_mcp 值    | 含义                       | 典型场景           |
| -------------- | -------------------------- | ------------------ |
| `AUTOSERVER`   | 后端单元测试 / API 验证    | 接口开发、业务逻辑 |
| `AUTOFRONTEND` | 前端视觉 / 布局 / 状态验证 | UI 组件、样式调整  |
| `AUTOE2E`      | 多步骤用户旅程             | 注册流程、购买流程 |
| `CONTRACT`     | Schema / API 契约验证      | 接口对接、类型定义 |
| `MIGRATION`    | 数据迁移验证               | 数据库变更         |
| `MANUAL`       | 非自动化的人工验收         | 需要人眼判断的场景 |

**required_mcp** 描述的是"实际要调用的工具"，因为我发现有时候不指定mcp，他可能就不会去调用，而是倾向于直接从代码开始测试：

| 场景              | required_mcp                  |
| ----------------- | ----------------------------- |
| 纯后端 / 基础设施 | 留空                          |
| 有可见 UI         | `chrome-devtools`（最低要求） |
| 多步交互          | `chrome-devtools;playwright`  |
| 强视觉 / 动画     | `chrome-devtools;screenpipe`  |



这样设计的好处是：Codex 既知道验证的"策略"（test_mcp），又知道验证的"手段"（required_mcp），不会出现"跑了个 smoke test 就说通过了"的情况。

---

## 11. 流程总结

```
你的需求
  │
  ├─ 复杂/模糊 → Claude brainstorming → spec 文档 → $mission 给spec.md生成csv
  │                                                      ↓
  │                                              mission-approved-doc
  │                                                      ↓
  │                                              issues/*.csv（提交到仓库）
  │                                                      ↓
  |												/goal @*.csv
  |
  ├─ 清晰/直接 → $mission "任务描述" ──→ mission-long-task
  │                                              ↓
  │                                      .mission/*.csv（本地恢复用）
  │                                              ↓
  |										 /goal @*.csv
  |
  ├─ 已有 CSV → /goal @xxx.csv ───────────────────┐
  │                                                ↓
  │                                        mission-csv-execute
  │                                        （四状态闭环执行引擎）
  │                                                ↓
  │                                        每条 issue 循环：
  │                                        开发 → 初始审查 → 回归审查 → 提交
  │                                                ↓
  │                                        REVIEW 行：整体验收 + 交工单
  │                                                ↓
  │                                        review.md / handoff.md / claims.json
  │                                                ↓
  │                                        全部关闭 = 任务完成
  │
  └─ 中断恢复 ┬─ codex resume（会话级，/goal 自动继续；前提是开头发过 hello 占位）
              └─ $mission continue ──→ mission-recovery（CSV 状态级，从断点继续）
```

享受这套新流程，感受生产力的提升！（maybe）
