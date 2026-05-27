# 有些元素创建数据适配器后才能用

## 数据适配器作用

数据适配器是用来存储数据的, 其实就是在内部创建一个数组或 map 之类的数据结构, 不创建就没法存储数据\.

## 必须创建数据适配器的元素

### List

```Go
// 创建List
list := widget.NewList(10, 70, 764, 315, w.Handle)
// 创建表头数据适配器
list.CreateAdapterHeader()
// 创建数据适配器: 5列
list.CreateAdapter(5)
```

### ListView

```Go
// 创建ListView
lv := widget.NewListView(10, 32, 445, 357, w.Handle)
// 创建数据适配器
lv.CreateAdapter()
```

### ListBox

```Go
// 创建ListBox
lb := widget.NewListBox(12, 33, 400, 450, w.Handle)
// 创建数据适配器
lb.CreateAdapter()
```

### Tree

```Go
// 创建Tree
tree := widget.NewTree(12, 33, 400, 260, w.Handle)
// 创建数据适配器
tree.CreateAdapter()
```

### CombBox

```Go
// 创建组合框
cbb := widget.NewComboBox(24, 50, 100, 30, w.Handle)
// 创建数据适配器
cbb.CreateAdapter()
```
