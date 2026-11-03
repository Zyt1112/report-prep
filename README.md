# report-prep

> 把一篇论文，变成一套**能讲、能问、能回溯**的汇报材料。

输入一篇 PDF（或几篇），输出按需：**讲解稿 → 讲述提纲 → 结构提纲 → PPT → 逐页详解与模拟追问**。也可以只做其中任意一件。

面向工科（实验 / 建模 / 仿真 / 器件方法）的组会、文献精读、开题与答辩预演。

---

## 它治三种病

| 病 | 表现 | 做法 |
|---|---|---|
| **名词标题病** | 每页写着“研究背景 / 实验方法 / 结果”，页与页之间没有因果 | 章节名 + 页内问句双层标题，每页一句核心结论 |
| **结论后置病** | 讲完背景听众仍不知道你要证明什么 | 第一张内容页给全篇判断和成立前提，再展开证据 |
| **数据无归属病** | 数字和结论回不到原文位置，改稿时到处漂移 | 证据台账 + `{{E001}}` 令牌，数字只有一个来源 |

核心主张：**讲解稿写给要上台的人，PPT 写给他对面的听众**。两者不是同一份东西的两种长度。

---

## 五步流程

| 步 | 产出 | 通过条件 |
|---|---|---|
| 0 | 任务卡 + 材料完备度 | 默认假设、缺失证据已标明 |
| 1 | **讲解稿** | 能解释“为什么这样做”，不是复述步骤 |
| 2 | **讲述提纲** | 拍数适配时长；附“章节 → 拍”的压缩关系 |
| 3 | **结构提纲** | 每页有标题、核心结论、证据 ID、视觉锚点、承接句、页型 |
| 4 | **PPT** | 提纲已确认；页序、版式、页码与提纲一致 |
| 5 | **逐页详解 + 模拟追问** | 与 PPT 同批交付；答案区分原文依据与推断 |

## 四种入口（不必每次跑全套）

| 你要什么 | 走到哪一步 | 拿到什么 |
|---|---|---|
| 读懂论文 | 0 → 1 | 讲解稿、自测问题、证据缺口 |
| 准备汇报 | 0 → 1 → 2 → 3 | 讲解稿、讲述提纲、结构提纲 |
| 修现有材料 | 0 → 3 | 标题、页序、结论、证据、承接的诊断 |
| 完整交付 | 0 → 1 → 2 → 3 → 4 → 5 | 上面全部 + PPT + 逐页详解 |

---

## 版式（v1.4 定稿）

**三带母版**，全篇不变，内容不侵入上下带：

```
┌────────────────────────────────────────────┐
│ [校徽]                            3 / 6    │  顶带 56px  深蓝 #0024B3
├────────────────────────────────────────────┤
│ 章节名 22px                                │
│ 核心结论句 19px                            │  内容带 56–658
│ [ 表 / 图 / 要点 ]                          │
├────────────────────────────────────────────┤
│ 术语·口径                  表 2  数据：Fig.5 │  底带 62px
└────────────────────────────────────────────┘
```

四条硬规矩：

1. **页数不设上限**。一页一个问题，问题多就加页；不把两问压一页，不为省页删证据或缩图。
2. **图按内容加，不按页数摊**。有数据就排表、有结构就画示意；没有就纯文字，不必每页配图。
3. **一页只标一处**。表格里用红字 + 2px 短下划线压住关键数字（不套长框），结构图用红框或红色左边条。
4. **术语首现即注解**。缩写第一次出现时在底带给中文全称，正文不塞定义。

多篇材料各做一套：共用母版与页型，但各自独立叙事，不强行建立篇间因果，也不写“与本人研究方向的关系”，除非用户明确要求。

完整规范见 [`references/deck-style.md`](references/deck-style.md)，可运行样张见 [`examples/deck-v3-4340m/`](examples/deck-v3-4340m/)。

---

## 目录

```
report-prep/
├── SKILL.md                    主入口：任务入口、流程门禁、资源路由、自检
├── references/
│   ├── pipeline.md             执行流程与工具适配
│   ├── structure.md            讲述结构、时长与听众、多篇模式
│   ├── deck-skeletons.md       四类论文的页级骨架
│   ├── deck-style.md           版式规范（母版带、页型、标注、机构母版）
│   ├── ppt-build.md            图表—结论绑定、逐页闭环
│   ├── register.md             语体与证据语气分级
│   ├── evidence.md             证据台账字段与用法
│   ├── page-notes.md           逐页详解与模拟追问模板
│   └── environment.md          依赖清单、换机器、常见报错
├── assets/
│   ├── explainer.html          讲解稿渲染模板
│   ├── outline.html            提纲渲染模板
│   ├── content.schema.json     内容 JSON 的 Schema
│   └── tyust-logo.png          机构校徽（白色透明版）
├── examples/
│   ├── deck-v3-4340m/          6 页标准样张（含 pptx 与 .slide 源码）
│   └── *.json / *.html         证据与内容示例
├── scripts/
│   ├── check_numbers.py        证据引用与显示值一致性
│   ├── render_html.py          内容 JSON → HTML
│   ├── check_html.py           HTML 结构与打印样式校验
│   ├── doctor.py               环境自检
│   └── setup_env.ps1           Windows 环境修复（slidep 原生模块）
└── tests/test_scripts.py       21 项单元测试
```

---

## 安装

```bash
git clone https://github.com/Zyt1112/report-prep.git ~/.workbuddy/skills/report-prep
cd ~/.workbuddy/skills/report-prep
python scripts/doctor.py --fix-hint
python -m unittest discover -s tests -v
```

`doctor.py` 会检查 Python 版本、22 个必需文件、脚本语法、目录可写、校徽、`slidep`、PDF 取文、中文字体、SWC 缓存权限。FAIL 必须清掉，WARN 只影响 PPT/PDF 环节。

## 换一台电脑

1. `git clone` 到用户级 Skill 目录（见上）。
2. `python scripts/doctor.py --fix-hint`。
3. Windows 上 `slidep` 报 `Failed to load native binding` → `scripts/setup_env.ps1 -UseVirtualDrive -Persist`。
4. 用 `examples/deck-v3-4340m/` 生成一遍，确认能出 6 页、校徽在、中文不是方框。
5. 把待读论文放进工作区，先建 `evidence.json`，再写内容 JSON。

细节与报错对照见 [`references/environment.md`](references/environment.md)。

## 可复现渲染

```bash
python scripts/check_numbers.py evidence.json content.json
python scripts/render_html.py content.json --evidence evidence.json -o deliverable.html
python scripts/check_html.py deliverable.html
python scripts/check_html.py assets/*.html --allow-placeholders
```

`check_numbers.py` 只验证“引用存在、状态合法、显示值与台账一致”，**不能替代回原文核对**。

---

## 不做什么

- 不在结构确认前生成 PPT。
- 不把推荐页数、拍数当硬指标。
- 不用比喻替代机制，不用无来源数字填空。
- 不把自动一致性检查说成“已证明与原文一致”。
- 不为版面好看伪造定量曲线或隐藏不利结果。

## 版本

- **1.4**（2026-11-03）定稿版式：页数不设上限、图按内容加、边界页可选、承接句入提纲、表格强调改短下划线；新增 `doctor.py` / `setup_env.ps1` / `environment.md`；收录 6 页样张。
- **1.3** `deck-style.md`：章节式版式、版面栅格、P1–P6 页型、术语注解。
- **1.2** 四类任务入口、证据台账与 `{{E001}}`、JSON→HTML 渲染、逐页详解、结构化 HTML 校验、21 项单测。
- **1.1** 实验/建模/仿真三类骨架。
- **1.0** 首版。

## 许可

MIT，见 [LICENSE](LICENSE)。
