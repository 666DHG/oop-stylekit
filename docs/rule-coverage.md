# 规则覆盖表

本文按 `docs/rule.md` 逐条核对 formatter、clang-tidy 和自定义 linter 的覆盖情况。

标记说明：

- `formatter`: 主要由 `.clang-format` 自动整理。
- `linter`: 主要由 `scripts/cpp_style_lint.py` 检查。
- `clang-tidy`: 主要由 `.clang-tidy` 检查。
- `manual`: 需要使用者人工判断，工具只能提示或无法可靠判断。

| 规则 | 覆盖方式 | 说明 |
|---|---|---|
| 2.1.1 空行的使用 | manual | 主要部分和函数内部逻辑段落是否需要空行依赖语义。 |
| 2.1.2 哪里应该使用空格 | formatter, linter | clang-format 处理常规空格；linter 补充逗号、三目、控制语句、case/default 冒号等检查。 |
| 2.1.3 哪里可以使用空格 | manual | 对齐空格属于可读性判断。 |
| 2.1.4 哪里不应该使用空格 | formatter, linter | 检查 `. -> :: []`、一元操作符和分号前空格。 |
| 2.1.5 缩进 | formatter, linter | 4 空格缩进、禁用 Tab。 |
| 2.1.6 长语句的书写格式 | formatter, linter | 80 列由 formatter/linter 处理；按低优先级操作符拆分需人工复核。 |
| 2.1.7 清晰划分控制语句的语句块 | formatter, linter | 检查 if/for/while/switch/else/do 的大括号。 |
| 2.1.8 一行只写一条语句或标号 | formatter, linter | 检查一行多个分号。 |
| 2.1.9 一次只声明、定义一个变量/常量 | linter | 检查简单多变量声明。 |
| 2.1.10 在表达式中使用括号 | manual | 是否需要括号取决于表达式语义。 |
| 2.1.11 `*`、`&` 和类型写在一起 | formatter, linter | clang-format 设置 Left；linter 检查基础类型写法。 |
| 2.2.1 对函数进行注释 | linter, manual | 检查声明前是否有注释，并检查定义前的必需字段；注释质量需人工判断。 |
| 2.2.2 对类进行注释 | linter, manual | 检查必需字段；接口说明是否充分需人工判断。 |
| 2.2.3 对文件进行注释 | linter, manual | 检查文件头必需字段。 |
| 2.2.4 空循环体确认性注释 | linter | 建议级，缺少时 warning。 |
| 2.2.5 多个 case 共用出口确认性注释 | linter | 建议级，缺少时 warning。 |
| 2.2.6 其它应该考虑进行注释的地方 | manual | 变量、分支、赋值等是否需要注释依赖语义。 |
| 2.2.7 行末注释尽量对齐 | manual | 对齐质量依赖局部排版。 |
| 2.2.8 注释量 | linter | 检查注释行不少于代码行的 1/3。 |
| 2.3.1 标识符命名要求 | linter, clang-tidy, manual | 检查大小写、bool 前缀、宏/常量、部分作用域和类型前缀；物理意义需人工判断。 |
| 2.3.2 标识符长度要求 | linter | 检查 4 到 25 字符，保留常见短名例外。 |
| 2.3.3 文件命名要求 | linter, manual | 类文件名与类名不一致时 warning；功能类文件需人工判断。 |
| 2.4.1 一条语句只包含一个赋值操作符 | linter | 检查简单赋值操作符数量。 |
| 2.4.2 控制语句条件中不使用赋值操作符 | linter | 建议级，缺少时 warning。 |
| 2.4.3 赋值表达式中的规定 | linter, manual | 检查简单左值重复；复杂表达式需人工判断。 |
| 2.4.4 禁用 goto | linter | 使用 goto 报 error。 |
| 2.4.5 避免浮点精确比较 | linter, clang-tidy | 检查已声明 float/double 和浮点字面量的 `==`/`!=`。 |
| 2.4.6 switch 每个分支结尾要求 | linter | 检查非空 case/default 是否有 break/return/throw。 |
| 2.4.7 switch default 分支 | linter | 缺少 default 报 error。 |
| 2.4.8 指针初始化 | linter | 检查简单未初始化指针声明。 |
| 2.4.9 释放内存后的指针变量 | linter, manual | delete 后数行内未置 nullptr 时 warning；生命周期例外需人工判断。 |
| 2.4.10 正规布尔表达式 | linter | 建议级，检查简单 `if (Flag)` 形式。 |
| 2.4.11 new 和 delete | linter, manual | 检查同文件简单配对和 new[]/delete[] 形式；跨函数/跨文件所有权需人工判断。 |
| 2.5.1 明确函数功能 | linter, manual | 检查函数体非注释代码超过 100 行；是否只做一件事需人工判断。 |
| 2.5.2 重复代码编写成函数 | manual | 重复逻辑需要人工设计判断。 |
| 2.5.3 函数参数指定类型和名称 | linter | 检查函数声明中的无名参数。 |
| 2.5.4 为函数指定返回值 | clang-tidy, compiler | 现代 C++ 编译器会拒绝多数缺失返回类型写法。 |
| 2.5.5 函数调用参数中不使用赋值操作符 | linter | 建议级，检查简单函数调用参数。 |
| 2.6.1 一个头文件只声明一个函数/一类函数/一个类 | linter, manual | 多类报 error；多函数声明 warning，是否“一类函数”需人工判断。 |
| 2.6.2 一个源文件只实现一个函数/一类函数/一个类 | linter, manual | 多函数实现 warning，是否“一类函数”需人工判断。 |
| 2.6.3 头文件只包含声明 | linter | 检查普通函数定义和全局变量定义。 |
| 2.6.4 源文件中不要有函数/类声明 | linter | 类声明报 error，函数声明 warning。 |
| 2.6.5 只允许头文件被包含 | linter | include `.cpp/.cc/.cxx` 报 error。 |
| 2.6.6 避免头文件重复包含 | linter | 检查 `#ifndef/#define` 或 `#if !defined/#define`。 |
| 2.7.1 严格限制公共变量使用 | manual | 是否必要取决于设计。 |
| 2.7.2 明确公共变量定义 | linter, manual | 检查全局变量命名；含义、范围、关系说明需人工判断。 |
| 2.7.3 防止公共变量与局部变量重名 | linter | 检查同文件简单重名。 |
| 2.8.1 默认构造函数 | linter | 缺少显式默认构造或 using 继承构造时报 error。 |
| 2.8.2 拷贝构造函数 | linter | 缺少显式拷贝构造或 `= delete` 报 error。 |
| 2.8.3 重载 `=` 操作符 | linter | 缺少 `operator=` 或 `= delete` 报 error。 |
| 2.8.4 析构函数 | linter | 缺少显式析构函数报 error。 |
| 2.8.5 基类虚析构 | linter, manual | 同文件识别到被继承的类时检查 virtual；跨文件继承需人工判断。 |
| 2.8.6 不要重定义继承来的非虚函数 | manual | 需要跨类语义分析，当前不自动判断。 |
| 2.8.7 operator new/delete 成对重载 | linter | 类内发现 operator new 但无 operator delete 报 error。 |
| 2.8.9 类数据成员访问控制 | linter | public 数据成员报 error，public const 引用例外。 |
| 2.8.10 限制继承层数 | manual | 跨文件继承层数需要人工确认。 |
| 2.8.11 慎用多继承 | linter, manual | 多继承 warning；理由是否充分需人工判断。 |
| 2.8.12 考虑类复用 | manual | 设计质量无法可靠自动检查。 |
| 2.8.13 类声明和实现分离 | linter, manual | cpp 中类声明报 error；模板/inline 的声明实现分离需人工复核。 |
| 2.9.1 常量代替无参数宏 | linter | 无参数宏常量报 error。 |
| 2.9.2 内联代替有参数宏 | linter | 有参数宏报 error。 |
| 2.9.3 C++ 风格类型转换 | linter, clang-tidy | C 风格转换 warning。 |
| 2.9.4 删除不再使用的代码 | linter, manual | 简单注释掉的代码 warning；是否真正废弃需人工判断。 |
