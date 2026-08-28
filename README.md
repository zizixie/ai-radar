# AI Radar · 个人 AI 情报雷达

> 不必每天打开一堆网站找 AI 新闻。

这是一个“个人 AI 情报雷达”：它会自动收集和整理 AI 行业的重要信息，把官方动态、新产品、热门开源项目和社区讨论放到一页里，方便你每天快速浏览。

🌐 **在线体验：** [https://zizixie.github.io/ai-radar/](https://zizixie.github.io/ai-radar/)

<!-- 网页预览图占位：将截图保存为 assets/preview.png 后，可取消下一行注释。 -->
<!-- ![AI Radar 网页预览](assets/preview.png) -->

## 30 秒开始使用

- **只想看** → 打开仓库 Pages 中显示的在线体验地址
- **想拥有自己的** → Fork → Pages → Actions
- **不会代码** → 直接让 AI / Codex 帮你修改

## 它能帮你做什么？

- 查看 OpenAI、Anthropic、Google DeepMind 的最新官方动态
- 发现 Product Hunt 上刚出现的新产品
- 查看 GitHub Trending 里的热门项目，以及当天新增 Stars
- 了解 Hacker News 上值得关注的 AI、LLM、Agent 与 AI Coding 讨论
- 集中浏览多个来源，不必在不同网站之间来回切换

## 目前的信息来源

| 来源 | 你能看到什么 |
| --- | --- |
| GitHub Trending | 当天热门开源项目、编程语言和新增 Stars |
| Product Hunt | 最新发布的产品 |
| OpenAI | OpenAI 官方新闻与产品更新 |
| Anthropic | Anthropic 官方 Newsroom 动态 |
| Google DeepMind | Google DeepMind 的研究、模型与产品动态 |
| Hacker News | 经过 AI / LLM / Agent / AI Coding 等关键词筛选的热门讨论 |

每个来源最多保留 20 条。某个来源临时无法访问时，其他来源仍会继续更新，已有内容也会保留。

## 如何使用

### A. 我只想看情报

直接打开在线网页即可：

👉 [打开 AI Radar 在线网页](https://zizixie.github.io/ai-radar/)

建议把它加入浏览器书签，每天花几分钟扫一眼。

页面顶部可以按“官方更新”“新工具”“GitHub”“讨论热点”快速筛选；“今日值得看”默认展示过去 24 小时内最新的 8 条内容。

### B. 我想搭建自己的 AI Radar

即使不会写代码，也可以照着做：

1. 在 [ai-radar 仓库](https://github.com/zizixie/ai-radar) 页面右上角点击 **Fork**，创建一份属于你的副本。
2. 进入你自己的仓库，点击 **Settings** → **Pages**。
3. 在 **Source** 选择 Deploy from a branch，分支选 main，文件夹选 /(root)，点击 **Save**。
4. 点击仓库顶部的 **Actions**。如果看到“Enable workflows”，点击它启用自动任务。
5. 运行一次“更新 AI 情报”（方法见下一节）。
6. 等待几分钟后，在 Pages 页面看到你的专属网址；打开它就是你的 AI Radar。

## 手动更新情报

想马上获取一次最新内容时：

1. 打开自己的 GitHub 仓库。
2. 点击顶部 **Actions**。
3. 在左侧选择 **更新 AI 情报**。
4. 点击右侧 **Run workflow**。
5. 再点击弹窗里的 **Run workflow**。
6. 等待出现绿色 ✅ 成功标志。

成功后，data/news.json 会自动更新；GitHub Pages 通常会在几分钟内同步网页。

## 自动更新

项目已经设置为**每天北京时间 08:15**自动运行一次。

它会抓取公开信息、更新数据；如果内容有变化，就自动保存到仓库。你平时只需打开网页查看即可。

## 如何改成自己的

不需要先学会编程。把下面的需求直接告诉 AI / Codex，也可以请懂代码的朋友帮忙：

| 想改什么 | 主要修改哪里 |
| --- | --- |
| 增加或删除新闻来源 | scripts/fetch_news.py |
| 改自动更新时间 | .github/workflows/update.yml |
| 改网页排版、颜色、栏目 | index.html |
| 改 Hacker News 的 AI 相关筛选规则 | scripts/fetch_news.py 里的关键词规则 |

例如，你可以说：“请为 AI Radar 增加一个我常看的公开 RSS 来源”，或“把每日更新时间改成晚上 8 点”。

## 让 AI 帮你改成自己的

可以直接复制这段话给 Codex：

> 请基于这个 AI Radar 项目，保留现有功能和简洁风格，只帮我完成：[写下你想改的内容]。请先检查相关文件，再修改并告诉我如何发布。

## 反馈与建议

发现问题，或有新的公开信息源建议？欢迎通过 GitHub **Issues** 提交。

## 项目目录，一句话看懂

```
index.html              网页长什么样、怎么展示资讯
data/                   已整理好的资讯数据
scripts/                自动抓取和整理资讯的小工具
.github/workflows/      GitHub 每天自动运行的任务设置
requirements.txt        自动抓取时需要安装的小工具清单
```

## 它是怎么工作的？

```
公开信息源
    ↓
Python 自动抓取
    ↓
整理、过滤、去重
    ↓
生成 data/news.json
    ↓
网页读取数据
    ↓
GitHub Pages 展示
```

## 常见问题

### 为什么信息没有更新？

先到 **Actions** 看“更新 AI 情报”最近一次运行是否为绿色成功。公开网站偶尔会临时限制访问；项目会保留上一次成功抓到的数据，不会让整页变空。

### 怎么手动更新？

按上面的“手动更新情报”步骤，在 **Actions** 中运行“更新 AI 情报”即可。

### Actions 失败怎么办？

点开失败的任务查看红色提示。常见情况是某个公开来源暂时无法访问；稍后重新运行通常即可。若持续失败，可以把提示交给 AI / Codex 协助排查。

### 修改网页以后为什么没有马上变化？

修改要先保存并提交到 main 分支。GitHub Pages 需要一点发布时间，等待几分钟后刷新网页；必要时使用浏览器的强制刷新。

### 可以增加自己的信息源吗？

可以。只要来源是公开可访问的网页或 RSS，通常都能接入。主要修改 scripts/fetch_news.py，也可以直接请 AI / Codex 帮你完成。

## 免责声明

本项目只聚合公开信息。新闻、项目介绍和其他内容的版权归原始来源所有；请以原始链接中的信息为准。
