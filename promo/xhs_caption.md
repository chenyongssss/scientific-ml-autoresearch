# 小红书文案（中文版）

## 版本一：偏项目发布
最近把一个自己很想用、也希望 scientific ML 社区能用上的小项目开源了：

**scientific-ml-autoresearch**

它不是“自动科学家”，也不是那种很重的 agent 平台。
我想做的其实更克制：

把 scientific ML 里最常见的研究闭环整理成一个轻量 workflow：

- plan 下一轮实验
- run 实验
- summarize 结果
- suggest 下一步
- repeat

这个项目目前已经支持：
- history-aware 的 round planning
- exploit / explore / ablate / validate / stop 这几类动作
- summary / suggestion / status 等研究过程输出
- constraints / robustness hooks / evaluation regimes
- claim strength 与跨轮 evidence tracking

我比较在意的一点是：
它不只是帮你“跑实验”，而是尽量避免把局部结果过早包装成结论。
所以现在它会显式区分：
- observed
- needs-validation
- supported
- uncertain

并且开始记录 claim trajectory 和 branch evidence。

现在还是一个持续迭代中的早期版本，但已经能跑通完整 workflow，也已经开源在 GitHub 上了。

如果你也在做：
- scientific machine learning
- PDE learning
- operator learning
- inverse problems
- physics/structure-aware ML

欢迎看看，也欢迎提 issue / 一起改。

GitHub：
https://github.com/chenyongssss/scientific-ml-autoresearch

---

## 版本二：偏思路分享
我一直觉得，scientific ML 里最耗时间的，不只是训练本身。
很多时间其实花在这些循环里：

- 改一点配置
- 补一个 ablation
- 再跑一组 baseline
- 汇总结果
- 想下一轮做什么
- 然后重复

所以最近我开源了一个轻量项目：
**scientific-ml-autoresearch**

目标不是做“AI 自动科研”的大叙事，
而是先把这条真实存在的 research loop 组织清楚。

目前这个项目会把 workflow 拆成：
- plan
- run
- summarize
- suggest
- loop

并且开始显式管理：
- exploit / explore / ablate / validate / stop
- constraints
- robustness checks
- claim strength
- historical evidence

我希望它更像一个：
**面向 scientific ML 的、克制但有研究意识的 workflow assistant**。

如果你对这类方向感兴趣，欢迎交流。

GitHub：
https://github.com/chenyongssss/scientific-ml-autoresearch

---

## 可配的标题候选
- 我做了一个面向 scientific ML 的 autonomous research workflow 开源工具
- 把 scientific ML 的实验闭环做成了一个轻量开源项目
- 不是自动科学家，而是一个更克制的 scientific ML research workflow
- 我开源了一个会做 plan / run / summarize / suggest 的 scientific ML 工具
- 给 scientific ML 社区做了一个轻量 research workflow 项目

---

## 推荐标签
#ScientificMachineLearning
#AI4Science
#科研工具
#开源项目
#GitHub
#机器学习
#深度学习
#PDE
#科研日常
#科研效率
