# 环境与依赖

换机器、重装系统，或某一步突然报错时看这一页。目标：**十分钟内让 Skill 跑起来**。

---

## 一、依赖分层

| 层 | 内容 | 缺了会怎样 |
|---|---|---|
| **必需** | Python 3.9+（只用标准库） | 证据检查、内容渲染、HTML 校验全部不可用 |
| **必需** | 本仓库的 `references/` `assets/` `scripts/` `tests/` | 提示词还能用，但脚本和模板不可用 |
| 推荐 | WorkBuddy `workbuddy-pdf` 技能 | 无法批量取 PDF 文本，只能手工粘贴原文 |
| 推荐 | WorkBuddy `workbuddy-pptx` 技能（内含 `slidep` CLI） | 无法直接生成 pptx，只能交提纲与 `.slide` 源码 |
| 可选 | `pypdf` 或 `pdfplumber` | `workbuddy-pdf` 不可用时的替代取文方案 |
| 可选 | 中文字体（微软雅黑 / 苹方 / Noto CJK） | 生成的 PPT 中文可能显示方框 |

**没有第三方 Python 包也能完成 1–3 步**（讲解稿、提纲、结构）。只有 PPT 生成依赖外部能力，缺失时按上表降级，不要把“装不上”变成“做不了”。

---

## 二、三分钟上手

```bash
# 1. 放到用户级 Skill 目录（两个平台通用）
git clone https://github.com/Zyt1112/report-prep.git ~/.workbuddy/skills/report-prep

# 2. 自检：缺什么、怎么修，一次说清
cd ~/.workbuddy/skills/report-prep
python scripts/doctor.py --fix-hint

# 3. 跑一遍测试，确认脚本没被装坏
python -m unittest discover -s tests -v
```

Windows 上自检报 `slidep` 原生模块失败时，再跑一条：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1 -UseVirtualDrive -Persist
```

若提示“在此系统上禁止运行脚本”，先只对当前会话放开策略：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& .\scripts\setup_env.ps1 -DryRun    # 先看它要做什么
```

然后在 WorkBuddy 里直接说“用 report-prep 给这篇论文做汇报”，或显式调用 Skill。

---

## 三、Windows：`slidep` 报 `Failed to load native binding`

**现象**：`slidep --version` 或 `slidep create` 立刻失败，报 `Failed to load native binding` / `@swc/core` 加载失败；`node` 本身正常。

**根因**：`@swc/core` 出于安全校验，会检查原生 `.node` 文件所在路径的**整条父目录链**。只要链上任意一级给 `Everyone` 或 `Authenticated Users` 授了替换/写入权限，它就拒绝加载。Windows 上 `C:\`、`C:\Users`、`%LOCALAPPDATA%` 默认常带这类 ACE，所以新建缓存目录也没用。

**解法（按顺序试）**：

1. 收紧现有缓存目录：
   ```powershell
   icacls "$env:LOCALAPPDATA\swc" /inheritance:d
   icacls "$env:LOCALAPPDATA\swc" /remove:g "*S-1-1-0" "*S-1-5-11"
   ```
2. 若仍失败，用最小权限目录 + 虚拟盘绕开父链：
   ```powershell
   mkdir D:\swcroot\cache
   icacls D:\swcroot /inheritance:r
   icacls D:\swcroot /grant:r "$env:USERNAME:(OI)(CI)F" "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F"
   subst X: D:\swcroot
   setx SWC_NATIVE_BINDING_CACHE "X:/cache"
   ```
3. 每个新终端都要有 `SWC_NATIVE_BINDING_CACHE`；`setx` 后要重开终端。
4. `subst` 虚拟盘**重启后失效**，重跑 `scripts/setup_env.ps1` 即可；想永久生效，把 `subst X: D:\swcroot` 放进任务计划（登录时触发）。

> 不需要为了这个去改 `C:\` 的 ACL。改系统盘权限的风险远大于收益。

---

## 四、路径约定

| 用途 | Windows | macOS / Linux |
|---|---|---|
| 用户级 Skill | `C:\Users\<你>\.workbuddy\skills\report-prep\` | `~/.workbuddy/skills/report-prep/` |
| 项目级 Skill | `<项目>\.workbuddy\skills\report-prep\` | `<项目>/.workbuddy/skills/report-prep/` |
| 校徽 | `assets/tyust-logo.png` | 同 |
| 每份 deck 的校徽 | `<deck 项目>/assets/tyust-logo.png` | 同 |

**校徽必须复制到每份 deck 自己的 `assets/`**：`.slide` 里的 `src` 是相对 deck 项目根目录解析的，指不到 Skill 目录。

---

## 五、换机器清单

- [ ] `git clone` 到用户级 Skill 目录
- [ ] `python scripts/doctor.py --fix-hint`，把 FAIL 清掉、WARN 按需处理
- [ ] `python -m unittest discover -s tests -v`，应为 21 项全过
- [ ] 用 `examples/deck-v3-4340m/` 跑一遍：`slidep create` + 逐页 `upsert-dsl`，确认能出 6 页
- [ ] 打开生成的 pptx，检查三件事：校徽在、中文不是方框、页码分母正确
- [ ] 把要汇报的论文 PDF 放好，先建 `evidence.json` 再写内容 JSON

---

## 六、常见报错对照

| 报错 | 原因 | 处理 |
|---|---|---|
| `Failed to load native binding` | SWC 父目录链 ACE 过宽 | 见第三节 |
| `No such file or directory: assets/tyust-logo.png` | 校徽没复制到 deck 项目 | 复制 `assets/tyust-logo.png` |
| `{{E001}}` 原样出现在 HTML 里 | 渲染时没带 `--evidence` | `render_html.py ... --evidence evidence.json` |
| `check_numbers.py` 报“证据项缺 value” | 该条是定性论断，被当成了数值证据 | 定性内容不占证据令牌，改写正文并标 PDF 结论编号 |
| 页码分母是旧值 | 手改了页数没改页码 | 页码由生成时按实际页数写，改页数就重生成 |
| pptx 打开中文变方框 | 缺中文字体 | 装微软雅黑 / 苹方 / Noto CJK |
| `slidep upsert-dsl` 报页面索引越界 | 用了 `--page-index` 但文件页数不足 | 去掉 `--page-index` 让工具追加，或先 `create` |

---

## 七、边界

- 本 Skill 不联网、不调用外部 API；所有校验都在本地完成。
- `doctor.py` 只读检查，唯一的写操作是在 Skill 根目录建一个临时探针文件并立即删除。
- `setup_env.ps1` 只动两处：`%LOCALAPPDATA%\swc` 的 ACL、`D:\swcroot`（或 `C:\swcroot`）目录与 `subst` 映射。加 `-DryRun` 可以先看它要做什么。
