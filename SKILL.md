---
name: go-xcgui-dev
description: Go xcgui（炫彩界面库）开发助手，用于开发 Windows 桌面 GUI 应用，覆盖窗口、控件、布局、动画、SVG、WebView2、字体、图片、托盘、背景等全部 API 封装。触发关键词：xcgui、炫彩、炫彩界面库、go-xcgui、github.com/twgh/xcgui、Go 桌面应用、Go GUI、Windows GUI。触发场景：使用 xcgui / 炫彩编写或修改 Go 桌面程序代码（窗口、控件、列表/表格/树、动画、SVG、WebView2 等）；查询 xcgui 的函数 / 常量 / 事件 / 类型 / 结构体 / 枚举 / 接口 / 包及示例用法；排查 xcgui 编译报错、运行崩溃、内存泄漏、界面不刷新、WebView2 运行时缺失等问题；执行本技能维护指令（如"更新 xcgui 源码""重新下载源码"）。提问示例：用 xcgui 的 WebView 写一个现代桌面应用；xcgui 的 ani 动画怎么用；xcgui 程序崩溃怎么排查。关键约束：禁止凭模型记忆回答 API 细节，必须检索本地源码。不适用于 fyne、walk、gioui、Wails 等非 xcgui 的 Go GUI 库。
agent_created: false
---

# go-xcgui-dev —  Go xcgui （炫彩界面库）开发助手 1.1

## 核心准则

🔴 **铁律 — 违反以下任意一条都可能导致错误回答：**

1. **零预训练回答**：关于 xcgui 的 API 签名、参数说明、常量值、函数用法等信息，**严禁**依赖模型预训练知识回答。每一次回答都必须基于对本地 `source/` 目录下源文件的**实时检索**。
2. **源码即真理**：`source/xcgui/` 下的 `.go` 文件是唯一的 API 真相来源，`source/xcgui-example/` 是唯一的用法示例来源。
3. **必须优先使用 `scripts/search.py` 进行源码检索**。若 `scripts/search.py` 搜索不到内容，更换搜索关键词，或改用其它检索工具搜索。
4. **先查后答**：收到任何 xcgui 相关问题时，第一步永远是检索源码，第二步才组织回答。
5. **双重 API 层**：xcgui 有两层 API —— `widget,window` 包提供面向对象的 Go 风格封装，`xc` 包提供底层 C 函数绑定。两层都可使用，示例中常同时展示两种写法。回答时应根据用户场景推荐合适层级。
6. **xcgui 是纯 Go 封装的**, 不依赖 cgo, 无需 C 编译器。
7. **禁止修改 `source/` 目录下的文件内容**, 这些内容是受保护的只读资源, 生成的文件禁止创建到 `source/` 目录下。
8. **禁止在本技能目录下创建文件**。

## 🚫 反例与禁止事项

以下操作绝对禁止，违反将导致程序崩溃、内存泄漏或功能异常：

| # | 禁止行为 | 后果 | 正确做法 |
|---|---------|------|---------|
| 1 | **在非 UI 线程操作 UI 元素** | 程序崩溃 | 用 `xc.UI()` 或 `xc.Auto()` 包裹 UI 操作 |
| 2 | **忘记调用 `Redraw` 就认为界面已更新** | 界面不刷新 | 修改元素后必须手动调用 `Redraw(false)`；列表修改数据后需先 `RefreshRow` 或 `RefreshData` 或 `RefreshDataHeader` 再 `Redraw` |
| 3 | **不创建数据适配器就直接使用 List/Tree/ListBox/ListView/ComboBox** | 运行时错误 | 创建对象后需调用 `CreateAdapter()`（参考 `references/Elements that require creating a data adapter.md`） |
| 4 | **IStream 对象用完后不释放** | 内存泄漏 | 不再使用时调用 `Release()`，无论传参还是返回值 |
| 5 | **WebView COM 对象用完后不释放** | 内存泄漏（COM 对象不被 Go GC 回收） | 手动调用 `Release()`；例外：`WebView2_2`~`WebView2_28` 等内部变量由 `Close()` 自动释放 |
| 6 | **将炫彩句柄当作 Windows 真实句柄** | 功能异常 | 用 `GetHWND()` 获取真实窗口句柄（`uintptr` 类型） |
| 7 | **凭模型记忆回答 API 细节，跳过源码检索** | 回答错误 | 必须用 `search.py` 检索 + `read` 确认后再回答 |
| 8 | **将生成的文件放到 `source/` 或本技能目录下** | 污染源码 | 创建到用户的工作目录中 |

## 源码初始化与更新

本技能不包含 `source/` 目录，首次使用或需要更新源码时，请执行以下操作。

### 自动下载源码

在技能根目录执行以下命令，自动下载 `xcgui` 和 `xcgui-example` 源码到 `source/` 目录：

```bash
python scripts/download.py
```

如果下载失败py脚本输出结果会给出下载链接的。

### 下载失败？手动下载

如果自动下载失败，提醒用户手动下载以下两个仓库的 ZIP 并解压到 `source/` 目录(下载地址会在py脚本输出结果中提供的)：

1. **xcgui 源码**：
   - 解压后重命名文件夹为 `xcgui`

2. **xcgui-example 示例**：
   - 解压后重命名文件夹为 `xcgui-example`

最终 `source/` 目录结构应如下：

```
source/
├── xcgui/           # 主库源码
└── xcgui-example/   # 示例代码
```

### 更新源码

当 xcgui 库有更新时，发出**"更新 xcgui 源码"**或**"重新下载源码"**指令即可重新执行 `python scripts/download.py` 下载最新源码。

---

## 信息检索工作流

收到任何 xcgui 问题时，**必须使用 `scripts/search.py` 搜索工具**按以下步骤主动检索源码：

### Step 0：检查前置条件

🔴 **CHECKPOINT**: 收到 xcgui 问题时，必须先确认 `source/` 目录存在（如不存在则执行 `python scripts/download.py`），然后至少执行一次 `search.py` 检索。不可跳过此步骤直接凭记忆回答。

### Step 1：确定搜索类型

根据问题类型，选择对应的搜索命令：

| 问题类型 | 使用命令 | 说明 |
|---------|---------|------|
| 查函数定义和注释 | `python scripts/search.py func <关键词>` | 会显示完整函数定义和注释 |
| 查常量定义和注释 | `python scripts/search.py const <关键词>` | 会显示完整常量定义和注释 |
| 查事件定义和注释 | `python scripts/search.py event <关键词>` | 会显示完整函数定义和注释 |
| 查类型/结构体定义和字段 | `python scripts/search.py type <关键词>` | 会显示类型注释、定义及字段块 (struct/interface) |
| 找示例参考 | `python scripts/search.py example <关键词>` | 搜 xcgui-example/ 全部示例 |
| 根据示例名或包注释精准找示例 | `python scripts/search.py example_name <keyword>` | 会更精准 |
| 不知道有什么元素对象 | `python scripts/search.py list widgets` | 列出所有可用元素对象和描述 |
| 不知道有什么窗口对象 | `python scripts/search.py list windows` | 列出所有窗口对象和描述 |
| 查看对象的所有事件 | `python scripts/search.py list events <对象名>` | 含继承链上的所有事件函数名 (含描述) |
| 查看对象的所有方法 | `python scripts/search.py list funcs <对象名>` | 含继承链上的所有方法名(含事件) |
| 了解项目结构 | `python scripts/search.py list packages` | 列出所有包和文件数 (含描述) |
| 查看所有示例 | `python scripts/search.py list examples` | 列出所有示例 (含描述) |
| 不知道包里有什么对象 | `python scripts/search.py list objects <包名>` | 列出包内所有公开对象 (含描述) |
| 不知道包里有什么非对象函数, 比如构造函数 | `python scripts/search.py list pkg_funcs <包名>` | 列出包内所有公开的包级函数（非方法，无接收者） |

> **关键词规则**：用 `/` 分割多个关键词，不区分大小写, 多个关键词时只会列出同时满足多个关键词的结果, 而不是`或`的意思；含中文时触发注释搜索。`list funcs` / `list events` 默认不含 `Event` 前缀函数（edge包除外, 因为edge包事件都是以Event开头的），末尾加 `all` 参数可全部列出。

### Step 2：阅读确认

搜索到候选后，用 `read` 工具打开目标文件（路径与行号已在搜索结果中给出），确认：
- 完整函数签名（多行参数、返回值类型）
- 中文注释（`// 函数_描述` 和参数说明）
- 事件回调的完整签名

### Step 3：回答

🔴 **CHECKPOINT**: 检索完毕。确认所有 API 引用均来自 `source/` 下的源码文件，附带了文件路径和行号，未使用模型预训练知识。

基于源码内容组织回答，附上相对文件路径和行号。

附上是基于什么版本的 xcgui 源码来回答的, 本地的 xcgui 源码版本号可在 `source/xcgui/README.md` 中找到, 可使用 `release-(\d+\.\d+\.\d+)` 正则表达式提取出该版本号, 会得到 `1.4.0` 这样的版本号。

## 故障处理与降级策略

当遇到以下场景时，按指定路径处理，不可静默失败。每个场景提供三段式方案：触发条件 → 一线修复 → 兜底方案。

### 1. 源码下载失败

| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|----------|-----------|
| `python scripts/download.py` 报错 | 检查 Python 是否安装（需 ≥3.7），重试 | 从 py 脚本输出中获取下载链接，告知用户手动下载 |
| 下载后 `source/` 目录为空 | 检查网络连接，重试一次 | 告知用户手动下载 ZIP 并解压到 `source/` 目录 |
| `source/` 存在但缺子目录（如只有 xcgui 无 xcgui-example） | 重新执行 download.py | 告知用户缺失的具体目录名，请求手动补充 |

### 2. 源码搜索失败

| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|----------|-----------|
| `search.py func/const/event <kw>` 无结果 | 更换关键词：中英切换、大小写变体、缩写与全称互换 | 使用 `grep -rn "关键词" source/` 直接搜索源文件(用其它搜索工具也可以) |
| `search.py` 本身报错（Python 异常） | 检查 Python 版本、确认脚本文件未损坏 | 回退到 grep 手动搜索(用其它搜索工具也可以)，告知用户 search.py 异常 |
| 搜索到结果但不确定含义 | 用 `read` 工具打开目标文件确认完整签名和注释 | 搜索同名示例（`search.py example <kw>`）交叉验证 |

### 3. 版本号提取失败

| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|----------|-----------|
| `source/xcgui/README.md` 不存在 | 执行 `python scripts/download.py` 下载源码 | 告知用户无法确定版本，建议重新下载 |
| README.md 中未匹配到版本号 | 手动打开文件确认格式是否变化 | 回复时标注"版本号未知"，不影响代码正确性 |

### 4. WebView2 运行时缺失

| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|----------|-----------|
| 程序提示"请安装 WebView2 运行时" | 代码中调用 `edge.DownloadWebView2()` 下载小型安装引导程序 | 告知用户手动前往 Microsoft 官网下载安装 |
| 本机版本低于库要求版本 | 打印警告但仍尝试运行（低版本通常向后兼容） | 告知用户升级 WebView2 运行时以获取最佳兼容性 |

## 事件

- xcgui的一个事件类型可以注册多个回调处理函数，执行顺序为先执行最后注册的回调函数，最后执行第一个注册的回调函数，当你想拦截当前事件或不想向后传递，只需要在回调函数中设置参数 `*pbHandled=true` 即可。
- 由于使用的是 `syscall.NewCallback` 创建的事件回调函数，该方法限制只能创建 2000 个左右的回调函数，超过就会 panic。当使用 `Event` 类型的函数来注册事件且回调函数是匿名函数时，每次都会创建 1 个新的回调函数，如果不加以控制，就可能会超过 2000 个。而 `AddEvent` 类型的函数会复用创建好的回调函数，可以任意使用匿名函数作为事件回调函数，无需担心超过 2000 个的限制。
- 以`AddEvent`开头的事件的最后一个参数 `allowAddingMultiple` 允许添加多个回调函数, 不填默认为 true, 如果为 fasle 则是覆盖。
- 优先使用`AddEvent`开头的事件, `edge`包的事件除外, 因为它里面只有`Event`开头的事件, `edge`包以`Event`开头的事件和`AddEvent`类型的事件实现原理是一致的, 可以看作是`AddEvent`类型的, 只是函数名不以Add开头, 它的最后一个参数也是 `allowAddingMultiple` 。

## 最佳实践

- 因为窗口默认是有四边框的, 而且直接在窗口上的元素, 其坐标是相对于整个窗口的, 坐标(0,0)是标题栏左上角, 所以用绝对坐标创建元素/绘制等操作前先使用 `GetBorderSize` 获取边框大小, Top即为标题栏高度, 得知边框大小后可避免将元素创建到边框或标题上; 可用窗口对象的 `SetBorderSize` 设置边框大小, 因为默认边框很宽, 不美观。
- 在动态添加布局元素后可调用其父元素的 `AdjustLayout().Redraw()` 以刷新布局, 防止布局错乱。
- 使用 WebView 时, 如果想让 html 中的元素(比如标题栏)可用鼠标拖动来移动窗口位置, 应该在创建 WebView 的 `WebViewOptions` 中启用 `AppDrag`, 然后给该元素添加 CSS: `app-region: drag`, 建议仅用于标题栏, 因为启用后会把该元素区域变为窗口非客户区, 在上面鼠标右键会弹出标题栏上才有的系统菜单; 如果不想让某个元素被拖动来移动窗口(比如标题栏中的控制按钮), 可以给它添加 `app-region: no-drag`; 如果除了标题栏之外还想有其它的可拖动区域且不使其变为非客户区, 可查看 `xcgui-example/webview/RoundedShadowWindow` 例子, 该例子中还有完美无锯齿的圆角阴影设置方法。

## 常见问题

> 核心反例（崩溃/泄漏/刷新等）请参见上方 [🚫 反例与禁止事项](#-反例与禁止事项)。

- Go 模块路径是 `github.com/twgh/xcgui`，最小 Go 版本 1.18。
- `Menu` 和 Shape* 等形状组件不继承 `Element`, 不要误认为继承。
- Shape* 等形状组件没有事件, 需要交互反馈可以用 Button / Element 等元素替代。
- List 表头数据适配器类型是 AdMap，不是 AdTable。
- ComboBox 的下拉列表是 ListView, 可以在 `AddEvent_Combobox_Popup_List` 事件中获取到其句柄, 然后进行样式美化。
- `Edit.AddText` 是「在当前插入点插入」，不是追加到末尾, 使用 `MoveEnd` 可把插入点移到末尾。
- 背景管理器的 `AddBkFill`/`AddBkBorder` 等添加背景的 API 是追加式, 没有「替换某个状态的背景」的 API，同名状态可多次追加, 因此**需要改底色时不能重复 Add**，必须先清空再添加，否则累积到 20 个会报错并终止程序。
- 背景管理器的 `AddBkFill` 等添加背景的 API 中的 id 参数指定后, 可使用 `_bkobj := bkm.GetObjectObj(id)` 获取到背景对象, 然后就可以操作该背景对象进行更多的美化。
- 布局项（位置/显隐）的变更不会自动生效：`LayoutItem_SetPosition`、`LayoutItem_SetWidth`、`Show` 等调用只是把变更写入布局属性，还需调用父容器的 `AdjustLayout()` 重排（通常紧跟 `Redraw()` 重绘），变更才会反映到界面上。
- 模态窗口 `DoModal` 返回后窗口及全部子元素已销毁, 再访问子元素句柄会报无效, 先取值再 `EndModal`。
- 当程序使用 `app.New()` 参数为 true 时, 此时为 Direct2D 渲染模式, 为 false 时为 GDI+ 渲染模式。
- 生成颜色除了使用 `xc.RGBA(r, g, b, a byte) uint32` 外, 还可使用 `xc.HexRGB2RGBA(str string, a byte) uint32` 将常见的 Web/CSS 十六进制颜色转换到炫彩界面库使用的颜色。
- xcgui 窗口的 Handle(`int`类型) 只是内部维护的序号, 真实句柄应该用 `GetHWND` 方法来获取，是 `uintptr` 类型的，可用于 windows api。**注意**: 像 `XWnd_GetFocusEle(hWindow int)` 类似函数的参数要传 `int` 类型的 Handle, 不要传 `int(w.GetHWND())`; 像 `XC_hWindowFromHWnd(hWnd uintptr)` 这样的要传 `uintptr` 类型的窗口真实句柄。
- 如果文本中出现炫彩, 它是炫彩界面库的简称, 也就是xcgui, 例如`炫彩窗口`, 它的意思是`xcgui window`。

## 最简单标准代码

```go
package main

import (
    "github.com/twgh/xcgui/app"
    "github.com/twgh/xcgui/window"
    "github.com/twgh/xcgui/widget"
    "github.com/twgh/xcgui/xcc"
)

func main() {
    app.InitOrExit()                          // 1. 初始化
    a := app.New()                         // 2. 创建 App 实例
    a.EnableAutoDPI().EnableDPI()      // 3. 启用 DPI

    w := window.New(0, 0, 600, 400, "标题", 0, xcc.Window_Style_Default) // 4. 创建窗口

    // 5. 创建控件并绑定事件
    btn := widget.NewButton(10, 40, 100, 30, "按钮", w.Handle)
    btn.AddEvent_BnClick(func(hEle int, pbHandled *bool) int {
        w.MessageBox("提示", "你点击了按钮", xcc.MessageBox_Flag_Ok, xcc.Window_Style_Modal)
        return 0
    })

    w.Show()                               // 6. 显示窗口
    a.Run()                                    // 7. 消息循环
    a.Exit()                                   // 8. 退出
}
```

## 给程序添加 Windows 资源 / 版本信息 / 程序清单

阅读 `source/xcgui-example/Basic/AutoDpi/给程序添加图标，版本信息，程序清单.md`, 根据指引安装 xc 命令行工具, 要查看其所有功能可执行 `xc -h`。

## 编译程序的命令

```bash
go build -ldflags="-s -w -H windowsgui" -trimpath
```

## 项模板

List, ListView, ListBox, Tree 元素中有项模板, 每一项都是从项模板创建的, 默认项模板可查看 `references/itemTemplate/` 下的 xml 文件以了解项中有什么元素, 以便于在项模板创建完成事件中修改项模板中的元素样式等。

相关原理图解: `references/itemTemplate/列表项模板复用机制.png`(启用项模板复用可调用 `EnableTemplateReuse(true)`), `references/itemTemplate/列表-项模板-数据适配器-关系图.png`。

## XCGUI源码目录地图

> `xcgui` 库中所有包的导入路径均以 `github.com/twgh/xcgui/` 为前缀，例如 `github.com/twgh/xcgui/xc`、`github.com/twgh/xcgui/app`。下文目录树中的目录名直接拼接此前缀即可得到完整导入路径。

```
source/
└── xcgui/                    # 主库源码
   ├── xc/                   # 底层 C API 绑定 — 所有 X* 函数, 所有炫彩struct
   ├── xcc/                  # 常量定义
   │   ├── xcconst.go        # 核心常量
   │   ├── combinedstate.go  # 组合状态常量
   │   ├── elementevent.go   # 元素事件常量
   │   ├── windowevent.go    # 窗口事件常量
   │   └── xml.go            # XML 相关常量
   ├── widget/               # 控件封装 — Button, Edit, List, Table, Tree, ...
   ├── window/               # 窗口封装
   │   ├── window.go         # 基础窗口
   │   ├── framewindow.go    # 框架窗口
   │   ├── modalwindow.go    # 模态窗口
   │   ├── floatwindow.go    # 浮动窗口
   │   ├── windowbase.go     # 窗口基类
   │   └── trayicon.go       # 托盘图标
   ├── ani/                  # 动画高级封装
   ├── ease/                 # 缓动函数
   ├── svg/                  # SVG 处理
   ├── drawx/                # 图形绘制
   ├── font/                 # 字体管理
   ├── imagex/               # 图片处理
   ├── res/                  # 资源管理
   ├── tf/                   # 便捷创建窗口方便测试
   ├── edge/                 # WebView2 封装 — ICoreWebView2* 接口
   │   └── webviewloader/    # WebView2 运行时加载
   ├── app/                  # 应用生命周期,炫彩全局API
   ├── common/               # 公共函数
   ├── adapter/              # 数据适配器
   ├── bkmanager/            # 背景管理器
   ├── bkobj/                # 背景对象
   ├── objectbase/           # 对象基类
   ├── wapi/                 # Windows API 封装
   │   ├── wnd/              # 基于wapi封装窗口操作
   │   └── wutil/            # 基于wapi封装工具函数
   ├── tmpl/                 # 列表项模板
   └── README.md             # xcgui 介绍
```

## xcgui 源码的编码规范速查

此文件指 xcgui 源码自身的编码规范, 不代表编写代码需遵循该规范, 可读取 `references/XCGUI Programming Standards.md` 文件
