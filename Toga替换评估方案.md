# NewGAN Manager：UI 框架替换评估（四点需求版）

> 项目：NewGAN-Manager-ByHzH v1.4.4
> 生成日期：2026-08-30（按用户四点明确需求修订，取代初版结论）
> 用户四点需求：
> 1. 只需桌面端：Windows / Linux / macOS
> 2. 前端渲染交互流畅：后台跑进度时，前端实时显示进度条与日志
> 3. 安装包体积小；安装目录用户可指定；全部组件在单一应用目录；卸载后干净无残留
> 4. 开发时只关注核心业务代码，不过多关注各平台打包流程

---

## 一、结论

**维持"替换 Toga、改用 Flet"的建议，但按第 3 点需求调整分发形态：不做传统安装包，改为"绿色单目录"分发。**

| 你的需求 | Flet 方案如何满足 |
| :--- | :--- |
| ① 桌面三平台 | `flet build windows/macos/linux` 一条命令一个平台，官方 CI 模板三平台全覆盖 |
| ② 实时进度与日志 | Flutter 引擎自绘渲染（60fps）+ 原生 asyncio；现有"线程池跑业务 + 进度回调"架构原样平移 |
| ③ 小体积、单目录、干净卸载 | 产物本身就是一个自包含目录/`.app`，压成 zip 分发；用户解压/拖放到**任意自选目录**；所有配置、日志、Profile 数据都写在应用目录内，**删除目录即彻底卸载** |
| ④ 只管业务代码 | 打包仅一条 `flet build` 命令 + 一份 `pyproject.toml` 配置；无 Briefcase 的 create/build/package 三段式、无每平台独立模板目录 |

**为什么第 3 点需求会改变分发形态**：你要的"安装目录自选 + 单一目录 + 卸载无残留"，恰恰是传统安装包（MSI/DMG）做不好的——安装包必然写注册表、开始菜单、卸载器，卸载后常有残留。而"绿色单目录"天然全部满足：没有安装过程，目录放哪由用户决定，删目录即卸载。当前 Toga 版本其实已经是"数据全在应用目录"的设计（`.config/`、`.user/`、`newgan.log` 都在应用目录内），迁移时保留这个设计即可无缝对接绿色分发。

---

## 二、逐条需求核验

### 需求 ①：桌面三平台

Flet 官方构建矩阵（2026-08 官方文档）：

| 在哪台机器上构建 | windows | macos | linux |
| :--- | :---: | :---: | :---: |
| Windows | ✅ | ✅ | ✅ |
| macOS | ✅ | ✅ | ✅ |
| Linux | ✅ | ✅ | ✅ |

- 三个平台都是 `flet build <平台>` 一条命令，产物自动输出到 `build/windows`、`build/macos`、`build/linux`。
- 各平台构建机前置条件（**只影响打包机，不影响用户**）：
  - Windows：Visual Studio 的 "Desktop development with C++" 工作负载（GitHub Actions 的 `windows-latest` 自带）
  - Linux：GTK3 等开发库（官方 CI 模板提供了一键安装命令，从 `flet --version --json` 自动取依赖清单）
  - macOS：Xcode 命令行工具（`macos-*` runner 自带）
- Flutter SDK 首次构建时**自动下载安装**，无需手动配置。

### 需求 ②：实时进度条 + 实时日志

这是 Flet 的强项，且与你现有架构完全同构：

**现状**（Toga 版）：`app_main_tab.py` 已经把解析/映射/写 XML 放到 `run_in_executor` 线程池，通过 `_update_progress(status, value)` 更新进度条；日志通过队列 + 50ms 批处理刷到文本框。

**迁移后**（Flet 版）：架构一比一平移，只换控件：

```python
# 伪代码示意：核心模式与现有代码同构
progress = ft.ProgressBar(value=0)
status = ft.Text("Ready")
log_area = ft.TextField(multiline=True, read_only=True)

async def replace_faces(e):
    status.value = "Validating RTF file..."
    progress.value = 0.0
    page.update()
    # 重活照旧进线程池，不阻塞 UI 线程
    rtf_data = await asyncio.to_thread(rtf_parser.parse_rtf, rtf, only_newgan)
    progress.value = 0.4
    status.value = "Mapping player to image..."
    page.update()
    ...
```

要点：
- Flet 桌面版是本地 Flutter 客户端 + 内嵌 Python 运行时，`page.update()` 走进程内通道，进度/日志刷新延迟毫秒级，渲染由 Flutter 引擎保证流畅（自绘 60fps，不受系统控件拖累）。
- 日志沿用你现有的**队列 + 批处理**模式（每 50ms 刷一批），避免高频 `update()` 抖动；现有 `NewGanLogManager` 不用改，只是输出目标从 `MultilineTextInput` 换成 `ft.TextField(multiline=True)`。
- 取消按钮：现有 `task.cancel()` 机制原样保留。

### 需求 ③：体积小、目录自选、单一目录、无残留

**分发形态设计（绿色单目录）：**

| 平台 | `flet build` 产物 | 分发形式 | 用户操作 |
| :--- | :--- | :--- | :--- |
| Windows | 自包含目录（`.exe` + 运行时） | 压成 `.zip` | 解压到**任意自选目录**，双击 exe |
| macOS | `.app` 包 | 压成 `.zip` 或直接提供 | 拖到任意位置（不强制 Applications） |
| Linux | 自包含目录（可执行文件 + 资源） | 压成 `.tar.gz` | 解压到任意目录，运行 |

**为什么这满足"干净无残留"：**

- 应用的全部用户数据——配置（`.user/cfg.json`、`<Profile>.json`）、Profile 快照（`<Profile>.xml`）、种族映射表（`.config/eth_cfg.json`）、日志（`newgan.log`）——按现有设计**全部写在应用目录内**。删除应用目录 = 卸载完成，无注册表、无残留文件。
- 迁移时数据目录定位规则：打包环境下取可执行文件所在目录（`os.path.dirname(sys.executable)`），开发环境下取源码目录，与现在 `self.paths.app` 的语义一致。
- 诚实说明一个细节：Flet 桌面版基于 Flutter，Flutter 运行时自身可能在系统用户数据目录写少量缓存（如 `console.log`）。这是运行时级的小文件，不含任何用户数据；如需绝对零残留，可在迁移冲刺中实测并通过环境变量/配置收敛，列为迁移验证项。

**体积预期（待实测，不虚构精确值）：**

- 产物包含 Flutter 客户端 + 内嵌 Python 运行时，解压后预计数十 MB 量级，压缩后更小；与当前 Briefcase MSI（同样内嵌完整 Python 运行时 + 依赖）属同量级或更小。
- Flet 打包默认把 `.py` 编译为 `.pyc` 并清理垃圾文件，支持 `--exclude` 排除无关目录、`--cleanup-*` 进一步瘦身。
- 附带收益：因为不再打包 `dhooks`/`requests`（见第五节死依赖清理），依赖面比现在更窄。
- 体积上限说明：在"仍用 Python 写界面"的前提下，任何方案都绕不开内嵌 Python 运行时，体积下不来是这一技术栈的共性；若未来把体积置于一切之上，只剩 Tauri（Rust + WebView，包体可降到 ~10MB）一条路，但那要求界面用 JS/TS 重写，违背你的第 4 点需求，故不推荐。

**用户写权限提示**：绿色目录若被用户放在受保护路径（如 `C:\Program Files`），写应用内数据需要管理员权限——与现状一致。README 建议引导用户放在个人目录；Windows 侧也可保留 `--uac-admin` 选项作为备选。

### 需求 ④：开发只关注业务代码

| 项 | Toga + Briefcase（现状） | Flet |
| :--- | :--- | :--- |
| 打包命令 | 每平台 `create → build → package` 三步 | 每平台一条 `flet build <平台>` |
| 平台配置 | `[tool.briefcase.app.x.windows/macOS/linux]` 三段 + 各自 backend 依赖 | 一份 `pyproject.toml`，配置项按需可选 |
| 系统依赖管理 | Linux 段要手动列 `system_requires`（现在还挂着无用的 webkitgtk） | 官方提供依赖清单自动安装命令 |
| CI | 三个各自失修的 workflow | 官方提供可直接抄的三平台 GitHub Actions 模板（含 Linux 依赖自动安装、产物上传） |
| 迭代调试 | `briefcase dev` | `flet run`（热重载） |

开发者日常接触面收敛为：**写 Python 业务代码 → `flet run` 调试 → `flet build` 出包**。平台差异被命令参数吸收，符合"不过多关注打包流程"。

---

## 三、候选复核：Flet 仍是唯一解吗？

按新需求重新过一遍候选：

| 候选 | 桌面三平台 | 实时进度/日志 | 绿色单目录适配 | 打包心智负担 | 结论 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Flet** | ✅ | ✅ 自绘渲染 | ✅ 产物即自包含目录 | ✅ 一条命令 | **推荐** |
| NiceGUI | ✅（native 窗口） | ✅ | ⚠️ Linux native 模式依赖 pywebview→WebKitGTK 系统库，违背"精简/无残留" | ⚠️ 需自行拼 PyInstaller | 不选 |
| 保留 Toga + Briefcase | ✅ | ✅ | ⚠️ MSI 安装器模式与"无残留/目录自选"冲突 | ❌ 三段式命令 + 平台模板 | 不选 |
| PySide6 | ✅ | ✅ | ✅ 可 onedir 绿色分发 | ⚠️ 打包体积更大、Qt 许可需注意、代码量大 | 备选，不推荐 |
| Tauri | ✅ | ✅ | ✅ 体积最小 | ❌ 界面需 JS/TS 重写 | 违背需求④，不选 |

结论不变：**Flet**。与初版的差别在于——移动端优势不再是理由（你不需要），胜出的理由收敛为：桌面三平台一条命令、自绘渲染保证流畅、产物天然适配绿色单目录分发。

---

## 四、组件映射表（不变，供迁移对照）

| 现有 Toga 组件 | Flet 对应 |
| :--- | :--- |
| `toga.OptionContainer`（Main/Profile/Log 三标签） | `ft.Tabs` |
| `toga.TextInput` / `MultilineTextInput` | `ft.TextField`（`multiline`、`read_only`） |
| `toga.Button` | `ft.ElevatedButton` / `ft.TextButton` |
| `toga.Switch` ×3 | `ft.Switch` |
| `toga.Selection` / `SourceSelection` | `ft.Dropdown` |
| `toga.ProgressBar` + 状态 Label | `ft.ProgressBar` + `ft.Text` |
| `toga.ImageView` | `ft.Image` |
| `toga.Box` + `Pack(ROW/COLUMN)` | `ft.Row` / `ft.Column` |
| `toga.OpenFileDialog` / `SelectFolderDialog` | `ft.FilePicker` |
| `toga.ErrorDialog` / `InfoDialog` / `QuestionDialog` | `page.open(ft.AlertDialog(...))` |
| `toga.Command` 帮助菜单 | 右上角 `ft.PopupMenuButton` |

业务衔接不变：`core/` 七个文件（约 900 行）零改动；`asyncio` 事件循环、线程池、取消机制、日志队列全部沿用。

---

## 五、实施步骤（按新需求修订）

| 步骤 | 内容 | 预估 |
| :--- | :--- | :--- |
| 1 | 建分支；装 `flet`，锁定版本；按官方结构整理项目（`pyproject.toml` + `src/main.py` + `assets/` 图标） | 0.5 天 |
| 2 | 清理死代码/死依赖：删 `Reporter.py`、`check_for_update` 死代码，移除 `dhooks`、`requests`；修复 `requirements.txt` 的 UTF-16 编码问题 | 0.5 天 |
| 3 | **数据目录改造**：把 `self.paths.app` 语义迁移为"打包时取可执行文件所在目录"，保证全部数据落在应用目录内（绿色分发前提） | 0.5 天 |
| 4 | 重写 Main 标签（Profile 管理 + 路径选择 + 模式开关 + 执行/取消 + 进度条） | 1~1.5 天 |
| 5 | 重写 Viewer 区与 Log 标签（日志批处理刷屏沿用现有队列机制） | 1 天 |
| 6 | 三平台 `flet build` 打通 + 实测产物体积、中文路径头像包、大 RTF | 1 天 |
| 7 | 用官方 GitHub Actions 模板重建 CI：三平台构建 + 压 zip + 上传 Release 产物 | 0.5 天 |

合计约 **5~6 个工作日**。

---

## 六、风险清单（按新需求更新）

| 风险 | 对策 |
| :--- | :--- |
| Flet 尚未 1.0，版本间有破坏性变更 | 锁定版本号；升级前读官方 changelog |
| Linux 用户机器需要 GTK3 运行库 | GTK3 是主流发行版桌面环境标配；README 注明最低要求即可 |
| Flutter 运行时可能在用户数据目录留少量缓存（如 `console.log`） | 迁移验证项：实测残留并评估收敛手段；不含用户数据，删除应用目录不影响 |
| 产物体积为"Python 界面技术栈"共性下限 | 预期与现状同量级；若不可接受，唯一出路是换非 Python 界面栈（违背需求④），需重新决策 |
| `ft.FilePicker` 在各平台的目录选择行为差异 | 步骤 6 回归重点：选目录、按扩展名过滤、中文路径 |
| 绿色目录放受保护路径导致写失败 | README 引导 + 可选 `--uac-admin`（Windows） |

---

## 七、最终建议

1. **换，换成 Flet**——四个需求逐条核验通过，且没有引入新的硬伤。
2. **分发形态改为绿色单目录 zip**（Windows zip / macOS zip 或 .app / Linux tar.gz），放弃 MSI/DMG 安装器——这是同时满足"目录自选 + 单一目录 + 无残留"的唯一干净解法。
3. 迁移重心在 UI 重写（约 1200 行）+ 数据目录改造，核心业务逻辑零改动，约 5~6 个工作日。
4. 顺手完成死依赖清理、requirements.txt 编码修复、CI 重建（官方模板直接可用）。

确认后我可以直接开工：从步骤 1+2（分支、依赖清理、Flet 项目骨架）开始。

---

## 八、信息来源说明

- 项目现状：本仓库全量源码扫描（import 清点、模块行数、数据目录设计见 `app.py` `_setup_application_data` 与 README）。
- Flet 构建矩阵、各平台前置条件、`flet build` 配置项（体积瘦身选项、`.pyc` 编译、`--exclude`/`--cleanup`）、官方 GitHub Actions 三平台模板、console.log 重定向行为：Flet 官方文档 Publishing/Windows/Linux 页（2026-08 访问）。
- Linux 构建依赖清单中 gstreamer/mpv 项仅媒体功能需要、可省略：官方 Linux 打包页原文明确。
- 体积数字为基于产物构成的量级判断，标注"待实测"，未虚构精确值。
