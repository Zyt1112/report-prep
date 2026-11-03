# 变更记录

两级版本号：新增能力或改规则升次版本，纯文档修正也记在这里。

## 1.7 — 2026-11-03

**新增 `build_deck.py`：提纲 JSON → `.slide`**

- 读结构化 deck content JSON，按页型（P1 封面 / P2 卡片 / P3 双栏 / P4 表格 / P5 步骤 / P6 边界）统一生成母版带与页面骨架，输出 `.slide` DSL 文件。
- 证据令牌 `{{E001}}` 在生成时解析为台账 `display`；不替 agent 猜图、不编造数据——图、表、卡片内容都来自输入 JSON。
- 输入格式以 `examples/deck.content.json` 为样例（含全部六种页型），`build_deck.py --help` 可查全部选项。
- 测试 34 → 40 项（六种页型 + CLI 参数 + 令牌解析 + 错误分支）。

**论文内容治理（用户工作区，不在本仓库）**

- 四篇 evidence/outline 的 17 条裸数字清零：已有证据的改用 `{{E0xx}}` 令牌；缺失的试验条件（应变幅档位、烘烤温度、喷丸距离公差等）补建证据项。
- `--source` 严格模式四篇全过：裸数字 0、quote 全部命中原文。
- 受影响的交付 HTML 已重渲染并同步桌面副本。

## 1.6 — 2026-11-03

**HTML 校验不再误报**

- `check_html.py` 支持 HTML5 可省略结束标签：`<p>a<p>b`、`<ul><li>a<li>b</ul>`、表格单元格等，由父元素或下一个同类元素隐式关闭，不再判为 ERROR（依据 HTML Living Standard 13.1.2.4 Optional tags）。
- 保留对真正错误的判定：`<div><span>x</div>` 这类跨父级闭合仍报错。
- 测试 29 → 34 项。

**工程加固**

- 新增 `.github/workflows/test.yml`：push / PR 时跑单元测试、`doctor.py`、模板校验、示例链路（数字检查 → 渲染 → HTML 校验）。
- `doctor.py` 新增版本号一致性检查：`SKILL.md`、`CHANGELOG.md`、`README.md` 三处必须相同。
- `CHANGELOG.md` 纳入必需文件清单（22 → 23）。

## 1.5 — 2026-11-03

**数字检查补漏（`scripts/check_numbers.py`）**

- 新增 `qualitative: true`：机制类定性论断可进台账，`value` 设 `null`，跳过数值等价校验，但仍校验 `source`/`locator`/`quote`/`status`/`kind`。
- 新增**裸数字扫描**：正文里带单位的数字一律提示；纯数字字段只在恰好等于某条证据值时提示“应改用令牌”。默认 WARN。
- 新增 `--source`：核对每条 `quote` 是否真出现在给定的原文文本里；`status: derived` 跳过（它的 quote 是推导依据，不是原句）。
- 新增 `--strict`（裸数字与 quote 缺失升级为 ERROR）、`--no-bare`（关闭扫描）。
- 归一化增强：`◦`/`˚`/`º` → `°`、`μ`/`µ` 统一、剥离 Markdown `###` 与转义符、弯引号归一——这些是 PDF 提取的常见噪声，不处理会造成大量假未命中。
- 测试 21 → 29 项。

**规则一致性**

- `deck-style.md` 的 P2 骨架删去页脚承接句，与“承接句只进提纲”一致。
- `ppt-build.md` 页面结构示意图改为「底带：术语/来源，页脚：页码」。

**工程**

- 版本记录移出 `SKILL.md`，由本文件承接；`SKILL.md` 每次加载少约 1.2 KB。

## 1.4 — 2026-11-03

- 版式定稿：页数不设上限、图按内容加不按页凑、边界与迁移页可选、承接句移入提纲、表格强调改红字短下划线。
- 新增 `scripts/doctor.py`（9 项环境自检）、`scripts/setup_env.ps1`（Windows slidep 原生模块修复）、`references/environment.md`。
- 收录 `examples/deck-v3-4340m/`：6 页标准样张 + pptx + `.slide` 源码。
- `README.md` 与 `HANDOVER.md` 重写为可交接文档。

## 1.3 — 2026-11-03

- 新增 `references/deck-style.md`：章节式版式规范、版面栅格、P1–P6 页型、“提纲到页面”映射。
- 标题三方案并存（章节式 / 问句式 / 双层默认）。
- 术语首现注解规则；提纲阶段需标注页型。
- 机构母版：太原科技大学色值 `#0024B3`、校徽 `assets/tyust-logo.png`、三带规格。

## 1.2 — 2026-11-02

- 四类任务入口（读懂 / 准备 / 修复 / 完整交付），不再强制全流程。
- 证据台账 + `{{E001}}` 令牌，来源数字单一来源。
- `scripts/render_html.py`：内容 JSON → HTML；`scripts/check_html.py` 改 `HTMLParser` 结构化校验。
- 新增逐页详解与模拟追问模板、器件/方法设计类骨架、阶段资源路由。
- 统一结论先行、页数、多篇模式规则。
- 21 项单元测试。

## 1.1 — 2026-11-02

- 按实验 / 建模 / 仿真三类论文拆分 PPT 骨架。
- 新增页面制作规范（`references/ppt-build.md`）。

## 1.0 — 2026-11-02

- 首版：结构诊断、讲解稿、讲述提纲、PPT 结构流程。
