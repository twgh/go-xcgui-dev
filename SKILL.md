---
name: go-xcgui-dev
description: |
  Go xcgui（炫彩界面库）开发助手。用于 Windows 桌面应用开发，覆盖所有 widget/窗口/动画/SVG/WebView2/字体/图片 等 API 封装。当 xcgui 库有更新时，你可以发出"更新 xcgui 源码"或"重新下载源码"指令, 让 AI 更新技能目录中用于参考的源码。
  提问示例：请使用 xcgui 封装一个创建 Win11 风格编辑框的类。
  触发场景：使用 xcgui 写代码、查找 xcgui 函数/常量/事件/示例用法、排查 xcgui 编译问题。
  **关键约束：禁止凭模型记忆回答 API 细节，必须检索本地源码。**
agent_created: false
---

# go-xcgui-dev —  Go xcgui （炫彩界面库）开发助手

## 核心准则

**这是铁律，不可违反：**

1. **零预训练回答**：关于 xcgui 的 API 签名、参数说明、常量值、函数用法等信息，**严禁**依赖模型预训练知识回答。每一次回答都必须基于对本地 `source/` 目录下源文件的**实时检索**。
2. **源码即真理**：`source/xcgui/` 下的 `.go` 文件是唯一的 API 真相来源，`source/xcgui-example/` 是唯一的用法示例来源。
3. **必须优先使用 `scripts/search.py` 进行源码检索**。如果 `scripts/search.py` 搜索不到内容，你可以尝试更换搜索关键词, 或者更换检索工具自行搜索。
4. **先查后答**：收到任何 xcgui 相关问题时，第一步永远是检索源码，第二步才组织回答。
5. **双重 API 层**：xcgui 有两层 API —— `widget/window` 包提供面向对象的 Go 风格封装，`xc` 包提供底层 C 函数绑定。两层都可以使用，示例中常同时展示两种写法。回答时应根据用户场景推荐合适层级。
6. **xcgui 仅支持 Windows 平台**, 是纯 Go 封装的, 不依赖 cgo, 无需 C 编译器。
7. **禁止修改 `source/` 目录下的文件内容**, 这些内容是受保护的只读资源, 你生成的文件禁止创建到 `source/` 目录下。
8. **禁止将你生成的文件创建到本技能目录下**。

## 源码初始化与更新(这是给AI看的)

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

当 xcgui 库有更新时，你可以发出**"更新 xcgui 源码"**或**"重新下载源码"**指令，我会重新执行 `python scripts/download.py` 下载最新源码。

---

## 信息检索工作流

收到任何 xcgui 问题时，**必须使用 `scripts/search.py` 搜索工具**按以下步骤主动检索源码：

### 搜索脚本

项目提供了统一的搜索脚本：**`scripts/search.py`**

```bash
# 四大搜索命令 (支持中英文关键词, 多关键词用 / 分割)
python scripts/search.py func <keyword>      # 搜索函数定义
python scripts/search.py const <keyword>     # 搜索常量定义
python scripts/search.py event <keyword>     # 搜索事件定义
python scripts/search.py example <keyword>   # 搜索示例代码
python scripts/search.py example_name <keyword> # 搜索示例名或包注释

# 列表/概览命令
python scripts/search.py list widgets        # 列出 widget 包所有公开对象
python scripts/search.py list windows        # 列出 window 包所有公开对象
python scripts/search.py list packages       # 列出所有源码包
python scripts/search.py list examples       # 列出所有示例
python scripts/search.py list events <对象名>  # 列出指定对象的所有事件 (含继承链, 含描述)
python scripts/search.py list funcs <对象名>   # 列出指定对象的所有方法 (含事件, 含继承链, 含描述)
python scripts/search.py list objects <包名>    # 列出指定包的所有公开对象 (含描述)
```

**关键词规则**：

- 用 `/` 分割多个关键词，会同时匹配所有关键词, 支持中英文, 不区分大小写
- 关键词除了可以搜索函数/常量/事件定义外, 还可以搜索它们的注释, 在关键词含中文时触发
- `list funcs <对象名>` 和 `list events <对象名>` 命令默认是不会列出以 `Event` 开头的函数的, 除非在最后面再加个 `all` 参数, 一般不需要 `Event` 开头的函数, 这两个命令都会列出 `AddEvent` 开头的函数, 这种事件添加方式更常用
- `drawx` 包内的对象是 `Draw`, `imagex` 包内的对象是 `Image` 和 `ImageSrc`, 使用 `list funcs <对象名>` 搜索对象函数时不要将对象写错为 `Drawx` 和 `Imagex` 等错误对象名

##### 示例

```python
python scripts/search.py func button/gettext       # 搜索函数名关键词
python scripts/search.py func 窗口/居中             # 用中文搜索函数注释
python scripts/search.py const button/check        # 搜索常量关键词
python scripts/search.py const 窗口/最小化          # 用中文搜索常量注释
python scripts/search.py event tree/select         # 搜索事件函数名关键词
python scripts/search.py event 窗口/鼠标光标        # 搜索事件函数中文注释关键词
python scripts/search.py example event/TabBar      # 搜索示例内容关键词
python scripts/search.py example 按钮/选中/事件     # 搜索示例内容关键词
python scripts/search.py example_name 美化/编辑框   # 搜索示例包注释
python scripts/search.py example_name draw/button  # 搜索示例名
python scripts/search.py list widgets              # 列出 widget 包所有公开对象
python scripts/search.py list windows              # 列出 window 包所有公开对象
python scripts/search.py list packages             # 列出所有源码包
python scripts/search.py list examples             # 列出所有示例
python scripts/search.py list events button        # 列出 button 的所有事件
python scripts/search.py list funcs button         # 列出 button 的所有方法
python scripts/search.py list objects window       # 列出 window 包所有公开对象
```

### Step 1：确定搜索类型

根据问题类型，选择对应的搜索命令：

| 问题类型 | 使用命令 | 说明 |
|---------|---------|------|
| 查函数定义和注释 | `python scripts/search.py func <关键词>` | 会显示完整函数定义和注释 |
| 查常量定义和注释 | `python scripts/search.py const <关键词>` | 会显示完整常量定义和注释 |
| 查事件定义和注释 | `python scripts/search.py event <关键词>` | 会显示完整函数定义和注释 |
| 找示例参考 | `python scripts/search.py example <关键词>` | 搜 xcgui-example/ 全部示例 |
| 根据示例名或包注释精准找示例 | `python scripts/search.py example_name <keyword>` | 会更精准 |
| 不知道有什么元素对象 | `python scripts/search.py list widgets` | 列出所有可用元素对象和描述 |
| 不知道有什么窗口对象 | `python scripts/search.py list windows` | 列出所有窗口对象和描述 |
| 查看对象的所有事件 | `python scripts/search.py list events <对象名>` | 含继承链上的所有事件函数名 (含描述) |
| 查看对象的所有方法 | `python scripts/search.py list funcs <对象名>` | 含继承链上的所有方法名(含事件) |
| 了解项目结构 | `python scripts/search.py list packages` | 列出所有包和文件数 (含描述) |
| 查看所有示例 | `python scripts/search.py list examples` | 列出所有示例 (含描述) |
| 不知道包里有什么对象 | `python scripts/search.py list objects <包名>` | 列出包内所有公开对象 (含描述) |

### Step 2：阅读确认

搜索到候选后，用 `read` 工具打开目标文件（路径与行号已在搜索结果中给出），确认：
- 完整函数签名（多行参数、返回值类型）
- 中文注释（`// 函数_描述` 和参数说明）
- 事件回调的完整签名

### Step 3：回答

基于源码内容组织回答，附上相对文件路径和行号。

附上是基于什么版本的 xcgui 源码来回答的, 本地的 xcgui 源码版本号可在 `source/xcgui/README.md` 中找到, 可使用 `release-(\d+\.\d+\.\d+)` 正则表达式提取出该版本号, 会得到 `1.4.0` 这样的版本号。

## 常见问题

- Go 模块路径是 `github.com/twgh/xcgui`，最小 Go 版本 1.18
- **在非 UI 线程操作 UI 会导致程序崩溃**, 对界面库元素的修改操作必须在 UI 线程执行，元素并不是线程安全的, 可使用 `xc.UI` 函数在UI线程执行操作, `xc.Auto` 函数是会自动判断是否在 UI 线程
- **修改 Webview 的代码要在 UI 线程执行, 就是与视觉相关的方法**, 可使用 `xc.UI` 函数在 UI 线程执行操作, `xc.Auto` 函数是会自动判断是否在 UI 线程
- **炫彩界面库元素默认是不会自动刷新的**, 所以你修改元素内容或大小等操作后, 需要手动调用该元素的 `Redraw` 方法, 参数一般填 `false` 即可。手动控制刷新性能会更好, 例如修改了列表多行内容, 最后只需要刷新一次。列表需要注意的是修改了数据后要调用 `RefreshRow` 或 `RefreshData` 然后再调用 `Redraw` 
- 炫彩元素的句柄只是界面库内部维护的序号而已, 并不是 windows 系统中真实的句柄, 比如说你输出窗口的 Handle, 它可能是 1, 炫彩窗口的真实句柄应该用 `GetHWND` 函数来获取，是 `uintptr` 类型的，可以用于 windows api
- 在动态添加布局元素后可调用 `w.AdjustLayout().Redraw(false)` 以刷新布局
- `IStream` 对象不再使用了需要调用 `Release` 释放, 不管是你传参的还是函数返回的, 不再使用后都要释放, 以防内存泄漏
- 获取的 WebView 相关的 com 对象不再使用了需要释放, 以防内存泄漏, 因为获取到的是 com 对象, gc回收了go对象, 但 com 对象不会被go gc回收, 所以需要手动调用 `Release` 释放, 例外情况是由于 `WebView.WebView2_2` 到 `WebView.WebView2_28` 是常用的对象变量(WebView2_*, 序号以后可能会更大), 这些内部声明好的对象变量会在调用 `WebView.Close` 时自动释放, 窗口关闭时会自动调用的, 你查看 `WebView.Close` 的源码可以看到释放的代码, 所以这些不需要你手动释放
- 当程序使用 `app.New()` 参数为 true 时, 此时为 Direct2D 渲染模式, 为 false 时为 GDI+ 渲染模式
- 生成颜色除了使用 `xc.RGBA` 函数外(函数定义为`func RGBA(r, g, b, a byte) uint32`), 还可以使用 `xc.HexRGB2RGBA` (函数定义为`func HexRGB2RGBA(str string, a byte) uint32`)将常见的 Web/CSS 十六进制颜色转换到炫彩界面库使用的颜色

## 需要创建数据适配器的元素

List, ListView, ListBox, Tree, CombBox, 不创建数据适配器就会报错, 无法存储数据, 怎么创建可读取 `references/Elements that require creating a data adapter.md`

## 源码目录地图

所有源码位于 `source/` 下，分两大目录：

```
source/
├── xcgui/                    # 主库源码 (525 .go 文件)
│   ├── xc/                   # 底层 C API 绑定 (77 文件) — 所有 X* 函数
│   │   └── dll/              # DLL 加载逻辑
│   ├── xcc/                  # 常量定义 (6 文件)
│   │   ├── xcconst.go        # 核心常量
│   │   ├── combinedstate.go  # 组合状态常量
│   │   ├── elementevent.go   # 元素事件常量
│   │   ├── windowevent.go    # 窗口事件常量
│   │   └── xml.go            # XML 相关常量
│   ├── widget/               # 控件封装 (42 文件) — Button, Edit, List, Table, Tree, ...
│   ├── window/               # 窗口封装 (8 文件)
│   │   ├── window.go         # 基础窗口
│   │   ├── framewindow.go    # 框架窗口
│   │   ├── modalwindow.go    # 模态窗口
│   │   ├── floatwindow.go    # 浮动窗口
│   │   ├── windowbase.go     # 窗口基类
│   │   └── trayicon.go       # 托盘图标
│   ├── ani/                  # 动画高级封装 (7 文件)
│   ├── ease/                 # 缓动函数 (2 文件)
│   ├── svg/                  # SVG 处理 (3 文件)
│   ├── drawx/                # 绘制扩展 (2 文件)
│   ├── font/                 # 字体管理 (2 文件)
│   ├── imagex/               # 图片处理 (5 文件)
│   ├── res/                  # 资源管理 (2 文件)
│   ├── tf/                   # 模板文件 (2 文件)
│   ├── edge/                 # WebView2 封装 (292 文件) — ICoreWebView2* 接口
│   │   └── webviewloader/    # WebView2 运行时加载
│   ├── app/                  # 应用生命周期 (12 文件)
│   ├── common/               # 公共工具 (3 文件)
│   ├── adapter/              # 数据适配器 (7 文件)
│   ├── bkmanager/            # 背景管理器 (3 文件)
│   ├── bkobj/                # 背景对象 (2 文件)
│   ├── objectbase/           # 对象基类 (4 文件)
│   ├── wapi/                 # Windows API 封装 (20 文件)
│   │   ├── wnd/              # 窗口子类化
│   │   └── wutil/            # 工具函数
│   ├── tmpl/                 # 模板 (3 文件)
│   └── README.md             # xcgui 介绍, 里面有每个包都有什么对象的说明
│
└── xcgui-example/            # 示例代码 (84 .go 文件)
    ├── Basic/                # 基础示例 (42 个)
    │   ├── SimpleWindow/     # 简单窗口 (入门必看)
    │   ├── ButtonImage/      # 图片按钮
    │   ├── ButtonSvg/        # SVG 按钮
    │   ├── FrameWindow/      # 框架窗口
    │   ├── ModalWindow/      # 模态窗口
    │   ├── List/List2/       # 列表控件
    │   ├── ListView/         # 列表视图
    │   ├── TabBar/           # 选项卡
    │   ├── ToolBar/          # 工具栏
    │   ├── ComboBox/         # 下拉框
    │   ├── Edit/             # 编辑框
    │   ├── Tree/             # 树形控件
    │   ├── Menu/MenuBar/     # 菜单
    │   ├── ProgressBar/      # 进度条
    │   ├── SliderBar/        # 滑动条
    │   ├── DateTime/         # 日期时间
    │   ├── MonthCal/         # 月历
    │   ├── ScrollBar/        # 滚动条
    │   ├── Gif/              # GIF 动画
    │   ├── Timer/            # 定时器
    │   ├── ShapePicture/     # 形状图片
    │   ├── ShapeText/        # 形状文本
    │   ├── CheckButton/      # 复选框按钮
    │   ├── RadioButton/      # 单选按钮
    │   ├── ListBox/          # 列表框
    │   ├── ChooseColor/      # 颜色选择
    │   ├── OpenFile/         # 文件打开
    │   ├── DropFiles/        # 拖放文件
    │   ├── ElementEvent/     # 元素事件
    │   ├── EventInterception/# 事件拦截
    │   ├── MultiWindow/      # 多窗口
    │   ├── SetDefaultFont/   # 设置默认字体
    │   ├── AutoDpi/          # 自适应 DPI
    │   ├── MemoryLoadImage/  # 内存加载图片
    │   ├── LoadLayoutFromString/ # 从字符串加载布局
    │   ├── MultithreadOperationUI/  # 多线程操作 UI
    │   ├── MultithreadOperationUI2/ # 多线程操作 UI(2)
    │   ├── ThreadOperationUI/    # 线程操作 UI
    │   ├── WindowBkColor/    # 窗口背景色
    │   └── uidesigner/       # UI 设计器示例
    │
    ├── Advanced/             # 高级示例 (26 个)
    │   ├── Animation/        # 动画特效大全 (最重要)
    │   ├── TabControl/       # 选项卡切换控制
    │   ├── SideNavigation/   # 侧边导航
    │   ├── SvgDraw/          # SVG 绘制
    │   ├── AudioPlayer/      # 音频播放器
    │   ├── Editor/           # 编辑器
    │   ├── TrayIcon/         # 系统托盘
    │   ├── TrayIcon2/        # 系统托盘(2)
    │   ├── VirtualTable1/    # 虚拟表格(1)
    │   ├── VirtualTable2/    # 虚拟表格(2)
    │   ├── Attach/           # 附加窗口
    │   ├── DebugInfo/        # 调试信息
    │   ├── DrawMenu/         # 自绘菜单
    │   ├── DrawRoundButton/  # 自绘圆角按钮
    │   ├── Ease_All/         # 缓动函数大全
    │   ├── Ease_Easy/        # 简易缓动
    │   ├── GoImage/          # Go 图片处理
    │   ├── HideTaskbarIcon/  # 隐藏任务栏图标
    │   ├── HideTaskbarIcon2/ # 隐藏任务栏图标(2)
    │   ├── HookKeyboard/     # 键盘钩子
    │   ├── HookMouse/        # 鼠标钩子
    │   ├── MouseCursor/      # 鼠标光标
    │   ├── RegisterHotKey/   # 注册热键
    │   ├── SendEvent/        # 发送事件
    │   ├── BeautifyEdit/     # 美化编辑框
    │   └── SetWindowIcon/    # 设置窗口图标
    │
    ├── webview/              # WebView2 示例 (14 个)
    │   ├── SimpleWebView/    # 简单 WebView
    │   ├── Chart/            # 图表
    │   ├── VueAndVite/       # Vue+Vite 集成
    │   ├── CalcMD5/          # JS-Go 互调
    │   ├── EmbedAssets/      # 嵌入资源
    │   ├── SharedBuffer/     # 共享缓冲区
    │   ├── CustomSchemeRegistration/ # 自定义协议
    │   ├── CreateByLayoutEle/ # 从布局元素创建
    │   ├── CreateByWindow/   # 从窗口创建
    │   ├── EnvironmentOptions/ # 环境选项
    │   ├── SaveMemory/       # 内存优化
    │   ├── RoundedShadowWindow/ # 圆角阴影窗口
    │   ├── AutomaticInstallWebView2Runtime/ # 自动安装 WebView2 运行时
    │   └── WebResourceRequestedEvent/ # 资源请求事件
    │
    └── HUMUI/                # 现代化 UI 示例 (2 个)
        ├── HouTai017/        # 后台管理
        └── YanZheng018/      # 验证码
```

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
    a := app.New(true)                         // 2. 创建 App 实例
    a.EnableAutoDPI(true).EnableDPI(true)      // 3. 启用 DPI

    w := window.New(0, 0, 600, 400, "标题", 0, xcc.Window_Style_Default) // 4. 创建窗口

    // 5. 创建控件并绑定事件
    btn := widget.NewButton(10, 10, 100, 30, "按钮", w.Handle)
    btn.AddEvent_BnClick(func(hEle int, pbHandled *bool) int {
        w.MessageBox("提示", "你点击了按钮", xcc.MessageBox_Flag_Ok, xcc.Window_Style_Modal)
        return 0
    })

    w.Show(true)                               // 6. 显示窗口
    a.Run()                                    // 7. 消息循环
    a.Exit()                                   // 8. 退出
}
```

## 常用包参考

| 包 | 用途 | 导入路径 |
|----|------|---------|
| `xc` | 底层 C API，所有以 `X` 开头的函数 | `github.com/twgh/xcgui/xc` |
| `xcc` | 所有炫彩常量和枚举 | `github.com/twgh/xcgui/xcc` |
| `widget` | 控件高级封装 | `github.com/twgh/xcgui/widget` |
| `window` | 窗口高级封装 | `github.com/twgh/xcgui/window` |
| `app` | 应用生命周期 | `github.com/twgh/xcgui/app` |
| `ani` | 动画高级封装 | `github.com/twgh/xcgui/ani` |
| `ease` | 缓动函数 | `github.com/twgh/xcgui/ease` |
| `svg` | SVG 加载处理 | `github.com/twgh/xcgui/svg` |
| `font` | 字体管理 | `github.com/twgh/xcgui/font` |
| `imagex` | 图片加载处理 | `github.com/twgh/xcgui/imagex` |
| `edge` | WebView2 完整封装 | `github.com/twgh/xcgui/edge` |
| `drawx` | 绘制辅助 | `github.com/twgh/xcgui/drawx` |
| `bkmanager` | 背景管理器 | `github.com/twgh/xcgui/bkmanager` |
| `bkobj` | 背景对象 | `github.com/twgh/xcgui/bkobj` |
| `adapter` | 数据适配器 | `github.com/twgh/xcgui/adapter` |
| `res` | 资源管理 | `github.com/twgh/xcgui/res` |
| `common` | 公共辅助函数 | `github.com/twgh/xcgui/common` |
| `wapi` | Windows API 封装 | `github.com/twgh/xcgui/wapi` |
| `wutil` | 使用 Windows API 封装常用函数 | `github.com/twgh/xcgui/wapi/wutil` |
| `wnd` | 使用 Windows API 封装窗口操作函数 | `github.com/twgh/xcgui/wapi/wnd` |

## 示例快速查找表

如果想要快速查找常用示例, 可读取 `references/Example Quick Search Table.md` 文件

如果找不到对应示例，可用 `python scripts/search.py example <关键词>` 搜索

## xcgui 源码的编码规范速查

这个指的是 xcgui 源码自身的编码规范, 不代表你写代码要遵循这个规范, 可读取 `references/XCGUI Programming Standards.md` 文件
