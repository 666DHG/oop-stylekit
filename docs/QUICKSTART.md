# QUICKSTART: Windows + VS Code + MinGW 使用指南

这份指南写给第一次配置 VS Code C++ 环境的同学。默认你已经按老师给的 PDF 安装好了 MinGW，路径类似：

```text
D:\mingw64
```

如果你的 MinGW 不在这个目录，把下面所有 `D:\mingw64` 替换成你自己的 MinGW 路径。

## 0. 最终目录应该长什么样

假设你的作业项目叫 `Shape`，最后大概应该是这样：

```text
Shape/
├─ .vscode/
│  ├─ settings.json
│  ├─ tasks.json
│  ├─ launch.json
│  └─ c_cpp_properties.json
├─ scripts/
│  ├─ cpp_style_lint.py
│  └─ lint-style.ps1
├─ .clang-format
├─ .clang-tidy
├─ .clangd
├─ .editorconfig
├─ Shape.cpp
└─ Shape.hpp
```

重点：VS Code 一定要打开整个项目文件夹，例如打开 `Shape/`，不要只双击打开一个 `.cpp` 文件。

## 1. 检查 MinGW 是否可用

打开 PowerShell 或 CMD，输入：

```powershell
g++ --version
gdb --version
```

如果能看到版本号，说明 MinGW 已经加入 PATH。

如果提示“不是内部或外部命令”，说明 MinGW 的 `bin` 目录没有加入 PATH。请把下面这个目录加入系统环境变量 `Path`：

```text
D:\mingw64\bin
```

改完环境变量后，要重新打开 PowerShell 或 VS Code。

## 2. 安装 VS Code 插件

打开 VS Code，按 `Ctrl+Shift+X` 打开扩展面板，安装这些插件：

1. `C/C++`
   - 发布者：Microsoft
   - 用途：编译任务、调试、GDB 支持。

2. `clangd`
   - 发布者：LLVM
   - 用途：代码补全、跳转、实时诊断、读取 `.clang-tidy`。

3. `EditorConfig for VS Code`
   - 发布者：EditorConfig
   - 用途：读取 `.editorconfig`，统一缩进、换行、文件编码。

安装 `clangd` 插件后，如果 VS Code 弹出提示让你下载 clangd，可以点同意。若没有提示，继续看下一节手动安装 LLVM。

## 3. 安装 clangd / clang-format / clang-tidy

MinGW 只提供 `g++` 和 `gdb`，通常不自带这些工具：

- `clangd`: 给 VS Code 做智能提示和实时诊断。
- `clang-format`: 按 `.clang-format` 自动排版代码。
- `clang-tidy`: 按 `.clang-tidy` 做更深的代码检查。

推荐安装 LLVM for Windows：

1. 打开 LLVM 下载页：<https://github.com/llvm/llvm-project/releases>
2. 在发行说明页开头，找到下载入口，例如：

```text
Windows x64 (64-bit): installer (signature)
```

3. 安装时勾选类似 `Add LLVM to the system PATH` 的选项

4. 安装完成后，重新打开 PowerShell，检查：

```powershell
clangd --version
clang-format --version
clang-tidy --version
```

都能显示版本号才算成功。

如果 `clangd` 插件已经自动下载了 clangd，但 `clang-format` 或 `clang-tidy` 命令不可用，仍然建议安装 LLVM。

## 4. 安装 Python

课程规范检查脚本需要 Python。

检查是否已安装：

```powershell
python --version
```

如果提示找不到命令，请安装 Python：

1. 打开 <https://www.python.org/downloads/windows/>
2. 下载 Windows installer。
3. 安装页勾选 `Add python.exe to PATH` 选项
4. 安装后重新打开 PowerShell，再运行：

```powershell
python --version
```

## 5. 把规范文件放进作业项目

从本仓库复制这些文件到你的作业项目根目录：

```text
.clang-format
.clang-tidy
.editorconfig
.clangd.example
scripts/
```

然后把：

```text
.clangd.example
```

重命名为：

```text
.clangd
```

复制后，项目根目录里应该能看到：

```text
.clang-format
.clang-tidy
.clangd
.editorconfig
scripts/
```

## 6. 修改 `.clangd`

打开项目根目录里的 `.clangd`，确认编译器路径。

如果你的 MinGW 是 `D:\mingw64`，可以写成：

```yaml
CompileFlags:
  Add: [-std=c++11, -Wall, -Wextra, -Wpedantic, -Wshadow]
  # 把下面的 Compiler 路径改为你自己的路径
  Compiler: D:/mingw64/bin/g++.exe

Diagnostics:
  ClangTidy:
    Add:
      - bugprone-*
      - clang-analyzer-*
      - readability-identifier-naming
    Remove:
      # 课程规范允许 public 常引用成员，例如 const unsigned int& Year。
      - cppcoreguidelines-avoid-const-or-ref-data-members
      - cppcoreguidelines-non-private-member-variables-in-classes
    CheckOptions:
      readability-identifier-naming.ClassCase: CamelCase
      readability-identifier-naming.FunctionCase: CamelCase
      readability-identifier-naming.ParameterCase: CamelCase
      readability-identifier-naming.ConstantCase: UPPER_CASE
      readability-identifier-naming.ConstexprVariableCase: UPPER_CASE
      readability-identifier-naming.EnumConstantCase: UPPER_CASE
      readability-identifier-naming.ClassConstantCase: UPPER_CASE
      readability-identifier-naming.StaticConstantCase: UPPER_CASE
      readability-identifier-naming.GlobalConstantCase: UPPER_CASE
      readability-identifier-naming.PrivateMemberIgnoredRegexp: 'm_.*'
      readability-identifier-naming.ProtectedMemberIgnoredRegexp: 'm_.*'
```

注意：

- Windows 路径在 `.clangd` 里建议写成 `/`，例如 `D:/mingw64/bin/g++.exe`。
- `-std=c++11` 可以按老师要求改成 `-std=c++17`、`-std=c++20` 或 `-std=c++23`。
- 这里的 C++ 标准最好和 `.vscode/tasks.json` 中的 `-std=` 保持一致。

## 7. 配置 VS Code 工作区设置

在项目根目录创建 `.vscode` 文件夹。如果已经有了，就直接进入这个文件夹。

创建或编辑：

```text
.vscode/settings.json
```

写入：

```json
{
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "llvm-vs-code-extensions.vscode-clangd",
    "C_Cpp.intelliSenseEngine": "disabled",
    "clangd.arguments": [
        "--clang-tidy",
        "--completion-style=detailed",
        "--header-insertion=never"
    ],
    "files.associations": {
        "*.hpp": "cpp",
        "*.h": "cpp"
    }
}
```

为什么要禁用 `C_Cpp.intelliSenseEngine`：

- Microsoft C/C++ 插件保留给编译和调试。
- clangd 负责补全和诊断。
- 两个智能提示引擎同时开，容易重复报错或互相打架。

## 8. 沿用 PDF 中的 VS Code 编译配置

老师 PDF 里的默认方案使用三个文件：

```text
.vscode/c_cpp_properties.json
.vscode/tasks.json
.vscode/launch.json
```

它们的作用是：

| 文件 | 作用 |
|---|---|
| `c_cpp_properties.json` | Microsoft C/C++ 插件的 IntelliSense 配置。用了 clangd 后它不是最重要，但保留也没问题。 |
| `tasks.json` | 编译配置，按 `Ctrl+Shift+B` 时运行。 |
| `launch.json` | 调试配置，按 `F5` 时运行，并通过 `preLaunchTask` 先编译。 |

如果你已经按 PDF 生成了这三个文件，可以继续使用。只需要确认里面的路径是你自己的 MinGW 路径。

### 8.1 `tasks.json` 简化推荐版

如果你还没有 `tasks.json`，可以创建：

```text
.vscode/tasks.json
```

写入：

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Debug - C++11 O0",
            "type": "cppbuild",
            "command": "D:/mingw64/bin/g++.exe",
            "args": [
                "-std=c++11",
                "-O0",
                "-g",
                "-Wall",
                "-Wextra",
                "-Wpedantic",
                "${fileDirname}\\*.cpp",
                "-o",
                "${fileDirname}\\${fileBasenameNoExtension}_debug.exe"
            ],
            "group": {
                "kind": "build",
                "isDefault": true
            },
            "problemMatcher": [
                "$gcc"
            ],
            "detail": "Debug build with MinGW g++"
        }
    ]
}
```

如果老师要求 C++23，把所有 `c++11` 改成 `c++23`。

### 8.2 `launch.json` 简化推荐版

如果你还没有 `launch.json`，可以创建：

```text
.vscode/launch.json
```

写入：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug current folder",
            "type": "cppdbg",
            "request": "launch",
            "program": "${fileDirname}\\${fileBasenameNoExtension}_debug.exe",
            "args": [],
            "stopAtEntry": false,
            "cwd": "${fileDirname}",
            "environment": [],
            "externalConsole": false,
            "MIMode": "gdb",
            "miDebuggerPath": "D:/mingw64/bin/gdb.exe",
            "setupCommands": [
                {
                    "description": "Enable pretty-printing",
                    "text": "-enable-pretty-printing",
                    "ignoreFailures": true
                }
            ],
            "preLaunchTask": "Debug - C++11 O0"
        }
    ]
}
```

注意：`preLaunchTask` 必须和 `tasks.json` 里的 `label` 完全一样。

### 8.3 `c_cpp_properties.json`

如果你已经使用 clangd，这个文件不是必须的。但如果 Microsoft C/C++ 插件提示要生成，可以保留 PDF 中的配置。

一个简单版本如下：

```json
{
    "configurations": [
        {
            "name": "MinGW64",
            "includePath": [
                "${workspaceFolder}/**"
            ],
            "defines": [
                "_DEBUG",
                "UNICODE",
                "_UNICODE"
            ],
            "compilerPath": "D:/mingw64/bin/g++.exe",
            "cStandard": "c17",
            "cppStandard": "c++11",
            "intelliSenseMode": "windows-gcc-x64"
        }
    ],
    "version": 4
}
```

## 9. 格式化代码

打开 `.cpp` 或 `.hpp` 文件，按下 `Shift+Alt+F`

如果第 7 步设置了 `editor.formatOnSave`，保存文件时也会自动格式化。

也可以在 PowerShell 中批量格式化：

```powershell
Get-ChildItem -Recurse -Include *.cpp,*.h,*.hpp,*.cc,*.cxx | ForEach-Object {
    clang-format -i $_.FullName
}
```

## 10. 运行课程规范检查

在 VS Code 中打开终端：

```text
终端 -> 新建终端
```

确认终端路径是项目根目录，然后运行：

```powershell
python .\scripts\cpp_style_lint.py
```

只检查某个文件：

```powershell
python .\scripts\cpp_style_lint.py Shape.cpp
```

Windows 也可以运行：

```powershell
.\scripts\lint-style.ps1
```

如果 PowerShell 提示不能运行脚本，可以先用 Python 命令。Python 命令最稳定。

终端默认最多显示 10 条问题，完整结果会保存到项目根目录：

```text
oop-lint-report.txt
```

如果想在终端显示更多问题：

```powershell
python .\scripts\cpp_style_lint.py --max-output 30
```

## 11. 编译和调试

编译：

```text
Ctrl+Shift+B
```

调试：

```text
F5
```

如果调试前提示找不到任务，请检查：

- `.vscode/tasks.json` 里的 `label`
- `.vscode/launch.json` 里的 `preLaunchTask`

这两个字符串必须完全一致。

## 12. 常见问题

### VS Code 一直提示找不到 `g++.exe`

检查所有配置里的路径

### `g++ --version` 可以用，但 VS Code 还是不行

重新启动 VS Code。环境变量修改后，已经打开的软件不会自动刷新 PATH。

### clangd 和 C/C++ 插件重复报错

确认 `.vscode/settings.json` 里有：

```json
"C_Cpp.intelliSenseEngine": "disabled"
```

### 保存时没有自动格式化

确认：

- 已安装 `clangd` 插件。
- 已安装 LLVM，并且 `clang-format --version` 可用。
- 项目根目录有 `.clang-format`。
- `.vscode/settings.json` 里有 `"editor.formatOnSave": true`。

### `.clang-tidy` 没有效果

确认 `.vscode/settings.json` 里有：

```json
"clangd.arguments": [
    "--clang-tidy"
]
```

然后重启 clangd：

```text
Ctrl+Shift+P -> clangd: Restart language server
```


## 13. 提交前检查清单

提交作业前，建议按顺序做：

1. 保存所有文件，让 VS Code 自动格式化。
2. 运行：

```powershell
python .\scripts\cpp_style_lint.py
```

3. 修掉所有 `error`。
4. 尽量修掉 `warning`。
5. 按 `Ctrl+Shift+B` 确认能编译。
6. 按 `F5` 确认能调试。
7. 人工检查 README 中列出的无法自动判断的规范项。
