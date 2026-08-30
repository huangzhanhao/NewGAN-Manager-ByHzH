# NewGAN Manager 跨平台打包与 Web 化方案

> 项目：NewGAN-Manager-ByHzH（Football Manager NewGAN 换脸工具）v1.4.4
> 生成日期：2026-08-30
> 目标：打包成 Windows / Linux / macOS 安装包，或重构为免安装 Web 应用

---

## 一、项目现状分析

### 1.1 技术栈

| 项 | 现状 | 说明 |
| :--- | :--- | :--- |
| UI 框架 | **Toga 0.5.2** | BeeWare 的跨平台原生 GUI 库 |
| 打包工具 | **Briefcase 0.3.25** | 官方最新已到 0.3.26 |
| Python | 3.11 | CI 与本地一致 |
| 核心依赖 | requests、dhooks、travertino | dhooks 仅 Reporter.py 用，未接入 UI |

### 1.2 架构耦合度评估（关键结论）

这是决定"打包"与"Web 化重构"可行性的核心。逐文件检查后结论非常乐观：

**`core/` 目录（业务逻辑层）几乎零依赖 Toga。**

| 模块 | 行数 | 是否依赖 Toga |
| :--- | ---: | :--- |
| ConfigManager.py | 36 | 否，纯 json/文件 IO |
| ProfileManager.py | 115 | 否 |
| FaceMapper.py | 214 | 否 |
| RtfParser.py | 243 | 否 |
| XmlParser.py | 164 | 否 |
| NewGanLogManager.py | 96 | 否 |
| Reporter.py | 24 | 否（依赖 dhooks，但未被 UI 引用） |
| SourceSelection.py | 28 | **是**（唯一例外，自定义 `toga.Selection` 子类） |

- 全项目 `import toga` 只出现在 **3 个 UI 文件**（`app.py`、`app_main_tab.py`、`app_log_tab.py`）+ `SourceSelection.py`。
- 依赖方向是单向的：**UI 层 → core 层**，core 层不反向依赖 UI。
- 换脸主流程（解析 RTF → 映射头像 → 写 config.xml）已通过 `asyncio.run_in_executor` 放到线程池，与 UI 解耦良好。

**结论：**
- 对"打包"路线：这是标准 Toga 项目，Briefcase 配置已就绪，可直接打包。
- 对"Web 化"路线：约 **900 行 core 业务逻辑可原样复用**，只需重写约 **1200 行 UI 层**（3 个文件），重构成本可控。

### 1.3 已发现的问题（影响打包）

| 问题 | 位置 | 影响 |
| :--- | :--- | :--- |
| CI 依赖版本过旧 | 3 个 workflow 用 `beeware==0.3.0 toga==0.4.0` | 与 pyproject 的 toga 0.5.2 不一致，构建会失败或行为漂移 |
| 测试路径失效 | workflow 仍指向 `src/test_app.py` 等旧模块 | 重构后这些文件已不存在，CI 测试步骤必挂 |
| Linux runner 已废弃 | `ubuntu-18.04` | GitHub Actions 已下线，需升级 |
| 产物版本写死 | artifact 名硬编码 `v1.4.0` | 与实际 1.4.4 不符 |
| Linux 依赖可能冗余 | `libwebkitgtk`、`gir1.2-webkit` | 项目未使用 WebView，这两项可考虑移除 |
| requirements.txt 编码异常 | 文件为 UTF-16 编码 | 常规 `pip install -r` 会解析失败 |
| Reporter.py 未接入 | 含 dhooks 硬编码依赖 | 可从打包依赖中剔除 |

---

## 二、三条可行路线总览

| 维度 | 路线 A：Toga+Briefcase 原生打包 | 路线 B：重构为"本地 Web"应用 | 路线 C：纯浏览器 Web 应用 |
| :--- | :--- | :--- | :--- |
| 是否真正"免安装" | 否（需安装安装包） | 半免安装（仍需本地装 Python 或打包运行时） | **是**（浏览器直接打开） |
| 保留现有代码 | 100% | 复用约 900 行 core，重写 UI | 复用 core，UI+文件访问全重写 |
| 读写本地文件能力 | 完整 | 完整 | **受限**（浏览器沙箱） |
| 工作量 | 小（修 CI 为主） | 中 | 大 |
| 用户体验 | 原生窗口 | 浏览器窗口/内嵌窗口 | 受浏览器限制 |
| 推荐度 | ★★★★★ | ★★★☆ | ★★ |

---

## 三、路线 A：Toga + Briefcase 原生打包（推荐）

### 3.1 为什么推荐

1. 项目本就是标准 Toga + Briefcase 结构，`pyproject.toml` 里 `[tool.briefcase.app.newganmanager]` 已配好 Windows / macOS / Linux 三平台 backend。
2. Briefcase 当前稳定支持：
   - **Windows** → `.msi` 安装包（WiX 5 生成）/ `.zip`
   - **macOS** → `.dmg` / `.app` / `.pkg`
   - **Linux** → `.AppImage` / `.deb` / `.rpm` / Flatpak
3. 工作量最小，主要是修复已经过时、跑不通的 CI。

### 3.2 具体实施步骤

**第一步：本地验证打包可用**

```powershell
# Windows 本机
pip install -U briefcase   # 升到 0.3.26
cd D:\MyProject\NewGAN-Manager-ByHzH
briefcase create
briefcase build
briefcase package          # 产物在 dist/，得到 NewGAN-Manager-1.4.4.msi
```

**第二步：清理打包依赖（瘦身 + 避免告警）**

- `pyproject.toml` 中 `requires` 可移除 `dhooks`（Reporter 未接入 UI）。
- Linux 段 `system_requires` 里的 `libwebkitgtk-3.0-0`、`gir1.2-webkit-3.0` 若无 WebView 可移除，减小体积、避免拉取已下架的 webkitgtk3。

**第三步：修复三个 GitHub Actions workflow（这是当前最大障碍）**

以 `windows-build.yml` 为例，需要改：

```yaml
# 1) 依赖版本对齐（原为 beeware==0.3.0 toga==0.4.0）
python -m pip install briefcase==0.3.26 toga==0.5.2

# 2) 测试命令改为指向现存测试（原指向已删除的 src/test_app.py）
python -m unittest discover -s src/tests -p "test*.py"

# 3) 产物版本动态化，不再硬编码 1.4.0
#    可用 ${{ github.ref_name }} 或读取 pyproject 版本
```

`linux-build.yml` 额外需要：

```yaml
# ubuntu-18.04 已下线，改为
runs-on: ubuntu-22.04   # 或 ubuntu-latest
# webkitgtk 依赖换成当前发行版可用的 gir1.2-webkit2-4.1（若确需）
```

`mac-build.yml`：`package` 步骤已有 `--adhoc-sign`（临时签名），若需对外分发且避免"无法打开"提示，应接入 Apple Developer 证书 + `briefcase package --adhoc-sign` 之外的正式签名与公证（notarization）。

**第四步：macOS 签名与公证（可选但强烈建议）**

- 不签名/仅 ad-hoc：其他用户下载会被 Gatekeeper 拦截。
- 正式分发需：Apple Developer 账号 → 配置证书 → `briefcase package` 自动签名 → 提交 Apple 公证。

### 3.3 路线 A 的产出

- `dist/NewGAN-Manager-1.4.4.msi`（Windows）
- `dist/NewGAN-Manager-1.4.4.dmg`（macOS）
- `linux/NewGAN-Manager-1.4.4-x86_64.AppImage`（Linux，或改出 `.deb`/Flatpak）
- 三平台 CI 自动构建，打 tag 即出包。

### 3.4 风险与注意

- **toga 0.5.2 在 Linux 的 GTK 版本兼容**：部分新发行版 GTK4 与 toga-gtk 0.5.x 仍有边缘问题，建议在主流发行版（Ubuntu 22.04/24.04）实测。
- **MSI 全用户安装权限**：Briefcase 0.3.26 修复了 MSI 全用户安装时目录权限继承问题（CVE-2026-33430），建议务必升到 0.3.26。
- **中文路径**：README 已知问题提到头像包含中文路径时预览可能失败，打包后仍需回归测试。

---

## 四、路线 B：重构为"本地 Web"应用（次选）

### 4.1 前提澄清

**"本地 Web 应用"≠"免安装"。** 它的形态是：程序在本地起一个 Web 服务，用户用浏览器打开 `http://localhost:端口`。但程序本体仍需本地运行，因此要么：
- 用户装 Python 后 `python -m ...` 启动，或
- 用 PyInstaller / Nuitka 把它打包成单个可执行文件（内置 Web 服务）。

**它的优势**是界面用 Web 技术，天然跨平台、样式现代、迭代快，且能复用全部 core 逻辑。

### 4.2 框架选型

| 框架 | 特点 | 适合度 |
| :--- | :--- | :--- |
| **NiceGUI** | 基于 FastAPI + Vue/Quasar，纯 Python 写 UI，支持 `ui.run()` 起本地服务，也可打包成桌面窗口（`native=True`，基于 pywebview） | ★★★★★ 推荐 |
| **Flet** | 基于 Flutter 引擎，Material Design，同样支持 Web+桌面+移动 | ★★★★ |
| Streamlit | 上手最快但布局定制弱、交互模型不匹配本工具 | ★★ |

**推荐 NiceGUI**，理由：
- 组件丰富（表格、文件上传、开关、进度条、对话框），与本工具 UI 需求高度吻合；
- `ui.run(native=True)` 一行即可从"浏览器模式"切到"独立桌面窗口模式"；
- 异步原生（FastAPI），与现有 `asyncio` 换脸流程无缝衔接。

### 4.3 重构工作量拆解

| 任务 | 说明 | 预估 |
| :--- | :--- | :--- |
| 复用 core/ | ConfigManager、ProfileManager、FaceMapper、RtfParser、XmlParser、NewGanLogManager 原样保留 | 0 改动 |
| 重写 Main 标签 | Profile 管理、目录/文件选择、模式选择、进度条、Viewer 预览 | 中 |
| 重写 Log 标签 | 日志级别筛选、滚动显示 | 小 |
| 文件选择对话框 | 用 NiceGUI 的 `ui.upload` / 或 native 模式下的系统对话框 | 小 |
| 图片预览 | `ui.image` 直接读本地路径 | 小 |
| 进度与取消 | 复用现有 `asyncio` + `run_in_executor`，用 NiceGUI 的 `ui.linear_progress` | 小 |

**总工作量：约重写 1200 行 UI，core 不动。** 相比从零重写大幅降低。

### 4.4 打包为"免安装"可执行文件

重构为 NiceGUI 后，仍可用 **PyInstaller** 打成单文件：

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name "NewGAN-Manager" main_web.py
```

得到一个 `NewGAN-Manager.exe`（及对应平台的单文件），用户双击即用、无需装 Python——这才是"本地 Web 技术 + 免安装"的完整闭环。

### 4.5 风险与注意

- **文件访问不是问题**（本地运行时对文件系统有完整权限，这是路线 B 相对路线 C 的最大优势）。
- 需处理 NiceGUI 静态资源在 PyInstaller 内的打包路径问题（常见坑，有成熟方案）。
- 若选 `native=True` 桌面窗口，需引入 `pywebview`，Linux 上依赖 WebKitGTK，反而又引入系统依赖——若目标是极简分发，建议走"浏览器打开"或纯 PyInstaller。

---

## 五、路线 C：纯浏览器 Web 应用（谨慎选择）

### 5.1 形态

托管一个网页，用户打开浏览器即用，**真正免安装**。

### 5.2 核心矛盾：本地文件读写

本工具的根本动作是：
1. 读用户硬盘上的 **头像包目录**（可能数 GB、成千上万张图）；
2. 读用户导出的 **RTF 名单**；
3. 写 **config.xml** 到头像包目录，供 FM 读取。

纯浏览器受沙箱限制：
- 只能通过 **File System Access API** 让用户手动授权目录，且**基本只有 Chromium 系（Chrome/Edge）支持**，Firefox/Safari 受限；
- 上传数 GB 头像包到服务器再处理，**不现实**（流量、隐私、时间都不可接受）；
- 因此头像匹配必须在**客户端浏览器内**用 JS 完成，等于把 Python core 逻辑**用 JS 重写一遍**。

### 5.3 技术设想

- 前端：纯 JS/TS（React/Vue），用 File System Access API 读写用户本地目录；
- 解析层：RTF 解析、XML 生成用 JS 重写；
- 无后端，或仅一个轻量静态托管（GitHub Pages / Vercel）。

### 5.4 风险与代价

| 风险 | 说明 |
| :--- | :--- |
| **浏览器兼容性** | File System Access API 非全浏览器支持，需明确提示用户用 Chrome/Edge |
| **core 逻辑重写** | ~900 行 Python 需用 JS 重写并保证行为一致，测试成本高 |
| **大目录性能** | 浏览器遍历数千文件、读 RTF、生成 XML，性能与内存需谨慎处理 |
| **用户心智** | 让普通 FM 玩家理解"浏览器要访问你的文件夹"并接受授权，有门槛 |

**结论**：路线 C 是唯一真正"免安装"的方案，但代价最高、风险最大，且牺牲了对非 Chromium 浏览器的支持。**除非明确目标是"网页版、零安装、面向大量不想装软件的用户"，否则不建议。**

---

## 六、选型建议

### 如果你的首要诉求是"尽快、稳妥地给用户三平台安装包"
→ **选路线 A**。项目天然适配，工作量集中在修复现有 CI，1～2 天可打通三平台自动构建。

### 如果你想要"更现代的界面 + 仍保留本地文件完整读写 + 单文件免安装"
→ **选路线 B（NiceGUI + PyInstaller）**。复用全部业务逻辑，界面体验升级，最终产出单文件可执行程序。

### 如果你坚持"打开浏览器就能用、什么都不用装"
→ **选路线 C**，但要接受浏览器兼容限制、core 逻辑用 JS 重写的工作量，以及对用户做"授权访问文件夹"的引导。

### 折中推荐
**先落地路线 A**（解决当下分发问题），**再评估路线 B**（作为下一代界面升级）。路线 C 可作为远期、面向更广用户群的选项单独立项。

---

## 七、附：需要修复的文件清单（路线 A 直接可用）

| 文件 | 改动 |
| :--- | :--- |
| `.github/workflows/windows-build.yml` | 升级 briefcase/toga 版本、改测试命令、动态化产物版本 |
| `.github/workflows/mac-build.yml` | 同上 + 正式签名/公证配置 |
| `.github/workflows/linux-build.yml` | `ubuntu-18.04` → `ubuntu-22.04`、修正 webkit 依赖、改测试命令 |
| `pyproject.toml` | 移除 `dhooks`、清理 Linux `libwebkitgtk`/`gir1.2-webkit` 冗余项 |
| `requirements.txt` | 修正为 UTF-8 编码（当前为 UTF-16，pip 无法解析） |

> 若确认走路线 A，我可以直接帮你把这三个 workflow 与 `pyproject.toml` 修复到位。

---

## 八、信息来源说明

- 项目现状：基于对本仓库 `pyproject.toml`、`requirements*.txt`、`src/newganmanager/**`、`.github/workflows/**`、`README.md` 的实际读取。
- Briefcase 版本与产物格式：BeeWare 官方文档（2026-08），最新稳定版 0.3.26，支持 MSI/DMG/AppImage/deb/Flatpak。
- NiceGUI / Flet 生态：2026 年公开资料，两者均为活跃的纯 Python 跨端 UI 框架。
