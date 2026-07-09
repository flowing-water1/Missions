---
name: mission
description: Use when a task may be a user-approved design/plan document, an existing task CSV, a markdown execution or investigation document, a long-running task description, or a recovery request and needs routing to the right mission sub-skill.
---

# Mission

统一任务入口。判断输入类型，委托给对应的子 skill。

**宣告：** "使用 mission skill，路由到 <子 skill 名称> 模式。"

## 路由规则

若当前会话里已经存在**未终态**的 mission 执行流，优先继续该执行流；不要因为用户发来解释性、进度性、原因性消息就重新路由。

按以下顺序检查，**第一个匹配的规则胜出**。

### 1. 现有 CSV 文件

```
输入匹配: *.csv 或包含路径分隔符
且路径在磁盘上存在
若路径是文件：该文件有合法 CSV 表头
若路径是目录：优先解析 `<dir>/<dir-name>.csv`；若不存在但目录内只有一个 CSV，则使用该 CSV；若多个 CSV 则询问用户
→ 委托给 mission-csv-execute
```

### 2. Markdown 文档

```
输入匹配: *.md（不是 *.csv）
且文件在磁盘上存在
→ 委托给 mission-doc-route
```

### 3. 恢复请求

```
输入为空，或用户说 "continue" / "resume" / "继续" / "接着做"
→ 委托给 mission-recovery
```

### 4. 复杂任务描述

```
输入是自然语言描述
且预估工作量 > 1 小时或步骤 ≥ 3
→ 委托给 mission-long-task
```

### 5. Fallback

```
预估工作量 < 1 小时且步骤 < 3
→ 不使用 mission。直接执行 + update_plan。
```

## 歧义处理

- 输入像 CSV 路径但文件不存在 → 询问用户
- 输入像文档路径但文件不存在 → 询问用户
- 不确定走 long-task 还是直接执行 → 默认直接执行（更轻量）

## 子 Skill 注册表

| 子 Skill | 职责 | 输入 |
|----------|------|------|
| `mission-approved-doc` | 已批准设计/计划文档 → CSV → 闭环执行 | doc-path.md |
| `mission-csv-execute` | CSV 闭环执行器（强内核） | csv-path |
| `mission-long-task` | 长任务拆分 → CSV → 闭环执行 | 任务描述 |
| `mission-recovery` | 恢复中断的任务 | 无 |
| `mission-doc-route` | 文档 → 路由到 approved-doc 或 long-task | doc-path.md |

## 关键原则

- **mission 自己不执行任务**，只做路由
- **所有执行流最终汇聚到 `mission-csv-execute`**
- 路由判断要快，不要过度分析
- **一旦进入执行类子 skill，就默认持续推进**：不得因为 checkpoint、commentary、阶段总结或里程碑切换，把控制权提前交还给用户
- **执行态有粘性**：一旦已路由到 `mission-csv-execute` 或其他执行类子 skill，后续消息默认仍属于同一执行流；除非用户显式要求 `stop` / `pause` / `cancel`、明确变更任务边界，或满足正式停止条件，否则不得重新落回普通 Q&A / 分析路由
