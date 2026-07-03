# OOP StyleKit

面向 OOP 作业的 C++ 代码风格工具包。它把范老师 V1.3 编码规范拆成三类可执行检查：

- `scripts/format-style.py` 负责自动排版：先运行 `clang-format`，再补课程要求的 `case/default` 冒号空格。
- `.clang-tidy` 负责通用 C++ 质量检查，例如潜在 bug、可读性、现代 C++ 写法和部分命名规则。
- `scripts/cpp_style_lint.py` 负责课程规范检查，例如文件/类/函数注释、命名前缀、控制语句大括号、头源文件组织、类规则等。

> 说明：这个工具是辅助提交前自查用的，不能保证覆盖老师规范里的所有语义判断。哪些规则能自动检查、哪些仍要人工看，见 [仍需人工检查](#仍需人工检查)部分 与 [docs/rule-coverage.md](docs/rule-coverage.md)。

## 仓库内容

| 文件/目录 | 作用 |
|---|---|
| `.clang-format` | clang-format 自动格式化规则。 |
| `.clang-tidy` | clang-tidy 静态检查规则。 |
| `.vscode/` | VS Code 保存时自动运行课程 formatter 的推荐配置。 |
| `.editorconfig` | 统一编辑器缩进、换行和文件末尾换行。 |
| `.clangd.example` | VS Code/clangd 参考配置，复制到作业项目后改名为 `.clangd`。 |
| `scripts/format-style.py` | 自定义 formatter 包装脚本，先跑 clang-format，再修正 `case/default` 冒号空格。 |
| `scripts/format-style.ps1` | Windows PowerShell formatter 包装脚本，供 VS Code 保存时调用。 |
| `scripts/cpp_style_lint.py` | 自定义课程规范检查器，不依赖第三方 Python 包。 |
| `scripts/lint-style.ps1` | Windows PowerShell 包装脚本。 |
| `example/` | 故意写坏的示例代码，用来测试 formatter 和 linter。 |
| `docs/QUICKSTART.md` | Windows + VS Code + MinGW 从零配置指南。 |
| `docs/rule-coverage.md` | 课程规范覆盖关系说明。 |

## 快速开始

如果你还没有配置 VS Code、MinGW、clangd、clang-format、clang-tidy 或 Python，先看 [docs/QUICKSTART.md](docs/QUICKSTART.md)。

在你的 OOP 作业项目根目录中放入这些文件：

```text
.clang-format
.clang-tidy
.editorconfig
.clangd
.vscode/
scripts/
```

其中 `.clangd` 可以由本仓库的 `.clangd.example` 复制改名得到。改名后请打开 `.clangd`，把编译器路径改成本机 MinGW 路径，例如：

```yaml
Compiler: D:/mingw64/bin/g++.exe
```

## 使用

检查代码时，建议按这个顺序走：

1. 先用 `format-style.py` 自动排版。
2. 再用 `clang-tidy` 看通用 C++ 问题。
3. 最后用 `cpp_style_lint.py` 检查课程规范。
4. 修完自动工具能发现的问题后，再人工检查工具无法判断的设计和语义规则。

## 1. 格式化

格式化只负责把代码排整齐。它会直接改写文件，不会告诉你代码设计是否符合课程规范。

在作业项目根目录运行：

```powershell
python .\scripts\format-style.py
```

只格式化某个文件或目录：

```powershell
python .\scripts\format-style.py Shape.cpp
python .\scripts\format-style.py Shape
```

Windows 也可以使用包装脚本：

```powershell
.\scripts\format-style.ps1 Shape.cpp
```

VS Code 保存时自动格式化需要安装推荐扩展 `emeraldwalk.RunOnSave`，并使用本仓库 `.vscode/settings.json` 中的配置。保存时由 clangd 负责常规格式化和 80 列换行，Run on Save 只补 `case/default` 冒号空格。具体配置见 [docs/QUICKSTART.md](docs/QUICKSTART.md)。

## 2. clang-tidy 检查

`clang-tidy` 会调用本地编译环境，所以它比格式化更依赖 MinGW、头文件路径和 C++ 标准设置。简单项目可以这样运行：

```powershell
clang-tidy .\Shape\*.cpp -- -std=c++11
```

如果项目有 `compile_commands.json`，优先使用编译数据库：

```powershell
clang-tidy .\Shape\Shape.cpp -p .\.build
```

如果 clang-tidy 报找不到头文件、找不到标准库或 C++ 标准不一致，先检查 `.clangd`、VS Code 编译任务和命令里的 `-std=` 是否一致。

## 3. 课程规范检查

课程规范检查器是这个仓库里最贴近老师 V1.3 规范的部分。它不修改代码，只输出 error/warning，并把完整结果写入报告文件。

在作业项目根目录运行：

```powershell
python .\scripts\cpp_style_lint.py
```

Windows 也可以使用包装脚本：

```powershell
.\scripts\lint-style.ps1
```

默认会检查当前目录下的 `.cpp/.hpp/.h/.cc/.cxx` 文件，并跳过 `.git`、`build`、`.build`、`out`、`example` 等目录。

只检查某个文件或目录：

```powershell
python .\scripts\cpp_style_lint.py Shape.cpp
python .\scripts\cpp_style_lint.py Shape Date
.\scripts\lint-style.ps1 Shape\Shape.cpp
```

检查本仓库的坏样例：

```powershell
python .\scripts\cpp_style_lint.py example
```

输出示例：

```text
Shape/Shape.cpp:12: error: 控制语句的语句块必须使用 '{' 和 '}'
... 3 more issue(s) hidden from terminal output
Full report: C:\path\to\your\oop-project\oop-lint-report.txt

C++ style lint: 1 error(s), 3 warning(s)
```

退出码规则：

- 有 `error`：退出码为 `1`。
- 只有 `warning` 或没有问题：退出码为 `0`。

常用参数：

```powershell
python .\scripts\cpp_style_lint.py --max-output 30
python .\scripts\cpp_style_lint.py --no-report
python .\scripts\cpp_style_lint.py --report reports\style.txt
```

参数说明：

- `--max-output 30`: 终端最多显示 30 条问题，报告文件仍保留全部问题。
- `--no-report`: 不生成 `oop-lint-report.txt`。
- `--report reports\style.txt`: 指定完整报告输出位置。

## error 和 warning 怎么看

建议优先处理所有 `error`，因为它们通常对应明确违反课程规范的写法，例如控制语句缺少大括号、头文件中定义普通函数、类缺少必要特殊成员函数等。

`warning` 多数是工具无法完全确定语义的提示，例如命名建议、函数过长、多个函数是否属于同一类功能、跨文件所有权是否合理。warning 不一定都要机械修改，但提交前应该逐条确认。

## 仍需人工检查

工具不能替代人工判断。提交前仍建议重点看这些内容：

- 注释内容是否准确、是否和代码同步，而不只是字段齐全。
- 空行、行末注释对齐、长表达式拆分位置是否真正易读。
- 变量名的物理意义是否清楚，缩写是否合理。
- 文件里的多个函数是否确实属于“一类函数”，类名/文件名是否符合功能。
- 函数是否只完成一件事，重复代码是否应该抽成函数。
- 公共变量是否真的必要，含义、取值范围、访问关系是否说明清楚。
- `new/delete` 是否跨函数、跨文件正确配对，`delete` 后不置空是否确实因为指针即将离开生命周期。
- 继承层数、重定义非虚函数、多继承、类复用、模板/inline 声明实现分离等设计规则。
- `case/default` 的冒号空格要求和 clang-format 默认行为冲突；请使用 `scripts/format-style.py` 或 VS Code Run on Save 配置，让保存后的结果保持为 `case 1 : `。
- `//【` 开头的 V1.3 字段注释用于固定模板对齐，formatter 会保持原样，不自动加空格或换行。

完整覆盖关系见 [docs/rule-coverage.md](docs/rule-coverage.md)。
