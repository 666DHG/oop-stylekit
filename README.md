# OOP Helper

这是面向 OOP 作业的 C++ formatter 和 linter 配置集合，规则依据见 [docs/rule.md](docs/rule.md)。

第一次配置 VS Code、MinGW、clangd 和本仓库规则文件的同学，先看 [docs/QUICKSTART.md](docs/QUICKSTART.md)。

## 包含内容

- `.clang-format`: 自动整理缩进、换行、括号、指针/引用贴近类型等格式。
- `.clang-tidy`: 启用常见 bug、性能、现代 C++、可读性和命名检查。
- `.editorconfig`: 统一编辑器的缩进、换行和文件末尾换行。
- `.clangd.example`: VS Code/clangd 的可选参考配置，不包含本机路径。
- `scripts/cpp_style_lint.py`: 课程规范检查器，检查注释、命名、语句、程序组织、类规则等。
- `scripts/lint-style.ps1`: Windows PowerShell 包装脚本。
- `example/`: 故意写坏的示例代码，用来校验 formatter 和 linter 是否能抓到常见问题。
- [docs/rule-coverage.md](docs/rule-coverage.md): 逐条说明规则由 formatter、linter 还是人工检查覆盖。

## 快速使用

把需要的配置复制到你的 OOP 作业项目根目录：

```powershell
Copy-Item .clang-format, .clang-tidy, .editorconfig C:\path\to\your\oop-project
Copy-Item -Recurse scripts C:\path\to\your\oop-project
```

如果使用 clangd，可以把 `.clangd.example` 复制为 `.clangd`，并按本机环境修改编译器路径。

## 格式化

先安装 `clang-format`，然后在作业项目根目录运行：

```powershell
clang-format -i *.cpp *.h *.hpp
```

如果代码分散在多层目录：

```powershell
Get-ChildItem -Recurse -Include *.cpp,*.h,*.hpp,*.cc,*.cxx | ForEach-Object {
    clang-format -i $_.FullName
}
```

## clang-tidy 检查

`clang-tidy` 依赖本地编译环境。简单项目可以这样运行：

```powershell
clang-tidy .\Shape\*.cpp -- -std=c++11
```

如果项目有 `compile_commands.json`，优先使用：

```powershell
clang-tidy .\Shape\Shape.cpp -p .\.build
```

## 课程规范检查

Python 脚本不依赖第三方库。默认检查当前目录下的 `.cpp/.hpp/.h/.cc/.cxx` 文件：

```powershell
python .\scripts\cpp_style_lint.py
```

Windows 也可以使用包装脚本：

```powershell
.\scripts\lint-style.ps1
```

只检查某个目录或文件：

```powershell
python .\scripts\cpp_style_lint.py Shape Date
.\scripts\lint-style.ps1 Shape\Shape.cpp
```

校验坏样例：

```powershell
python .\scripts\cpp_style_lint.py example
```

`example/` 默认不会被根目录扫描纳入，只有显式指定时才会检查。

输出格式类似：

```text
Shape/Shape.cpp:12: error: 控制语句的语句块必须使用 '{' 和 '}'
... 3 more issue(s) hidden from terminal output
Full report: C:\path\to\your\oop-project\oop-lint-report.txt

C++ style lint: 1 error(s), 3 warning(s)
```

有 `error` 时退出码为 `1`，只有 `warning` 或没有问题时退出码为 `0`。
终端默认最多显示 10 条问题，完整结果会写入 `oop-lint-report.txt`。可用 `--max-output 30` 调整终端显示数量，或用 `--no-report` 关闭报告文件。

## 需要人工检查的内容

工具不能替代老师规范里的全部语义判断。提交前仍需人工检查：

- 注释内容是否准确、是否和代码同步，而不只是字段齐全。
- 空行、行末注释对齐、长表达式拆分位置是否真正易读。
- 变量名中的“物理意义”是否清楚，缩写是否合理。
- 文件里多个函数是否确实属于“一类函数”，类/文件命名是否符合功能。
- 函数是否只完成一件事，重复代码是否应抽成函数。
- 公共变量是否真的必要，含义、取值范围、访问关系是否说明清楚。
- `new/delete` 是否跨函数、跨文件正确配对，delete 后不置空是否确实因为指针即将离开生命周期。
- 继承层数、重定义非虚函数、多继承、类复用、模板/inline 声明实现分离等设计规则。
- `case/default` 的冒号空格要求和部分 clang-format 版本可能冲突；若 formatter 改回 `case 1:`，以课程规范和 linter 输出为准手动调整。

完整覆盖关系见 [docs/rule-coverage.md](docs/rule-coverage.md)。
