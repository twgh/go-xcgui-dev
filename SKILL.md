---
name: go-xcgui-dev
description: |
  xcgui（炫彩界面库）Go 绑定开发助手。用于 Windows 桌面应用开发，覆盖所有 widget/窗口/动画/SVG/WebView2 等 API 封装。
  触发场景：使用 xcgui 写代码、封装新 API、查找 xcgui 函数/常量/事件用法、排查 xcgui 编译/运行时问题、参考示例项目结构、生成新控件封装代码。
  **关键约束：禁止凭模型记忆回答 API 细节，必须检索本地源码。**
agent_created: false
---

# go-xcgui-dev — xcgui 炫彩界面库 Go 绑定开发助手

## 核心准则

**这是铁律，不可违反：**

1. **零预训练回答**：关于 xcgui 的 API 签名、参数说明、常量值、函数用法等信息，**严禁**依赖模型预训练知识回答。每一次回答都必须基于对本地 `source/` 目录下源文件的**实时检索**。
2. **源码即真理**：`source/xcgui/` 下的 `.go` 文件是唯一的 API 真相来源，`source/xcgui-example/` 是唯一的用法示例来源。
3. **先查后答**：收到任何 xcgui 相关问题时，第一步永远是检索源码，第二步才组织回答。
4. **双重 API 层**：xcgui 有两层 API —— `widget/window` 包提供面向对象的 Go 风格封装，`xc` 包提供底层 C 函数绑定。两层都可以使用，示例中常同时展示两种写法。回答时应根据用户场景推荐合适层级。
5. **xcgui 仅支持 Windows 平台**，不能使用 grep/ripgrep 等 Linux 命令行工具搜索源码。**必须使用 `scripts/search.py` 进行源码检索**。如果 `scripts/search.py` 搜索不到内容，你可以尝试更换搜索关键词。

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

# 列表/概览命令
python scripts/search.py list widgets        # 列出 widget 包所有公开对象
python scripts/search.py list windows        # 列出 window 包所有公开对象
python scripts/search.py list packages       # 列出所有源码包
python scripts/search.py list examples       # 列出所有示例
python scripts/search.py list events <对象名>  # 列出指定对象的所有事件 (含继承链)
python scripts/search.py list funcs <对象名>   # 列出指定对象的所有方法 (含继承链)
python scripts/search.py list events         # 列出所有事件函数名
```

**关键词规则**：

- 用 `/` 分割多个关键词，会同时匹配所有关键词, 支持中英文, 不区分大小写
- 关键词除了可以搜索函数/常量/事件定义外, 还可以搜索它们的注释, 关键词含中文时触发

##### 示例

```python
python scripts/search.py func Center               # 搜索函数名关键词 (单个关键词)
python scripts/search.py func button/gettext       # 搜索函数名关键词 (多个关键词用 / 分割)
python scripts/search.py func 最大化                # 用中文注释搜索函数 (单个关键词)
python scripts/search.py func 窗口/居中             # 用中文注释搜索函数 (多个关键词用 / 分割)
python scripts/search.py const Window_Style        # 搜索常量关键词 (单个关键词)
python scripts/search.py const button/check        # 搜索常量关键词 (多个关键词用 / 分割)
python scripts/search.py const 阴影窗口             # 用中文注释搜索常量 (单个关键词)
python scripts/search.py const 窗口/最小化          # 用中文注释搜索常量 (多个关键词用 / 分割)
python scripts/search.py event BnClick             # 搜索事件函数名关键词 (单个关键词)
python scripts/search.py event tree/select         # 搜索事件函数名关键词 (多个关键词用 / 分割)
python scripts/search.py event 窗口消息过程         # 搜索事件函数中文注释关键词 (单个关键词)
python scripts/search.py event 窗口/鼠标光标        # 搜索事件函数中文注释关键词 (多个关键词用 / 分割)
python scripts/search.py example TabBar            # 搜索示例关键词 (单个关键词)
python scripts/search.py example event/TabBar      # 搜索示例关键词 (多个关键词用 / 分割)
python scripts/search.py example 按钮/选中/事件     # 搜索示例关键词 (多个关键词用 / 分割)
python scripts/search.py list widgets              # 列出 widget 包所有公开对象
python scripts/search.py list windows              # 列出 window 包所有公开对象
python scripts/search.py list packages             # 列出所有源码包
python scripts/search.py list examples             # 列出所有示例
python scripts/search.py list events button        # 列出指定对象所有事件函数名
python scripts/search.py list funcs button         # 列出指定对象所有方法名
python scripts/search.py list events               # 列出所有事件函数名(这个可能没什么大用)
```

### Step 1：确定搜索类型

根据问题类型，选择对应的搜索命令：

| 问题类型 | 使用命令 | 说明 |
|---------|---------|------|
| 查函数定义和注释 | `python scripts/search.py func <关键词>` | 会显示完整函数定义和注释 |
| 查常量定义和注释 | `python scripts/search.py const <关键词>` | 会显示完整常量定义和注释 |
| 查事件定义和注释 | `python scripts/search.py event <关键词>` | 会显示完整函数定义和注释 |
| 找示例参考 | `python scripts/search.py example <关键词>` | 搜 xcgui-example/ 全部示例 |
| 不知道有什么元素对象 | `python scripts/search.py list widgets` | 列出所有可用元素对象和描述 |
| 不知道有什么窗口对象 | `python scripts/search.py list windows` | 列出所有窗口对象和描述 |
| 查看对象的所有事件 | `python scripts/search.py list events <对象名>` | 含继承链上的所有事件 |
| 查看对象的所有方法 | `python scripts/search.py list funcs <对象名>` | 含继承链上的所有方法(含事件方法) |
| 了解项目结构 | `python scripts/search.py list packages` | 列出所有包和文件数 (含描述) |
| 查看所有示例 | `python scripts/search.py list examples` | 列出所有示例 (含描述) |

### Step 2：阅读确认

搜索到候选后，用 `read` 工具打开目标文件（路径与行号已在搜索结果中给出），确认：
- 完整函数签名（多行参数、返回值类型）
- 中文注释（`// 函数_描述` 和参数说明）
- 相关常量的实际值
- 事件回调的完整签名

### Step 3：回答

基于源码内容组织回答，附上相对文件路径和行号。

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
│   └── tmpl/                 # 模板 (3 文件)
│
└── xcgui-example/            # 示例代码 (83 .go 文件)
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
    ├── Advanced/             # 高级示例 (25 个)
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
    └── HUMUI/                # 拟物化 UI 示例 (2 个)
        ├── HouTai017/        # 后台管理
        └── YanZheng018/      # 验证码
```

## 编码规范速查

### 文档注释风格

```go
// 函数名_中文描述, 简要说明.
//
// x: x坐标.
//
// y: y坐标.
//
// name: 标题.
//
// hParent: 父句柄.
func XBtn_Create(x, y, cx, cy int32, name string, hParent int) int {
```

- 函数名前用中文下划线分隔描述开头
- 注释中引用常量格式：`xcc.Constant_Name_`, 也可能缺失 `xcc.`, 只有 `Constant_Name_`, 你需要知道它确实是在 `xcc` 包里的.

### 构造函数模式

```go
// 1. 直接创建
func NewButton(x, y, cx, cy int32, name string, hParent int) *Button

// 2. 从句柄创建（handle <= 0 返回 nil）
func NewButtonByHandle(handle int) *Button

// 3. 从 name 创建
func NewButtonByName(name string) *Button

// 4. 从 UID 创建
func NewButtonByUID(nUID int32) *Button

// 5. 从 UID 名称创建
func NewButtonByUIDName(name string) *Button
```

### 两种 API 层级

xcgui 提供了两套 API，功能等价，风格不同：

**高层 Go 封装（推荐用于新代码）**：

```go
btn := widget.NewButton(10, 10, 100, 30, "按钮", w.Handle)
btn.AddEvent_BnClick(func(hEle int, pbHandled *bool) int {
    // 处理点击
    return 0
})
```

**底层 C 函数绑定（直接控制，无封装开销）**：

```go
hBtn := xc.XBtn_Create(10, 10, 100, 30, "按钮", w.Handle)
xc.XBtn_AddEvent_BnClick(hBtn, func(hEle int, pbHandled *bool) int {
    return 0
})
```

**关键区别**：
- 高层 `widget.Button` 嵌入 `Element`，提供链式调用和自动方法集
- 底层 `xc.XBtn_*` 直接操作 int 句柄，需手动管理生命周期
- 所有底层函数签名中 `hEle`/`hWindow` 等句柄参数都在第一位

### 事件回调签名

```go
// 元素事件：标准签名
func(hEle int, pbHandled *bool) int

// 窗口事件
func(hWindow int, pbHandled *bool) int

// 鼠标事件（额外参数）
func(hEle int, nFlags int, pPt *xc.POINT, pbHandled *bool) int

// 绘制事件
func(hEle int, hDraw int, pbHandled *bool) int

// 销毁事件
func(hWindow int, pbHandled *bool) int

// 鼠标进入/离开（离开事件多一个参数）
func(hEle int, pbHandled *bool) int           // MouseStay
func(hEle, hEleStay int, pbHandled *bool) int // MouseLeave
```

### bool 参数可选化约定

最后一个 `bool` 参数为 `variadic ...bool`：

```go
// 如果是 Enable 类型的函数, 那么使其默认为 true
func Xxx_Enable(hEle int, bEnable ...bool)

// 调用时：不传参数使用默认值 true
Xxx_Enable(hEle)        // 相当于 bEnable=true
Xxx_Enable(hEle, true)
Xxx_Enable(hEle, false)
```

### 标准入口模式

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

## 封装新模块时的模板参考

当需要为 xcgui 新增模块封装时，按需求选择参考模板：

| 场景 | 参考文件 |
|------|---------|
| 封装新控件 | `source/xcgui/widget/button.go` |
| 封装新窗口类型 | `source/xcgui/window/framewindow.go` |
| 封装底层 C API | `source/xcgui/xc/button.go` |
| 封装动画系统 | `source/xcgui/ani/` |
| 封装常量定义 | `source/xcgui/xcc/xcconst.go` |
| 观察 Go 结构体嵌入 | `source/xcgui/widget/button.go` (Button 嵌入 Element) |

## 封装时的代码生成模板

### 控件封装模板

```go
package widget

import (
    "github.com/twgh/xcgui/xc"
    "github.com/twgh/xcgui/xcc"
)

// MyControl 我的控件.
type MyControl struct {
    Element
}

// 控件_创建, 失败返回 nil.
//
// x: x坐标.
// y: y坐标.
// cx: 宽度.
// cy: 高度.
// name: 标题.
// hParent: 父句柄.
func NewMyControl(x, y, cx, cy int32, name string, hParent int) *MyControl {
    return NewMyControlByHandle(xc.XMyCtrl_Create(x, y, cx, cy, name, hParent))
}

// 从句柄创建对象, 失败返回 nil.
func NewMyControlByHandle(handle int) *MyControl {
    if handle <= 0 { return nil }
    p := &MyControl{}
    p.SetHandle(handle)
    return p
}

// 从 name 创建对象, 失败返回 nil.
func NewMyControlByName(name string) *MyControl {
    return NewMyControlByHandle(xc.XC_GetObjectByName(name))
}

// 从 UID 创建对象, 失败返回 nil.
func NewMyControlByUID(nUID int32) *MyControl {
    return NewMyControlByHandle(xc.XC_GetObjectByUID(nUID))
}

// 从 UID 名称创建对象, 失败返回 nil.
func NewMyControlByUIDName(name string) *MyControl {
    return NewMyControlByHandle(xc.XC_GetObjectByUIDName(name))
}

// 控件_方法描述.
//
// param: 参数说明.
func (m *MyControl) SomeMethod(param int32) bool {
    return xc.XMyCtrl_SomeMethod(m.Handle, param)
}
```

### 底层 C 函数绑定模板

```go
package xc

import (
    "github.com/twgh/xcgui/common"
    "github.com/twgh/xcgui/xcc"
)

// 控件_创建.
//
// x: x坐标.
// y: y坐标.
// cx: 宽度.
// cy: 高度.
// name: 标题.
// hParent: 父句柄.
func XMyCtrl_Create(x, y, cx, cy int32, name string, hParent int) int {
    r, _, _ := xMyCtrl_Create.Call(
        uintptr(x), uintptr(y), uintptr(cx), uintptr(cy),
        common.StrPtr(name), uintptr(hParent))
    return int(r)
}

// 控件_方法.
//
// hEle: 控件句柄.
// param: 参数说明.
func XMyCtrl_SomeMethod(hEle int, param int32) bool {
    r, _, _ := xMyCtrl_SomeMethod.Call(uintptr(hEle), uintptr(param))
    return r != 0
}
```

## 示例快速查找表

| 想实现的功能 | 参考示例 |
|------------|---------|
| 最简单的窗口 | `source/xcgui-example/Basic/SimpleWindow/SimpleWindow.go` |
| 按钮事件 | `source/xcgui-example/Basic/SimpleWindow/SimpleWindow.go` |
| 框架窗口/多面板 | `source/xcgui-example/Basic/FrameWindow/FrameWindow.go` |
| 模态窗口 | `source/xcgui-example/Basic/ModalWindow/ModalWindow.go` |
| 列表控件 | `source/xcgui-example/Basic/List/` + `Basic/List2/` |
| 虚拟列表/表格 | `source/xcgui-example/Advanced/VirtualTable1/` + `VirtualTable2/` |
| 树形控件 | `source/xcgui-example/Basic/Tree/tree.go` |
| 选项卡 | `source/xcgui-example/Basic/TabBar/` + `Advanced/TabControl/` |
| 工具栏 | `source/xcgui-example/Basic/ToolBar/ToolBar.go` |
| 下拉框 | `source/xcgui-example/Basic/ComboBox/ComboBox.go` |
| 编辑框 | `source/xcgui-example/Basic/Edit/Edit.go` |
| 菜单 | `source/xcgui-example/Basic/Menu/` + `Basic/MenuBar/` |
| 颜色选择器 | `source/xcgui-example/Basic/ChooseColor/ChooseColor.go` |
| 日期时间 | `source/xcgui-example/Basic/DateTime/` + `Basic/MonthCal/` |
| SVG 按钮/图片 | `source/xcgui-example/Basic/ButtonSvg/ButtonSvg.go` |
| 图片按钮 | `source/xcgui-example/Basic/ButtonImage/ButtonImage.go` |
| 进度条 | `source/xcgui-example/Basic/ProgressBar/ProgressBar.go` |
| 滑动条 | `source/xcgui-example/Basic/SliderBar/SliderBar.go` |
| 动画（全部） | `source/xcgui-example/Advanced/Animation/Animation.go` |
| 缓动函数 | `source/xcgui-example/Advanced/Ease_All/` + `Ease_Easy/` |
| SVG 绘制 | `source/xcgui-example/Advanced/SvgDraw/SvgDraw.go` |
| 侧边导航 | `source/xcgui-example/Advanced/SideNavigation/SideNavigation.go` |
| 系统托盘 | `source/xcgui-example/Advanced/TrayIcon/` + `TrayIcon2/` |
| 鼠标/键盘钩子 | `source/xcgui-example/Advanced/HookMouse/` + `HookKeyboard/` |
| 热键注册 | `source/xcgui-example/Advanced/RegisterHotKey/RegisterHotKey.go` |
| 多窗口 | `source/xcgui-example/Basic/MultiWindow/MultiWindow.go` |
| 多线程操作 UI | `source/xcgui-example/Basic/MultithreadOperationUI/` + `ThreadOperationUI/` |
| 拖放文件 | `source/xcgui-example/Basic/DropFiles/DropFiles.go` |
| 文件打开对话框 | `source/xcgui-example/Basic/OpenFile/OpenFile.go` |
| DPI 自适应 | `source/xcgui-example/Basic/AutoDpi/AutoDpi.go` |
| UI 设计器 | `source/xcgui-example/Basic/uidesigner/uidesigner.go` |
| 内存加载图片 | `source/xcgui-example/Basic/MemoryLoadImage/MemoryLoadImage.go` |
| 加载布局字符串 | `source/xcgui-example/Basic/LoadLayoutFromString/` |
| 设置默认字体 | `source/xcgui-example/Basic/SetDefaultFont/SetDefaultFont.go` |
| 事件拦截 | `source/xcgui-example/Basic/EventInterception/EventInterception.go` |
| 元素事件 | `source/xcgui-example/Basic/ElementEvent/ElementEvent.go` |
| 自绘菜单 | `source/xcgui-example/Advanced/DrawMenu/DrawMenu.go` |
| 自绘圆角按钮 | `source/xcgui-example/Advanced/DrawRoundButton/DrawRoundButton.go` |
| 音频播放 | `source/xcgui-example/Advanced/AudioPlayer/AudioPlayer.go` |
| Go 图片处理 | `source/xcgui-example/Advanced/GoImage/GoImage.go` |
| WebView2 基础 | `source/xcgui-example/webview/SimpleWebView/` |
| WebView2 + Vue | `source/xcgui-example/webview/VueAndVite/` |
| WebView2 图表 | `source/xcgui-example/webview/Chart/` |
| WebView2 JS-Go 互调 | `source/xcgui-example/webview/CalcMD5/` |
| WebView2 嵌入资源 | `source/xcgui-example/webview/EmbedAssets/` |
| WebView2 自定义协议 | `source/xcgui-example/webview/CustomSchemeRegistration/` |
| WebView2 圆角阴影窗口 | `source/xcgui-example/webview/RoundedShadowWindow/` |
| 优美的 UI 界面例子 | `source/xcgui-example/HUMUI/HouTai017/` 和 `YanZheng018/` |

如果找不到对应示例，用 `python scripts/search.py example <关键词>` 搜索。

## 踩坑经验

- `source/xcgui-example/Basic/` 下是基础控件示例，`source/xcgui-example/Advanced/` 下是高级组合用法示例
- `Animation.go` 是最完整的动画参考
- Go 模块路径是 `github.com/twgh/xcgui`，最小 Go 版本 1.18
- 背景管理器的 XML 字符串（如 `{99:1.9.9;...}`）是从 UI 设计器中设计好后复制出来的，不应手写
- `xc.XAnimaItem_EnableCompleteRelease()` 用于在动画序列完成后自动释放项
- `w.AdjustLayout().Redraw(false)` 在动态添加布局元素后调用以刷新布局
- **xcgui 仅支持 Windows 平台**，不要使用 bash/grep 命令搜索源码，使用 `python scripts/search.py`
