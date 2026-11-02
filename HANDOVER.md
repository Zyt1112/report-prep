# report-prep v1.2 交接文档

面向接手维护者。讲清三件事：**为什么改、改成了什么、哪些还没验证**。

---

## 一、这次优化解决什么问题

### 1. 规则自相矛盾（P0）

v1.1 存在多组互相打架的要求，模型执行时只能随机选一边：

| 冲突 | 表现 |
|---|---|
| 结论先行 vs 第一页只给画面 | `SKILL.md` 要求第一页给判断，实验骨架第一页却要求"只给画面、不给数据"，核心结论拖到第 6 页 |
| 6–8 拍 vs 固定七拍 | 主流程说 6–8 拍，`assets/outline.html` 却写死七拍；骨架说"七页是下限"，示例又给六页方案 |
| 逐篇独立 vs 依赖链 | 一处要求多篇逐篇独立完成，另一处要求建立跨篇依赖链 |
| 通用定位 vs 材料学专用 | 描述写"论文或资料"，模板/示例却集中于材料疲劳、实验、建模、仿真 |

### 2. 数字没有单一来源（single source of truth）

同一个数字要在讲解稿、讲述提纲、PPT、逐页详解里各写一遍。靠提示词要求"回原文核对"无法验证，改稿时极易在不同产物间漂移。

### 3. 环境耦合与过度绝对

- 写死 `D:/WorkBuddy/...` 的 PDF 工具路径；
- 把 `slidep`、SWC 缓存目录及 ACL 处理写成通用流程；
- 要求"交付件一律放用户桌面"（强制写个人目录）；
- 大量绝对判断，如"跳过讲解稿**必然**做出并列式结构""二手转述**必错**"。

---

## 二、总体思路

**不推倒重做。** 保留 v1.0/1.1 的方法论内核：讲解稿写给汇报者本人（而非听众）、问句标题 + 页间承接、数据可追溯、不伪造定量曲线。

在此基础上做四件事：

1. **原则 → 可检查的产物。** 新增 `evidence.json` 证据台账 + 内容 JSON + `{{E001}}` 引用令牌：来源数字只在一处定义，渲染时注入，不再手工复制到多个文件。
2. **原则 → 流程。** 增加四种任务入口（读懂论文 / 准备汇报 / 修复现有材料 / 完整交付），不再要求所有请求都从长讲解稿开始。
3. **绝对规则 → 默认值 + 可覆盖。** 页数、拍数由时长和必要问题数决定，取消七页下限；领域不匹配时自定义问题链，不强套模板。
4. **环境特定 → 官方能力优先。** WorkBuddy 中统一走 `workbuddy-pdf` / `workbuddy-pptx` / `workbuddy-docx`；外部命令先确认可用；输出用指定目录或工作区。

---

## 三、两份外部意见的采纳情况

### Claude 清单（基于实际读文件，以采纳为主）

| 建议 | 处理 | 说明 |
|---|---|---|
| 修正结论先行与骨架第一页矛盾 | **采纳** | 改为"问句标题 + 核心结论句"，第一张内容页必须给核心判断与前提 |
| 补 `page-notes.md` 和模拟追问 | **采纳** | 新增文件：每页模板、追问分类、不得编造答案 |
| 新增 `check_numbers.py` | **采纳但降级定位** | 实现为"声明引用与显示值一致性检查"，**明确不能证明与 PDF 一致** |
| 写长稿前加确认点 | **采纳并合并门禁** | 完整模式先给 ≤6 行任务卡；避免"长稿确认 + PPT 确认"双重打断 |
| 时长与听众对照表 | **采纳** | 放入 `structure.md`，5/10/15/20/30 分钟建议拍数 |
| 新增器件/方法设计类骨架 | **采纳** | `deck-skeletons.md` 新增 D 类 |
| WorkBuddy 环境适配 | **采纳** | 移除硬编码路径、强制桌面输出、slidep 专属流程 |
| description 补边界 | **采纳** | 重写为"支持/不支持什么"，减少触发词堆叠 |
| 升级 `check_html.py` | **采纳** | 改为 `HTMLParser` 结构化校验，区分 error/warning |
| 保留 `agent_created: true` | **采纳** | 平台写入的标记，不删 |

### Gemini 建议（基于目录树推断，选择性吸收）

| 建议 | 处理 | 说明 |
|---|---|---|
| 按需加载 / 阶段锁 | **吸收但弱化** | 原已是渐进加载，未"必然 Token 爆炸"；改为阶段资源路由表，不设硬性阶段锁 |
| JSON + 脚本渲染 HTML | **采纳** | 实现 `render_html.py`；但**不承诺"提速 3 倍""错误率降为 0"** |
| 图表—结论绑定 Visual–Claim | **采纳并兼容化** | 保留问句标题 + 增加核心结论句；新增 `visual_anchor / callout / claim` |
| 前置信息盘点 | **不重复新增** | 原步骤 0 已有，仅补"材料完备度"和"重点倾向" |

---

## 四、文件变更清单

### 修改

| 文件 | 变化 |
|---|---|
| `SKILL.md` | 重写：四种任务入口、步骤 0 盘点、阶段资源路由、证据规则、四类骨架、多篇三模式、自检 |
| `README.md` | 重写：v1.2 变更、用法示例、可复现工作流、测试命令、新目录 |
| `references/structure.md` | 问句标题+结论句、时长/听众表、多篇三模式 |
| `references/deck-skeletons.md` | 四类骨架（新增器件/方法设计）、首页核心结论、页数不设下限 |
| `references/register.md` | 去掉绝对表述，加入证据语气分级（原文/作者解释/推断/建议/未知） |
| `references/ppt-build.md` | 新增 Visual–Claim 绑定、定量图与示意图边界、逐页闭环 |
| `references/pipeline.md` | 移除硬编码路径/桌面/slidep 细节，改为官方能力优先 + JSON 渲染 |
| `assets/explainer.html` / `outline.html` | 改为带 `{{TOKEN}}` 的渲染模板，拍数由 JSON 驱动 |
| `scripts/check_html.py` | 重写为 `HTMLParser`：错误嵌套、未知实体、裸 `&`、thead/tbody、真实 `@page` |
| `examples/12Cr13-ppt-outline.html` | 首页补核心结论，去掉"只给画面不给数据"，页脚动态化 |

### 新增

| 文件 | 用途 |
|---|---|
| `references/evidence.md` | 证据台账字段、使用流程、派生值、非数值论断、图表证据、检查边界 |
| `references/page-notes.md` | 逐页详解模板、模拟追问、不得编造答案 |
| `scripts/render_html.py` | 内容 JSON → HTML，转义 + 证据令牌注入（仅标准库） |
| `scripts/check_numbers.py` | 校验证据引用、状态、display 与 value 一致性 |
| `assets/content.schema.json` | 内容 JSON 的 JSON Schema（draft 2020-12） |
| `examples/evidence.json` | 证据台账示例 |
| `examples/explainer.content.json` / `outline.content.json` | 两类内容 JSON 示例 |
| `examples/demo-source.txt` | 仅用于演示证据引用的假数据源 |
| `tests/test_scripts.py` | 21 项单元测试 |
| `HANDOVER.md` | 本文档 |

---

## 五、新的工作流

```bash
# 1. 检查证据引用与数字一致性
python scripts/check_numbers.py evidence.json content.json

# 2. 渲染 HTML（按 kind 自动选 explainer / outline 模板）
python scripts/render_html.py content.json --evidence evidence.json -o deliverable.html

# 3. 校验 HTML 结构与打印样式
python scripts/check_html.py deliverable.html

# 4. 校验模板本身（允许占位符）
python scripts/check_html.py assets/*.html --allow-placeholders

# 5. 跑单元测试
python -m unittest discover -s tests -v
```

**PPT 阶段**：结构提纲经用户确认 → 每页按"标题 + 核心结论 + 视觉锚点 + 证据"制作 → 实际渲染/打开检查 → 同步更新逐页详解与模拟追问。未按此顺序、未经确认不得生成 PPT。

---

## 六、验证结果（已实测）

| 项目 | 结果 |
|---|---|
| 单元测试 | **21 项全部通过**（渲染、转义、证据校验、HTML 解析器） |
| 端到端（真实命令行） | 两类 JSON 的 `check_numbers` → `render_html` → `check_html` 全部 OK |
| 模板校验 | `explainer.html` / `outline.html` 结构 OK |
| 旧材料示例 | `12Cr13-ppt-outline.html` 校验 OK |
| Skill 元数据 | `quick_validate.py` → Skill is valid |

**未验证（不要当作已完成）**：

- WorkBuddy 平台内的实际触发效果与误触发情况；
- `slidep` 命令能否在当前环境运行（v1.2 已改为可选适配器，不再是主线）；
- 拿真实 PDF 论文跑完整"提取 → 讲解稿 → PPT"链路（工作区内暂无论文源文件）。

---

## 七、已知限制与下一步

1. `check_numbers.py` 只检查**显式声明**的 `{{E001}}` 令牌。章节编号、用户指定时长等结构性数字可普通书写；但来源科研数据应都用令牌，交付前需人工检查是否绕过令牌手写了来源数字。
2. HTML 脚本检查不能发现所有分页、溢出、字体替换问题，**必须实际打开并检查打印预览**。
3. 尚未做真实论文的端到端验收（实验/建模/仿真/器件方法四类各一篇）。建议下一轮补 fixtures 与四类骨架验收。
4. 触发/误触发测试目前是设计约束，尚未在平台内实测。

---

## 八、维护约定

- **保留 `agent_created: true`**，它是平台写入的标记。
- **不要宣传"提速 3 倍""HTML 错误率降为 0"**——渲染只消除一类格式错误，不能消除错误数据、内容缺失和视觉溢出。
- **数字检查的 scope 必须写明**：通过 = 声明的引用与显示值一致，**不证明与 PDF 原文一致**。
- 来源数字、图表、非数值论断一律走证据台账；推断与工程建议单独标注，不得伪装成作者结论。
