# Lint Fixture: Bad Style Example

这个目录是故意写坏的示例，用来校验 formatter 和 linter 是否能抓到常见问题。它不是可提交作业代码，也不保证能正常编译。

默认运行下面命令时，linter 会跳过本目录：

```powershell
python .\scripts\cpp_style_lint.py
```

如果要检查这个坏样例，请显式指定 `example`：

```powershell
python .\scripts\cpp_style_lint.py example
```

你应该能看到大量 error/warning，例如：

- 缺少 V1.3 文件/类/函数注释字段。
- include guard 名称不一致。
- 头文件中包含函数定义或全局变量定义。
- 宏名不是全大写，宏常量/宏函数不符合规范。
- 类名/函数名/bool 名不符合命名规则。
- 私有成员缺少 `m_`、`m_i`、`m_ui`、`m_p` 等前缀。
- public 数据成员不符合课程规范。
- 控制语句缺少大括号。
- 一行多条语句。
- 指针未初始化、`new[]` 和 `delete` 不匹配。
- `switch` 缺少 `default` 或 case 结尾缺少 `break`。
- `goto`、浮点精确比较、函数调用参数中自增等语句问题。
- Tab 缩进、行尾空白、长行、逗号/三目/一元操作符空格错误。

终端默认只显示前 10 条问题，完整输出会写入项目根目录的 `oop-lint-report.txt`。如果想在终端看更多：

```powershell
python .\scripts\cpp_style_lint.py example --max-output 50
```

建议校验 formatter 时先复制一份再运行 `clang-format -i`，因为 formatter 会直接改写文件：

```powershell
Copy-Item -Recurse example example-work
clang-format -i example-work\*.cpp example-work\*.hpp
python .\scripts\cpp_style_lint.py example-work
```