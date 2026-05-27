# XCGUI 源码的编码规范速查

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

### 