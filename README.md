# scientific-ml-autoresearch

## 中文说明

**scientific-ml-autoresearch** 是一个面向 scientific machine learning 的轻量级自动研究工作流。

它围绕研究中最常见的一条迭代链路组织起来：

- 规划实验分支
- 执行训练与评估
- 记录 scientific checks
- 汇总证据状态
- 生成下一轮建议

这个仓库的重点不是“大而全的 MLOps 平台”，也不是“全自动科学家”。
它提供的是一个**完整、可运行、证据感知型**的研究工作流，用较少的基础设施完成以下事情：

- branch-aware planning
- evidence bundle expansion
- constraints 与 robustness checks 的结构化记录
- branch evidence card 聚合
- claim taxonomy 与 evidence gaps
- persisted evidence state
- provenance 与 artifact validity
- resumable execution

### 当前工作流

核心循环由以下步骤组成：

1. `plan`：根据 task spec、history 和 evidence state 生成 round plan
2. `run`：执行 train / eval，并写入 metrics、checks、provenance
3. `summarize`：生成 round summary，展示 branch evidence 与科学检查结果
4. `suggest`：根据 claim taxonomy 与 evidence gaps 给出下一轮建议
5. `loop`：把整个 round-based workflow 串起来持续运行

### 核心设计

#### 1. 分支优先的计划方式
系统把一个 round 看成若干 **canonical branches** 的预算分配问题，而不是单纯的 config 列表扩展。

每个 branch 可以再扩展成多个 evidence members，例如：

- 不同 seed
- 不同 evaluation regime

这使得 workflow 可以同时表达：

- branch exploration breadth
- evidence validation depth

#### 2. 证据感知的研究判断
系统不会只记录“谁最好”，还会维护：

- branch evidence cards
- claim taxonomy
- evidence gaps
- partial bundle completion

它能够区分：

- observed
- promising
- validated
- unsupported

并把这些状态反馈到 planner 和 suggester 中。

#### 3. scientific checks 是一等对象
`constraints` 和 `robustness_checks` 不是备注，它们会进入：

- runner
- evidence state
- summary
- suggestion
- planning decisions

这让 scientific ML 中常见的验证逻辑，例如：

- conservation
- stability
- shifted-grid robustness
- noisy-observation robustness

能够成为真正可追踪的 workflow 对象。

#### 4. 可靠性层
仓库当前包含完整的 workflow reliability 基础：

- `provenance.json`
- artifact validity flags
- `round_XX_evidence_state.json`
- resume / rerun policy
- invalid artifact recovery

这意味着 workflow 不只是“会建议”，还能够在中断后继续运行，并对结果有效性做出明确判断。

### 主要文件与输出

典型运行目录会包含：

- `task.yaml`
- `round_XX_plan.yaml`
- `round_XX_evidence_state.json`
- `round_XX_summary.md`
- `round_XX_suggestions.md`
- `history.json`

每个 experiment 目录中通常包含：

- `config.yaml`
- `train.log`
- `eval.log`
- `metrics.json`
- `provenance.json`
- robustness artifacts

### 命令行入口

```bash
autoresearch init --example advection --output runs/advection_demo
autoresearch plan --task runs/advection_demo/task.yaml
autoresearch run --task runs/advection_demo/task.yaml
autoresearch summarize --run runs/advection_demo
autoresearch suggest --run runs/advection_demo
autoresearch loop --task runs/advection_demo/task.yaml --rounds 3
autoresearch status --run runs/advection_demo
```

### 文档与界面

- 任务格式：`docs/task-format.md`
- 扩展说明：`docs/extending.md`
- 静态工作流界面：`docs/workflow-ui/index.html`

静态界面使用纯 HTML / CSS / JS 编写，可以直接在浏览器中打开。

---

## English

**scientific-ml-autoresearch** is a lightweight auto-research workflow for scientific machine learning.

It organizes a familiar research loop into a coherent system:

- plan experiment branches
- execute training and evaluation
- record scientific checks
- aggregate evidence state
- generate the next round suggestion

This repository is not positioned as a full MLOps platform or an autonomous scientist.
It is a **complete, runnable, evidence-aware workflow** built to support scientific ML research with modest infrastructure and clear state transitions.

### What the workflow contains

The current system includes:

- branch-aware planning
- evidence bundle expansion
- structured constraints and robustness checks
- branch evidence cards
- claim taxonomy and evidence gaps
- persisted evidence state
- provenance and artifact validity
- resumable execution

### Current workflow loop

The main loop is organized as:

1. `plan`: generate a round plan from the task spec, history, and evidence state
2. `run`: execute train / eval commands and write metrics, checks, and provenance
3. `summarize`: produce a round summary centered on branch evidence and scientific checks
4. `suggest`: recommend the next action from claim taxonomy and evidence gaps
5. `loop`: connect the round-based workflow into a continuous research cycle

### Core design

#### 1. Branch-first planning
A round is treated as an allocation problem over **canonical branches**, not only as a flat list of configurations.

Each branch can expand into multiple evidence members, such as:

- different seeds
- different evaluation regimes

This gives the workflow an explicit way to represent both:

- exploration breadth
- validation depth

#### 2. Evidence-aware research judgment
The system tracks more than a single best run. It maintains:

- branch evidence cards
- claim taxonomy
- evidence gaps
- partial bundle completion

It distinguishes among:

- observed
- promising
- validated
- unsupported

These states feed back into planning and suggestion generation.

#### 3. Scientific checks as first-class workflow objects
`constraints` and `robustness_checks` are part of execution and reporting rather than being left as narrative comments.

They are consumed by:

- the runner
- evidence state generation
- summaries
- suggestions
- planning decisions

This makes common scientific ML validation concepts such as:

- conservation
- stability
- shifted-grid robustness
- noisy-observation robustness

part of the workflow itself.

#### 4. Reliability layer
The repository includes a workflow reliability layer with:

- `provenance.json`
- artifact validity flags
- `round_XX_evidence_state.json`
- resume / rerun policy
- invalid artifact recovery

The workflow therefore does more than recommend actions. It can resume interrupted work and make explicit judgments about artifact validity.

### Main files and outputs

A typical run directory contains:

- `task.yaml`
- `round_XX_plan.yaml`
- `round_XX_evidence_state.json`
- `round_XX_summary.md`
- `round_XX_suggestions.md`
- `history.json`

Each experiment directory commonly contains:

- `config.yaml`
- `train.log`
- `eval.log`
- `metrics.json`
- `provenance.json`
- robustness artifacts

### CLI entry points

```bash
autoresearch init --example advection --output runs/advection_demo
autoresearch plan --task runs/advection_demo/task.yaml
autoresearch run --task runs/advection_demo/task.yaml
autoresearch summarize --run runs/advection_demo
autoresearch suggest --run runs/advection_demo
autoresearch loop --task runs/advection_demo/task.yaml --rounds 3
autoresearch status --run runs/advection_demo
```

### Documentation and UI

- Task format: `docs/task-format.md`
- Extension notes: `docs/extending.md`
- Static workflow UI: `docs/workflow-ui/index.html`

The UI is written in plain HTML / CSS / JS and can be opened directly in a browser.

---

## License

MIT
