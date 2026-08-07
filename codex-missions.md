# 用 Missions 跑一条可恢复、可审计的长任务

Missions 解决的不是“怎么让 agent 一直输出”，而是长任务中更实际的三个问题：需求有没有经过批准、执行状态能不能在中断后恢复、最终结论有没有足够证据。

## 先理解五个角色

`mission` 只是路由器。它根据输入，把工作交给四个职责单一的子 skill：

```text
mission
├── mission-spec          讨论需求、写 draft、取得批准
├── mission-approved-doc  approved spec -> issues/<stem>/
├── mission-csv-execute   执行 CSV 并维护证据与提交状态
└── mission-recovery      从 issues/ 找到未完成 CSV
```

入口不讨论方案，也不执行 issue。这样做是为了让每个状态变化只有一个负责人。

## 安装前先准备依赖

运行脚本需要 Python 3.11 或更高版本：

```bash
python --version
```

`humanizer-zh` 是必装依赖。它只处理 spec 等自然语言正文，不碰 frontmatter 和机器字段：

```bash
npx skills add https://github.com/op7418/Humanizer-zh.git
```

`lite-arch` 建议安装。装了以后，涉及通信、存储、鉴权、分层等架构权衡时会先召回旧 ADR，并在 spec 获批后判断是否记录新 ADR；没装不会阻断 mission：

```text
https://github.com/flowing-water1/lite-arch
```

具体复制命令和 Codex reviewer 注册方式见 [README](./README.md)。

## 第一步：从需求生成 draft

把自然语言需求交给 `mission`：

```text
mission 给后台增加批量导入，支持 CSV 校验、错误行下载和失败重试
```

入口会路由到 `mission-spec`。它先读相关仓库上下文，只在仍有会改变方案的问题时追问，而且一次只问一个。方案确定后，会写入：

```text
docs/specs/<YYYY-MM-DD>-<topic>.md
```

spec 至少回答四件事：

- Goal：最终要得到什么。
- Scope：这次做哪些内容，边界到哪里。
- Design：关键行为和约束是什么。
- Acceptance Criteria：怎样证明完成。

draft 不允许直接进入实现。你必须看到完整内容，并明确批准那一版。

## 第二步：批准必须可验证

批准后，skill 会把 frontmatter 改成：

```yaml
---
mission: spec
status: approved
created: 2026-08-07
approved_at: 2026-08-07T15:30:00+08:00
---
```

随后提交 spec，再运行校验器证明两个事实：

1. approved spec 已存在于 `HEAD`。
2. 工作副本和已批准内容完全一致。

正文只要再改一个字，原批准就失效，必须退回 draft。这道门防止 agent 拿“你批准过旧版本”当作实现新内容的授权。

## 第三步：从 spec 生成执行工件

`mission-approved-doc` 会先抽取三张账本，再生成 CSV：

```text
issues/<stem>/
├── <stem>.csv
├── <stem>.claims.json
├── <stem>.outcomes.json
└── <stem>.deferred.json
```

三张账本分别回答：

- claims：spec 的每条可验证承诺由哪个 issue 覆盖，需要什么等级的证据。
- outcomes：最终读者要回答哪些问题，什么结果决定成败，当前不能声称什么。
- deferred：哪些发现属于未来改进，不应该偷偷扩进本轮范围。

组件实现和生产接线会拆开。比如“实现 worker”和“把 worker 注册进启动流程”通常是两条 issue，避免模块写完却没人调用。

## 第四步：执行 CSV

可以直接输入生成的 CSV，也可以把 artifact 目录交给入口：

```text
mission @issues/<stem>/<stem>.csv
```

执行器逐行维护四个状态：

```text
dev_state
review_initial_state
review_regression_state
git_state
```

四个状态全部到终态后，一条普通 issue 才关闭。实现完成不等于验证完成，验证完成也不等于提交完成。

`test_mcp` 表示验证策略，`required_mcp` 表示必须实际调用的工具。两者分开，是为了防止“写了 E2E 目标，最后只跑一个静态 smoke test”这种证据降级。

## 第五步：REVIEW-N 对照最初目标

CSV 末尾固定有 `REVIEW-01`。它不是普通代码审查，而是拿下面这些材料做整体验收：

- approved spec
- CSV 与四状态
- claims / outcomes / deferred
- 实际 diff 和提交
- 测试与外部验证证据
- 之前的 review log

review 优先使用注册的只读 reviewer，其次使用只读 ephemeral `codex exec`，最后才是 self-review。使用哪条路径、请求了什么模型、实际观察到什么模型、证据来自哪里，都分开记录。

finding 分三类：

- 当前范围缺口：追加 follow-up issue 和下一条 `REVIEW-N`，继续执行。
- deferred improvement：写进 deferred ledger，不扩大本轮范围。
- human-required blocker：确实需要用户权限、凭证、审批或业务决定时才暂停。

## 第六步：看 handoff，不要只看日志

任务关闭前会生成：

```text
<stem>.review.md
<stem>.handoff.md
reviews/
```

`review.md` 是审计日志，`handoff.md` 是给人的交工单。回到电脑后优先看 handoff，它会说明：

- 做了什么。
- 哪些目标有证据支持。
- 哪些验证受限。
- 还有什么风险。
- 怎样复现或检查结果。

handoff 还要通过机械 contract check。文件名、CSV notes 引用和 Markdown 骨架不一致时，不能把 review 写成完成。

## 中断后怎么恢复

在新会话里输入：

```text
mission continue
```

恢复器只扫描 `issues/*/*.csv` 和兼容的 `issues/*.csv`，按最近修改时间定位未完成任务，再交回执行器。它不会扫描整个磁盘，也不会自动接管任意外部 CSV。

如果同时有多个未完成任务，恢复器会列出来让你选择。这是必要的边界，不应为了“全自动”擅自并行修改多个工作树。

## 哪些任务不该用 mission

目标、范围和验收已经清楚的普通任务，直接实现往往更合适。mission 适合这些场景：

- 需求还需要讨论和明确批准。
- 工期长，可能跨会话或中断。
- 有多条承诺，需要逐项对账。
- 需要独立 review 和正式 handoff。

把每个小改动都塞进 mission，只会增加工件成本，并不会让结果更可靠。
