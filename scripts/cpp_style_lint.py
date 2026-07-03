from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_ROOT = Path.cwd().resolve()
ROOT = DEFAULT_ROOT
SOURCE_SUFFIXES = {".cpp", ".hpp", ".h", ".cc", ".cxx"}
HEADER_SUFFIXES = {".hpp", ".h"}
IMPLEMENTATION_SUFFIXES = {".cpp", ".cc", ".cxx"}
SKIP_DIRS = {
    ".git",
    ".build",
    ".codex-tmp",
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "out",
}
DEFAULT_SKIP_DIRS = SKIP_DIRS | {"example"}
SIMPLE_NAME_EXEMPTIONS = {"i", "j", "k", "x", "y", "z", "Day", "Set", "main"}
CONTROL_KEYWORDS = ("if", "for", "while", "switch")
ASSIGNMENT_RE = re.compile(r"(\+\+|--|\+=|-=|\*=|/=|%=|>>=|<<=|&=|\|=|\^=|(?<![=!<>])=(?!=))")
COMMENT_DIVIDER_RE = re.compile(r"^\s*//\s*-{20,}\s*$")
DECLARATION_START_RE = re.compile(
    r"^\s*(?:static\s+|extern\s+|const\s+|constexpr\s+|mutable\s+|unsigned\s+|signed\s+|long\b|short\b|"
    r"char\b|int\b|float\b|double\b|bool\b|void\b|std::|[A-Z]\w+\b)"
)
TYPE_PREFIXES = {
    "char": "c",
    "int": "i",
    "short": "n",
    "long": "l",
    "long long": "ll",
    "float": "f",
    "double": "r",
}


@dataclass
class Issue:
    path: Path
    line: int
    severity: str
    message: str

    def format(self) -> str:
        try:
            rel = self.path.relative_to(ROOT)
        except ValueError:
            rel = self.path
        return f"{rel}:{self.line}: {self.severity}: {self.message}"


@dataclass
class FunctionInfo:
    name: str
    line: int
    end_line: int
    header: str
    body: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    line: int
    end_line: int
    kind: str
    bases: list[str]
    body: list[tuple[int, str]]


@dataclass
class FunctionDeclInfo:
    name: str
    line: int
    header: str


def iter_source_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    explicit_targets = bool(targets)
    pending = targets or [ROOT]
    for target in pending:
        if target.is_file():
            candidates = [target]
        elif target.is_dir():
            candidates = target.rglob("*")
        else:
            continue

        for path in candidates:
            path = path.resolve()
            if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
                continue
            try:
                parts = path.relative_to(ROOT).parts
            except ValueError:
                parts = path.parts
            skip_dirs = SKIP_DIRS if explicit_targets else DEFAULT_SKIP_DIRS
            if any(part in skip_dirs for part in parts):
                continue
            files.append(path)
    return sorted(set(files))


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def strip_line_comment(line: str) -> str:
    in_string = False
    in_char = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and not in_char:
            in_string = not in_string
            continue
        if char == "'" and not in_string:
            in_char = not in_char
            continue
        if not in_string and not in_char and line[index:index + 2] == "//":
            return line[:index]
    return line


def strip_strings(line: str, fill: str = " ") -> str:
    result: list[str] = []
    in_string = False
    in_char = False
    escaped = False
    for char in line:
        if escaped:
            result.append(fill)
            escaped = False
            continue
        if char == "\\" and (in_string or in_char):
            result.append(fill)
            escaped = True
            continue
        if char == '"' and not in_char:
            in_string = not in_string
            result.append(fill)
            continue
        if char == "'" and not in_string:
            in_char = not in_char
            result.append(fill)
            continue
        result.append(fill if in_string or in_char else char)
    return "".join(result)


def strip_template_arguments(code: str) -> str:
    result: list[str] = []
    depth = 0
    for char in code:
        if char == "<":
            depth += 1
            continue
        if char == ">" and depth > 0:
            depth -= 1
            continue
        if depth == 0:
            result.append(char)
    return "".join(result)


def case_default_label_colon_index(code: str) -> int | None:
    stripped = code.lstrip()
    indent_len = len(code) - len(stripped)
    if stripped.startswith("case "):
        index = indent_len + len("case ")
    elif stripped.startswith("default"):
        after_keyword = stripped[len("default"):len("default") + 1]
        if after_keyword not in {"", " ", "\t", ":"}:
            return None
        index = indent_len + len("default")
    else:
        return None

    ternary_depth = 0
    while index < len(code):
        char = code[index]
        if char == "?":
            ternary_depth += 1
        elif char == ":":
            if code[index - 1:index + 1] == "::" or code[index:index + 2] == "::":
                index += 2
                continue
            if ternary_depth > 0:
                ternary_depth -= 1
            else:
                return index
        index += 1

    return None


def is_case_default_label_with_trailing_label_space(code: str) -> bool:
    colon_index = case_default_label_colon_index(code)
    if colon_index is None:
        return False
    return code[:colon_index].endswith(" ") and code[colon_index + 1:] == " "


def code_lines_without_comments(lines: list[str]) -> list[str]:
    result: list[str] = []
    in_block = False
    for raw in lines:
        line = raw
        output = ""
        cursor = 0
        while cursor < len(line):
            if in_block:
                end = line.find("*/", cursor)
                if end == -1:
                    cursor = len(line)
                else:
                    in_block = False
                    cursor = end + 2
                continue

            block_start = line.find("/*", cursor)
            slash_start = line.find("//", cursor)
            starts = [pos for pos in (block_start, slash_start) if pos != -1]
            if not starts:
                output += line[cursor:]
                break

            first = min(starts)
            output += line[cursor:first]
            if first == slash_start:
                break

            end = line.find("*/", first + 2)
            if end == -1:
                in_block = True
                break
            cursor = end + 2
        result.append(output)
    return result


def count_comment_and_code_lines(lines: list[str]) -> tuple[int, int]:
    comment_lines = 0
    code_lines = 0
    in_block = False
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        has_comment = False
        cursor = 0
        while cursor < len(line):
            if in_block:
                has_comment = True
                end = line.find("*/", cursor)
                if end == -1:
                    cursor = len(line)
                else:
                    in_block = False
                    cursor = end + 2
                continue

            block_start = line.find("/*", cursor)
            slash_start = line.find("//", cursor)
            starts = [pos for pos in (block_start, slash_start) if pos != -1]
            if not starts:
                if line[cursor:].strip():
                    code_lines += 1
                break

            first = min(starts)
            if line[cursor:first].strip():
                code_lines += 1
            has_comment = True
            if first == slash_start:
                break

            end = line.find("*/", first + 2)
            if end == -1:
                in_block = True
                break
            cursor = end + 2

        if has_comment:
            comment_lines += 1
    return comment_lines, code_lines


def previous_comment_block(lines: list[str], line_index: int, max_gap: int = 3) -> str:
    index = line_index - 1
    gap = 0
    block: list[str] = []
    while index >= 0:
        stripped = lines[index].strip()
        if not stripped:
            gap += 1
            if gap > max_gap and block:
                break
            index -= 1
            continue
        if stripped.endswith("*/"):
            block.append(stripped)
            index -= 1
            while index >= 0:
                inner = lines[index].strip()
                block.append(inner)
                if inner.startswith("/*"):
                    index -= 1
                    break
                index -= 1
            continue
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*") or stripped.endswith("*/"):
            block.append(stripped)
            index -= 1
            continue
        break
    return "\n".join(reversed(block))


def normalize_comment_text(block: str) -> str:
    return re.sub(r"\s+", "", block)


def has_field_groups(block: str, field_groups: list[tuple[str, ...]]) -> bool:
    normalized = normalize_comment_text(block)
    return all(any(field in normalized for field in group) for group in field_groups)


def has_comment_content(block: str) -> bool:
    normalized = normalize_comment_text(block)
    return bool(normalized.strip("/-*"))


FILE_COMMENT_FIELDS = [
    ("【文件名】", "文件名"),
    ("【功能模块和目的】", "【功能模块】", "【文件功能】", "【功能】", "功能模块和目的"),
    ("【开发者及日期】", "【开发者】", "【作者及日期】", "【作者】", "开发者及日期"),
]

CLASS_COMMENT_FIELDS = [
    ("【类名】", "类名"),
    ("【功能】", "【类功能】", "功能"),
    ("【接口说明】", "【接口】", "接口说明", "接口"),
    ("【开发者及日期】", "【开发者】", "【作者及日期】", "【作者】", "开发者及日期"),
]

FUNCTION_COMMENT_FIELDS = [
    ("【函数名称】", "【函数名】", "函数名称", "函数名"),
    ("【函数功能】", "【功能】", "函数功能"),
    ("【参数】", "【形参】", "参数"),
    ("【返回值】", "【返回】", "返回值", "返回"),
    ("【开发者及日期】", "【开发者】", "【作者及日期】", "【作者】", "开发者及日期"),
]


def first_code_line(lines: list[str]) -> int:
    code_lines = code_lines_without_comments(lines)
    for index, line in enumerate(code_lines):
        if line.strip():
            return index
    return 0


def expected_guard(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", path.name).upper()


def split_parameters(params: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for char in params:
        if char in "(<[{":
            depth += 1
        elif char in ")>]}":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def assignment_count(code: str) -> int:
    sanitized = strip_strings(code)
    sanitized = re.sub(r"\boperator\s*(==|=|\+=|-=|\*=|/=|%=|>>=|<<=|&=|\|=|\^=)", "operator", sanitized)
    return len(ASSIGNMENT_RE.findall(sanitized))


def likely_declaration(code: str) -> bool:
    return bool(DECLARATION_START_RE.match(code))


def likely_function_declaration(code: str) -> bool:
    stripped = code.strip()
    if not stripped.endswith(";") or any(token in stripped for token in (".", "->", "<<", ">>")):
        return False
    if stripped.startswith(("return ", "if ", "for ", "while ", "switch ", "else ", "case ")):
        return False
    return bool(
        re.match(
            r"(?:static\s+|virtual\s+|inline\s+|explicit\s+|friend\s+|constexpr\s+)*"
            r"(?:const\s+)?(?:unsigned\s+|signed\s+|long\s+|short\s+)?"
            r"(?:void|char|int|float|double|bool|[A-Z]\w*|std::\w+|[A-Za-z_]\w*::[A-Za-z_]\w*)"
            r"[\w:<>&*\s]*\s+[~A-Za-z_]\w*(?:::\w+)?\s*\([^;{}]*\)\s*(?:const\s*)?(?:override\s*)?(?:final\s*)?;",
            stripped,
        )
    )


def extract_declared_name(statement: str) -> str | None:
    statement = re.split(r"[={]", statement, maxsplit=1)[0].strip().rstrip(";")
    statement = statement.replace("*", " ").replace("&", " ")
    tokens = re.findall(r"[A-Za-z_]\w*", statement)
    if not tokens:
        return None
    if tokens[-1] in {"const", "static", "unsigned", "signed", "long", "short"}:
        return None
    return tokens[-1]


def identifier_base(name: str) -> str:
    for prefix in ("m_p", "m_", "g_p", "g_", "s_"):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def is_probable_variable_declaration(code: str) -> bool:
    stripped = code.strip()
    if not stripped.endswith(";") or stripped.startswith("#"):
        return False
    if stripped.startswith(("return ", "using ", "typedef ", "namespace ", "class ", "struct ", "enum ")):
        return False
    if likely_function_declaration(stripped):
        return False
    return bool(DECLARATION_START_RE.match(stripped))


def has_pointer_type(code: str) -> bool:
    before_name = re.split(r"[=;]", code, maxsplit=1)[0]
    return "*" in before_name


def expected_primitive_prefix(code: str) -> str | None:
    normalized = " ".join(code.replace("*", " ").replace("&", " ").split())
    unsigned = "unsigned " in normalized
    for type_name, prefix in sorted(TYPE_PREFIXES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(type_name)}\b", normalized):
            if unsigned:
                return f"u{prefix}"
            return prefix
    return None


def check_scoped_variable_name(
    path: Path,
    line: int,
    code: str,
    name: str,
    scope_prefix: str,
    issues: list[Issue],
) -> None:
    pointer = has_pointer_type(code)
    expected_prefix = f"{scope_prefix}p" if pointer else scope_prefix
    if not name.startswith(expected_prefix):
        kind = "指针变量" if pointer else "变量"
        issues.append(Issue(path, line, "error", f"{kind} {name} 应使用 {expected_prefix} 前缀"))
        return

    primitive_prefix = expected_primitive_prefix(code)
    if primitive_prefix and not pointer:
        after_scope = name[len(scope_prefix):]
        if not after_scope.startswith(primitive_prefix):
            issues.append(Issue(path, line, "warning", f"变量 {name} 建议使用 {scope_prefix}{primitive_prefix} 前缀"))


def brace_depth_before_lines(code_lines: list[str]) -> list[int]:
    depths: list[int] = []
    depth = 0
    for code in code_lines:
        depths.append(depth)
        depth += code.count("{") - code.count("}")
        depth = max(0, depth)
    return depths


def contains_unqualified_identifier(expression: str, name: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9_:.>]){re.escape(name)}\b"
    for match in re.finditer(pattern, expression):
        prefix = expression[max(0, match.start() - 2):match.start()]
        if prefix.endswith(("->", "::", ".")):
            continue
        return True
    return False


def check_identifier_name(path: Path, line: int, name: str, issues: list[Issue]) -> None:
    if not name or name in SIMPLE_NAME_EXEMPTIONS:
        return
    if name.startswith("_"):
        issues.append(Issue(path, line, "error", f"标识符 {name} 不可以下划线开头"))
    base = identifier_base(name)
    if base not in SIMPLE_NAME_EXEMPTIONS and not (4 <= len(base) <= 25):
        issues.append(Issue(path, line, "warning", f"标识符 {name} 长度建议保持在 4 到 25 个字符之间"))


def looks_like_function_definition(statement: str) -> bool:
    compact = " ".join(statement.strip().split())
    if not compact.endswith("{"):
        return False
    if compact.startswith(("if ", "for ", "while ", "switch ", "catch ", "else ", "do ")):
        return False
    if compact.startswith(("class ", "struct ", "enum ", "namespace ")):
        return False
    return bool(
        re.search(
            r"[A-Za-z_~][\w:~<>]*\s*\([^;{}]*\)\s*"
            r"(const\s*)?(override\s*)?(final\s*)?(\s*->\s*[\w:<>&*\s]+)?"
            r"(\s*:\s*.+)?\{$",
            compact,
        )
    )


def function_name_from_header(header: str) -> str:
    before_params = header.split("(", 1)[0].strip()
    return before_params.split()[-1].split("::")[-1].lstrip("~")


def looks_like_function_declaration(statement: str) -> bool:
    compact = " ".join(statement.strip().split())
    if not compact.endswith(";") or any(token in compact for token in (".", "->", "<<", ">>")):
        return False
    if compact.startswith(("return ", "if ", "for ", "while ", "switch ", "else ", "case ")):
        return False
    if compact.startswith(("using ", "typedef ", "class ", "struct ", "enum ", "namespace ")):
        return False
    if "(" not in compact or ")" not in compact:
        return False
    return bool(
        re.match(
            r"(?:static\s+|virtual\s+|inline\s+|explicit\s+|friend\s+|constexpr\s+)*"
            r"(?:[\w:~<>*&]+\s+)*"
            r"(?:operator\s*[^\s(]+|~?[A-Za-z_]\w*(?:::\w+)?)\s*"
            r"\([^;{}]*\)\s*(?:const\s*)?(?:override\s*)?(?:final\s*)?(?:=\s*(?:0|delete|default)\s*)?;",
            compact,
        )
    )


def collect_statement(code_lines: list[str], start: int, limit: int = 8) -> str:
    parts: list[str] = []
    for index in range(start, min(len(code_lines), start + limit)):
        code = code_lines[index].strip()
        if not code:
            continue
        parts.append(code)
        if ";" in code or re.search(r"(^|\s)\{\s*$", code):
            break
    return " ".join(parts)


def find_matching_brace(code_lines: list[str], start: int) -> int:
    depth = 0
    seen = False
    for index in range(start, len(code_lines)):
        line = strip_strings(code_lines[index])
        for char in line:
            if char == "{":
                depth += 1
                seen = True
            elif char == "}":
                depth -= 1
                if seen and depth == 0:
                    return index
    return start


def find_matching_function_brace(code_lines: list[str], start: int) -> int:
    body_start = start
    body_column = -1
    for index in range(start, len(code_lines)):
        line = strip_strings(code_lines[index]).rstrip()
        if re.search(r"(^|\s)\{\s*$", line):
            body_start = index
            body_column = line.rfind("{")
            break
    if body_column < 0:
        return start

    depth = 0
    for index in range(body_start, len(code_lines)):
        line = strip_strings(code_lines[index])
        cursor = body_column if index == body_start else 0
        for char in line[cursor:]:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return index
    return body_start


def collect_functions(code_lines: list[str]) -> list[FunctionInfo]:
    functions: list[FunctionInfo] = []
    brace_depth = 0
    index = 0
    while index < len(code_lines):
        statement = collect_statement(code_lines, index)
        top_level = brace_depth == 0
        if top_level and "(" in code_lines[index] and looks_like_function_definition(statement):
            end = find_matching_function_brace(code_lines, index)
            functions.append(
                FunctionInfo(
                    name=function_name_from_header(statement),
                    line=index + 1,
                    end_line=end + 1,
                    header=statement,
                    body=code_lines[index:end + 1],
                )
            )
            index = end + 1
            continue
        brace_depth += strip_strings(code_lines[index]).count("{") - strip_strings(code_lines[index]).count("}")
        brace_depth = max(0, brace_depth)
        index += 1
    return functions


def collect_function_declarations(code_lines: list[str], functions: list[FunctionInfo]) -> list[FunctionDeclInfo]:
    declarations: list[FunctionDeclInfo] = []
    function_lines = {
        line_no
        for function in functions
        for line_no in range(function.line, function.end_line + 1)
    }
    for index, code in enumerate(code_lines):
        if index + 1 in function_lines:
            continue
        if "(" not in code:
            continue
        statement = collect_statement(code_lines, index, limit=12)
        if not looks_like_function_declaration(statement):
            continue
        declarations.append(
            FunctionDeclInfo(
                name=function_name_from_header(statement),
                line=index + 1,
                header=statement,
            )
        )
    return declarations


def collect_classes(code_lines: list[str]) -> list[ClassInfo]:
    classes: list[ClassInfo] = []
    index = 0
    while index < len(code_lines):
        match = re.match(r"\s*(class|struct)\s+([A-Za-z_]\w*)\s*([^;{]*)\{", code_lines[index])
        if not match:
            index += 1
            continue
        kind, name, tail = match.groups()
        bases = re.findall(r"(?:public|protected|private)\s+([A-Za-z_]\w*)", tail)
        end = find_matching_brace(code_lines, index)
        body = [(line_no + 1, code_lines[line_no]) for line_no in range(index + 1, end)]
        classes.append(ClassInfo(name=name, line=index + 1, end_line=end + 1, kind=kind, bases=bases, body=body))
        index = end + 1
    return classes


def nonblank_code_after(code_lines: list[str], index: int) -> tuple[int, str] | None:
    for next_index in range(index + 1, len(code_lines)):
        stripped = code_lines[next_index].strip()
        if stripped:
            return next_index, stripped
    return None


def nonblank_code_before(code_lines: list[str], index: int) -> tuple[int, str] | None:
    for prev_index in range(index - 1, -1, -1):
        stripped = code_lines[prev_index].strip()
        if stripped:
            return prev_index, stripped
    return None


def is_expression_continuation(code_lines: list[str], index: int, stripped: str) -> bool:
    if not stripped or stripped.startswith("#"):
        return False
    if re.match(r"^(\.|->|::|,|\?|:|\+|-|\*|/|%|&&|\|\||&|\||\^|==|!=|<=|>=|<|>|=|\+=|-=|\*=|/=|%=)", stripped):
        return True

    before = nonblank_code_before(code_lines, index)
    if not before:
        return False
    prev = before[1].rstrip()
    if prev.endswith((",", "(", "[", "?", ":", "+", "-", "*", "/", "%", "&&", "||", "&", "|", "^", "=", "+=", "-=", "*=", "/=", "%=")):
        return True
    if prev.endswith((";", "{", "}", ":")):
        return False
    return bool(re.search(r"[,(+\-*/%&|^?:=<>]$", prev))


def lint_comments(
    path: Path,
    lines: list[str],
    code_lines: list[str],
    functions: list[FunctionInfo],
    declarations: list[FunctionDeclInfo],
    classes: list[ClassInfo],
) -> list[Issue]:
    issues: list[Issue] = []
    comment_lines, real_code_lines = count_comment_and_code_lines(lines)
    if real_code_lines and comment_lines * 3 < real_code_lines:
        issues.append(Issue(path, 1, "error", f"注释行数不足 1/3：注释 {comment_lines} 行，代码 {real_code_lines} 行"))

    header = previous_comment_block(lines, first_code_line(lines), max_gap=10)
    if not has_field_groups(header, FILE_COMMENT_FIELDS):
        severity = "warning" if has_comment_content(header) else "error"
        issues.append(Issue(path, 1, severity, "文件首部缺少完整 V1.3 文件注释字段：文件名/功能模块和目的/开发者及日期"))

    for class_info in classes:
        block = previous_comment_block(lines, class_info.line - 1)
        if not has_field_groups(block, CLASS_COMMENT_FIELDS):
            severity = "warning" if has_comment_content(block) else "error"
            issues.append(Issue(path, class_info.line, severity, f"类 {class_info.name} 前缺少完整 V1.3 类注释字段"))

    for function in functions:
        block = previous_comment_block(lines, function.line - 1)
        if not has_field_groups(block, FUNCTION_COMMENT_FIELDS):
            severity = "warning" if has_comment_content(block) else "error"
            issues.append(Issue(path, function.line, severity, f"函数 {function.name} 定义前缺少完整 V1.3 函数注释字段"))

    for declaration in declarations:
        block = previous_comment_block(lines, declaration.line - 1, max_gap=1)
        if not has_comment_content(block):
            issues.append(Issue(path, declaration.line, "warning", f"函数 {declaration.name} 声明前缺少注释说明"))

    for index, line in enumerate(code_lines):
        stripped = line.strip()
        if re.match(r"(while|for)\s*\([^)]*\)\s*;\s*$", stripped) and "//" not in lines[index]:
            issues.append(Issue(path, index + 1, "warning", "空循环体建议给出确认性注释"))
        if re.match(r"(while|for)\s*\([^)]*\)\s*\{\s*$", stripped):
            after = nonblank_code_after(code_lines, index)
            if after and after[1].startswith("}") and "//" not in lines[index] and "//" not in lines[after[0]]:
                issues.append(Issue(path, index + 1, "warning", "空循环体建议给出确认性注释"))

    return issues


def lint_format(path: Path, lines: list[str], code_lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for index, raw in enumerate(lines):
        line_no = index + 1
        code = strip_strings(code_lines[index], fill="x")
        stripped = code.strip()
        if "\t" in raw:
            issues.append(Issue(path, line_no, "error", "禁止使用 Tab 缩进；请使用 4 个空格"))
        case_label_colon = case_default_label_colon_index(code)
        has_required_case_label_trailing_space = is_case_default_label_with_trailing_label_space(code)
        if raw.rstrip() != raw and not COMMENT_DIVIDER_RE.match(raw) and not has_required_case_label_trailing_space:
            issues.append(Issue(path, line_no, "warning", "行尾存在多余空白"))
        if len(raw) > 80 and not COMMENT_DIVIDER_RE.match(raw):
            issues.append(Issue(path, line_no, "warning", "长语句建议控制在 80 字符以内"))
        leading = len(raw) - len(raw.lstrip(" "))
        if leading % 4 != 0 and stripped and not is_expression_continuation(code_lines, index, stripped):
            issues.append(Issue(path, line_no, "warning", "缩进建议按 4 个空格对齐"))
        if re.search(r"\s+;", code):
            issues.append(Issue(path, line_no, "error", "分号前不能有空格"))
        if re.search(r"\s+(\.|->|::)|(\.|->|::)\s+|\[\s+|\s+\]", code):
            issues.append(Issue(path, line_no, "error", "不要在 .、->、::、[] 前后使用空格"))
        if re.search(r",\S|\s+,", code):
            issues.append(Issue(path, line_no, "error", "逗号后应有空格，逗号前不应有空格"))
        ternary_code = code.replace("::", "  ")
        if (
            "?" in ternary_code
            and ":" in ternary_code
            and re.search(r"\S\?|\?\S|\S:|:\S", ternary_code)
        ):
            issues.append(Issue(path, line_no, "error", "三目运算符 '?' 和 ':' 前后均应有空格"))
        if re.search(r"(\+\+|--|!|~)\s+[A-Za-z_(]|\b[A-Za-z_]\w*\s+(\+\+|--)", code):
            issues.append(Issue(path, line_no, "error", "一元操作符和操作对象之间不应有空格"))
        if re.search(r"\b(if|for|while|switch)\(", code):
            issues.append(Issue(path, line_no, "error", "控制语句和后续 '(' 之间应有一个空格"))
        if re.search(r"\b(if|for|while|switch)\s*\([^)]*\)\{", code):
            issues.append(Issue(path, line_no, "error", "控制语句 ')' 与 '{' 之间应有一个空格"))
        if re.search(r"\bdo\{", code):
            issues.append(Issue(path, line_no, "error", "do 和后续 '{' 之间应有一个空格"))
        if case_label_colon is not None and not code[:case_label_colon].endswith(" "):
            issues.append(Issue(path, line_no, "error", "case/default 的 ':' 前应有一个空格"))
        if case_label_colon is not None and not code[case_label_colon + 1:].startswith(" "):
            issues.append(Issue(path, line_no, "error", "case/default 的 ':' 后应有一个空格"))
        if code.count(";") > 1 and not stripped.startswith("for "):
            issues.append(Issue(path, line_no, "error", "一行只写一条语句或标号"))
        if re.search(r"\b(char|short|int|long|float|double|bool|void)\s+[*&]", code):
            issues.append(Issue(path, line_no, "error", "声明指针/引用时 * 或 & 应与类型写在一起，如 int* Value"))
        declaration_code = strip_template_arguments(code)
        if (
            "," in declaration_code
            and ";" in declaration_code
            and "(" not in declaration_code
            and ")" not in declaration_code
            and "{" not in declaration_code
            and likely_declaration(declaration_code)
        ):
            issues.append(Issue(path, line_no, "error", "一次只声明、定义一个变量/常量"))
    return issues


def control_statement_tail(code_lines: list[str], start: int, stripped: str) -> tuple[int, str] | None:
    match = re.match(r"(if|for|while|switch)\s*\(", stripped)
    if not match:
        return None

    depth = 1
    cursor = match.end()
    for index in range(start, min(len(code_lines), start + 12)):
        line = strip_strings(code_lines[index]).strip()
        if index != start:
            cursor = 0
        while cursor < len(line):
            char = line[cursor]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return index, line[cursor + 1:].strip()
            cursor += 1
    return None


def lint_control_blocks(path: Path, code_lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for index, code in enumerate(code_lines):
        stripped = strip_strings(code).strip()
        if not stripped:
            continue
        control_tail = control_statement_tail(code_lines, index, stripped)
        if control_tail:
            end_index, tail = control_tail
            if tail:
                if not tail.startswith(("{", ";")):
                    issues.append(Issue(path, index + 1, "error", "控制语句的语句块必须使用 '{' 和 '}'"))
            else:
                after = nonblank_code_after(code_lines, end_index)
                if not after or not after[1].startswith("{"):
                    issues.append(Issue(path, index + 1, "error", "控制语句的语句块必须使用 '{' 和 '}'"))
        else_match = re.match(r"else\b\s*(.*)$", stripped)
        if else_match:
            tail = else_match.group(1).strip()
            if tail.startswith("if"):
                continue
            if tail:
                if not tail.startswith("{"):
                    issues.append(Issue(path, index + 1, "error", "else 语句块必须使用 '{' 和 '}'"))
            else:
                after = nonblank_code_after(code_lines, index)
                if not after or not after[1].startswith("{"):
                    issues.append(Issue(path, index + 1, "error", "else 语句块必须使用 '{' 和 '}'"))
        do_match = re.match(r"do\b\s*(.*)$", stripped)
        if do_match:
            tail = do_match.group(1).strip()
            if tail:
                if not tail.startswith("{"):
                    issues.append(Issue(path, index + 1, "error", "do...while 的语句块必须使用 '{' 和 '}'"))
            else:
                after = nonblank_code_after(code_lines, index)
                if not after or not after[1].startswith("{"):
                    issues.append(Issue(path, index + 1, "error", "do...while 的语句块必须使用 '{' 和 '}'"))
        if re.match(r"}\s*$", stripped):
            after = nonblank_code_after(code_lines, index)
            if after and re.match(r"while\s*\(", after[1]) and "do" in "\n".join(code_lines[max(0, index - 20):index]):
                issues.append(Issue(path, index + 1, "error", "do...while 结构中 while 前的 '}' 必须和 while 同行"))
    return issues


def lint_switches(path: Path, lines: list[str], code_lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    index = 0
    while index < len(code_lines):
        if not re.search(r"\bswitch\s*\(", code_lines[index]):
            index += 1
            continue
        end = find_matching_brace(code_lines, index)
        block = code_lines[index:end + 1]
        if not any(re.match(r"\s*default\s*:", line) for line in block):
            issues.append(Issue(path, index + 1, "error", "switch 语句必须包含 default 分支"))
        labels = [
            (offset, line)
            for offset, line in enumerate(block)
            if re.match(r"\s*(case\b.*|default)\s*:", line)
        ]
        for label_index, (offset, label_line) in enumerate(labels):
            next_offset = labels[label_index + 1][0] if label_index + 1 < len(labels) else len(block)
            segment = block[offset + 1:next_offset]
            real_segment = [line.strip() for line in segment if line.strip() and line.strip() not in {"{", "}"}]
            if not real_segment:
                continue
            has_exit = any(re.search(r"\b(break|return|throw)\b", line) for line in real_segment)
            if not has_exit:
                issues.append(Issue(path, index + offset + 1, "error", "switch 的每个非空 case 分支应以 break/return/throw 结束"))
            if label_index + 1 < len(labels) and "break" in " ".join(real_segment) and "//" not in lines[index + next_offset - 1]:
                if re.match(r"\s*case\b", label_line):
                    issues.append(Issue(path, index + offset + 1, "warning", "多个 case 共用出口时建议给出确认性注释"))
        index = end + 1
    return issues


def lint_statements(path: Path, code_lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    float_names: set[str] = set()
    bool_names: set[str] = set()
    new_targets: dict[str, tuple[int, bool]] = {}
    deleted_targets: dict[str, bool] = {}
    for index, code in enumerate(code_lines):
        stripped = strip_strings(code).strip()
        if not stripped:
            continue
        for match in re.finditer(r"\b(?:float|double)\s+[*&]?\s*([A-Za-z_]\w*)", stripped):
            float_names.add(match.group(1))
        for match in re.finditer(r"\bbool\s+([A-Za-z_]\w*)", stripped):
            bool_names.add(match.group(1))

        if re.search(r"\bgoto\b", stripped):
            issues.append(Issue(path, index + 1, "error", "禁止使用 goto 语句"))
        if not stripped.startswith("for ") and assignment_count(stripped) > 1:
            issues.append(Issue(path, index + 1, "error", "一条程序语句中只应包含一个赋值操作符"))
        lhs_match = re.match(r"\s*([A-Za-z_]\w*)\s*(?:[+\-*/%&|^<>]?=)\s*(.*);", stripped)
        if lhs_match and (contains_unqualified_identifier(lhs_match.group(2), lhs_match.group(1)) or re.search(r"\+\+|--", lhs_match.group(2))):
            issues.append(Issue(path, index + 1, "warning", "赋值表达式中同一左值不应重复出现或再次被赋值"))
        condition_match = re.match(r"\s*(if|while|for|switch)\s*\((.*)\)", stripped)
        if condition_match and ASSIGNMENT_RE.search(condition_match.group(2).replace("==", "")):
            issues.append(Issue(path, index + 1, "warning", "不要在控制语句的条件表达式中使用赋值操作符"))
        if "==" in stripped or "!=" in stripped:
            if re.search(r"\d+\.\d+", stripped) or any(re.search(rf"\b{name}\b", stripped) for name in float_names):
                issues.append(Issue(path, index + 1, "error", "不要对浮点数做等于/不等于精确比较"))
        pointer_decl = re.search(r"\b(?:char|short|int|long|float|double|bool|void|[A-Z]\w*)\*+\s+([A-Za-z_]\w*)\s*;", stripped)
        if pointer_decl:
            issues.append(Issue(path, index + 1, "error", "定义指针变量/常量时必须同时初始化，不能悬空声明"))
        for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(([^()]*)\)", stripped):
            call_name = call.group(1)
            if call_name in CONTROL_KEYWORDS or likely_function_declaration(stripped):
                continue
            if any(assignment_count(param) > 0 for param in split_parameters(call.group(2))):
                issues.append(Issue(path, index + 1, "warning", "函数调用参数列表中不应使用赋值操作符"))
                break
        new_match = re.search(r"\b([A-Za-z_]\w*)\s*=\s*new\b([^;]*)", stripped)
        if new_match:
            new_targets[new_match.group(1)] = (index + 1, "[" in new_match.group(2))
        delete_match = re.search(r"\bdelete(\s*\[\s*\])?\s+([A-Za-z_]\w*)\s*;", stripped)
        if delete_match:
            name = delete_match.group(2)
            deleted_targets[name] = delete_match.group(1) is not None
            lookahead = "\n".join(code_lines[index + 1:index + 4])
            if not re.search(rf"\b{name}\s*=\s*nullptr\s*;", lookahead):
                issues.append(Issue(path, index + 1, "warning", "delete 后若指针仍在生命周期内，建议立即赋值为 nullptr"))
        for name in bool_names:
            if re.search(rf"\b(if|while|for)\s*\(\s*{name}\s*\)", stripped):
                issues.append(Issue(path, index + 1, "warning", "布尔表达式建议写成显式比较，如 Flag == true"))
    for name, (line, is_array_new) in new_targets.items():
        if name not in deleted_targets:
            issues.append(Issue(path, line, "warning", f"局部 new 出来的指针 {name} 未在同文件中看到 delete，请确认 new/delete 成对"))
        elif deleted_targets[name] != is_array_new:
            issues.append(Issue(path, line, "error", f"指针 {name} 的 new/delete 与 new[]/delete[] 形式必须对应"))
    return issues


def lint_names(path: Path, code_lines: list[str], functions: list[FunctionInfo], classes: list[ClassInfo]) -> list[Issue]:
    issues: list[Issue] = []
    seen_lower: dict[str, tuple[str, int]] = {}
    depths = brace_depth_before_lines(code_lines)
    class_lines = {
        line_no
        for class_info in classes
        for line_no in range(class_info.line, class_info.end_line + 1)
    }
    global_names: dict[str, int] = {}

    for class_info in classes:
        check_identifier_name(path, class_info.line, class_info.name, issues)
        if not class_info.name[0].isupper():
            issues.append(Issue(path, class_info.line, "error", f"自定义类型名 {class_info.name} 应以大写字母开头"))

    for function in functions:
        name = function.name
        if name and name not in {"operator", "main"} and not name.startswith("operator"):
            check_identifier_name(path, function.line, name, issues)
            if name and not name[0].isupper():
                issues.append(Issue(path, function.line, "error", f"函数名 {name} 应以大写字母开头"))
            if function.header.strip().startswith("bool ") and not name.startswith(("Is", "Has")):
                issues.append(Issue(path, function.line, "error", f"bool 类型函数 {name} 必须以 Is 或 Has 等开头"))

    for index, code in enumerate(code_lines):
        stripped = strip_strings(code).strip()
        line_no = index + 1
        if not stripped:
            continue
        type_match = re.match(r"\s*(?:typedef\s+.*\s+|using\s+|namespace\s+|(?:enum(?:\s+class)?|union)\s+)([A-Za-z_]\w*)", stripped)
        if type_match:
            type_name = type_match.group(1)
            check_identifier_name(path, line_no, type_name, issues)
            if not type_name[0].isupper():
                issues.append(Issue(path, line_no, "error", f"自定义类型名 {type_name} 应以大写字母开头"))
        macro = re.match(r"\s*#\s*define\s+([A-Za-z_]\w*)", stripped)
        if macro:
            name = macro.group(1)
            if name.upper() != name:
                issues.append(Issue(path, line_no, "error", f"宏 {name} 应全部大写"))
        const_decl = re.match(r"\s*(?:static\s+)?(?:const|constexpr)\b", stripped)
        if const_decl and ";" in stripped and "(" not in stripped and "&" not in stripped:
            name = extract_declared_name(stripped) or ""
            if name.upper() != name:
                issues.append(Issue(path, line_no, "warning", f"常量 {name} 按 V1.3 应全部大写"))
        bool_decl = re.match(r"\s*bool\s+([A-Za-z_]\w*)\s*(?:[=;])", stripped) if "(" not in stripped else None
        if bool_decl:
            bool_name = bool_decl.group(1)
            bool_base = bool_name[2:] if bool_name.startswith("m_") else bool_name
            if not bool_base.startswith(("Is", "Has")):
                issues.append(Issue(path, line_no, "error", f"bool 变量 {bool_name} 必须以 Is 或 Has 等开头"))
        is_variable_declaration = is_probable_variable_declaration(stripped)
        decl_name = extract_declared_name(stripped) if is_variable_declaration and "(" not in stripped else None
        if decl_name:
            check_identifier_name(path, line_no, decl_name, issues)
            is_class_line = line_no in class_lines
            if not is_class_line:
                if depths[index] == 0 and not stripped.startswith(("const ", "constexpr ")):
                    if stripped.startswith("static "):
                        check_scoped_variable_name(path, line_no, stripped, decl_name, "m_", issues)
                    elif not stripped.startswith("extern "):
                        check_scoped_variable_name(path, line_no, stripped, decl_name, "g_", issues)
                        global_names[decl_name] = line_no
                elif depths[index] > 0 and stripped.startswith("static "):
                    check_scoped_variable_name(path, line_no, stripped, decl_name, "s_", issues)
                if depths[index] > 0 and decl_name in global_names:
                    issues.append(
                        Issue(path, line_no, "error", f"局部变量 {decl_name} 不应与全局变量重名，全局变量在第 {global_names[decl_name]} 行")
                    )
            lowered = decl_name.lower()
            if lowered in seen_lower and seen_lower[lowered][0] != decl_name:
                prev_name, prev_line = seen_lower[lowered]
                issues.append(
                    Issue(path, line_no, "error", f"不要只用大小写区分标识符：{prev_name}({prev_line}) 与 {decl_name}")
                )
            seen_lower[lowered] = (decl_name, line_no)
    return issues


def lint_declarations(path: Path, code_lines: list[str], functions: list[FunctionInfo]) -> list[Issue]:
    issues: list[Issue] = []
    for index, code in enumerate(code_lines):
        stripped = code.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if likely_function_declaration(stripped):
            params_match = re.search(r"\((.*)\)", stripped)
            if params_match:
                for param in split_parameters(params_match.group(1)):
                    clean = param.replace("=", " = ").split("=")[0].strip()
                    if clean and clean != "void" and re.match(r"^(const\s+)?[\w:<>]+\s*[*&]?$", clean):
                        issues.append(Issue(path, index + 1, "error", "函数声明和定义的参数列表中应同时写类型和名称"))
    for function in functions:
        code_count = sum(1 for line in function.body if line.strip() and line.strip() not in {"{", "}"})
        if code_count > 100:
            issues.append(Issue(path, function.line, "error", f"函数体代码长度超过 100 行：{code_count} 行"))
    return issues


def lint_file_organization(path: Path, code_lines: list[str], classes: list[ClassInfo], functions: list[FunctionInfo]) -> list[Issue]:
    issues: list[Issue] = []
    if path.suffix in HEADER_SUFFIXES:
        directives = [line.strip() for line in code_lines if line.strip().startswith("#")]
        ifndef = next((line for line in directives if line.startswith("#ifndef")), "")
        if not ifndef:
            ifndef = next((line for line in directives if re.match(r"#\s*if\s+!\s*defined", line)), "")
        define = next((line for line in directives if line.startswith("#define")), "")
        if not ifndef or not define:
            issues.append(Issue(path, 1, "error", "头文件必须使用 include guard 防止重复包含"))
        else:
            guard_match = re.search(r"#\s*ifndef\s+([A-Za-z_]\w*)|defined\s*\(?\s*([A-Za-z_]\w*)\s*\)?", ifndef)
            guard_name = next((group for group in (guard_match.groups() if guard_match else ()) if group), "")
            define_name = define.split()[1] if len(define.split()) > 1 else ""
            if guard_name != define_name:
                issues.append(Issue(path, 1, "error", "include guard 的 #ifndef 与 #define 宏名必须一致"))
            if guard_name and guard_name != expected_guard(path):
                issues.append(Issue(path, 1, "warning", f"include guard 建议使用文件名大写形式：{expected_guard(path)}"))
        if len(classes) > 1:
            issues.append(Issue(path, classes[1].line, "error", "按 V1.3，一个头文件中只应声明一个类"))
        if classes and path.stem != classes[0].name:
            issues.append(Issue(path, classes[0].line, "warning", f"类文件名建议与类名一致：{classes[0].name}.hpp"))
        declaration_count = sum(1 for line in code_lines if likely_function_declaration(line.strip()))
        if declaration_count > 1 and not classes:
            issues.append(Issue(path, 1, "warning", "头文件中包含多个函数声明，请确认它们属于同一类功能"))
        depths = brace_depth_before_lines(code_lines)
        for index, code in enumerate(code_lines):
            stripped = code.strip()
            if depths[index] == 0 and is_probable_variable_declaration(stripped):
                if not stripped.startswith(("extern ", "const ", "constexpr ", "static const ", "static constexpr ")):
                    issues.append(Issue(path, index + 1, "error", "头文件中不应包含全局变量定义"))
        for function in functions:
            if not re.search(r"\b(template|inline)\b", function.header):
                issues.append(Issue(path, function.line, "error", "头文件中不应包含普通函数定义"))

    if path.suffix in IMPLEMENTATION_SUFFIXES:
        if len(classes) > 0:
            issues.append(Issue(path, classes[0].line, "error", "源文件中不应声明类，类声明应统一放到头文件"))
        for index, code in enumerate(code_lines):
            stripped = code.strip()
            if re.match(r"#\s*include\s+[\"<].*\.(cpp|cc|cxx)[\">]", stripped):
                issues.append(Issue(path, index + 1, "error", "只允许头文件被包含，不要 include 源文件"))
            if likely_function_declaration(stripped):
                issues.append(Issue(path, index + 1, "warning", "源文件中不应放函数声明，声明应放到头文件"))
        if len(functions) > 1:
            prefixes = {re.sub(r"(Constructor|Destructor|Get|Set|Is|Has|Print|Read|Write|Load|Save|Init|Run)", "", function.name, count=1) for function in functions}
            if len(prefixes) > 3:
                issues.append(Issue(path, 1, "warning", "源文件中实现了多个函数，请确认它们属于同一类功能"))
    return issues


def lint_classes(path: Path, classes: list[ClassInfo]) -> list[Issue]:
    issues: list[Issue] = []
    base_names = {base for class_info in classes for base in class_info.bases}
    for class_info in classes:
        access = "private" if class_info.kind == "class" else "public"
        has_default_ctor = False
        has_copy_ctor = False
        has_assignment = False
        has_destructor = False
        destructor_virtual = False
        has_operator_new = False
        has_operator_delete = False
        public_data_seen = False
        has_inherited_ctor = False
        if len(class_info.bases) > 1:
            issues.append(Issue(path, class_info.line, "warning", f"类 {class_info.name} 使用了多继承，请确认有充分理由"))
        inline_body_depth = 0
        pending_inline_body = False
        for line_no, code in class_info.body:
            stripped = code.strip()
            stripped_no_strings = strip_strings(stripped)
            if inline_body_depth > 0:
                inline_body_depth += stripped_no_strings.count("{") - stripped_no_strings.count("}")
                inline_body_depth = max(0, inline_body_depth)
                continue
            if pending_inline_body and "{" in stripped_no_strings:
                pending_inline_body = False
                inline_body_depth = stripped_no_strings.count("{") - stripped_no_strings.count("}")
                inline_body_depth = max(0, inline_body_depth)
                continue
            if pending_inline_body and stripped.rstrip().endswith(";"):
                pending_inline_body = False
            access_match = re.match(r"(public|private|protected)\s*:", stripped)
            if access_match:
                access = access_match.group(1)
                continue
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("friend "):
                continue
            if re.match(r"using\s+\w+::\w+\s*;", stripped):
                has_inherited_ctor = True
            if re.search(rf"\b{class_info.name}\s*\(\s*\)", stripped) or re.search(
                rf"\b{class_info.name}\s*\([^)]*=", stripped
            ):
                has_default_ctor = True
            if re.search(rf"\b{class_info.name}\s*\(\s*const\s+{class_info.name}\s*&", stripped):
                has_copy_ctor = True
            if re.search(r"\boperator\s*=\s*\(", stripped):
                has_assignment = True
            if re.search(rf"~{class_info.name}\s*\(", stripped):
                has_destructor = True
                if "virtual" in stripped:
                    destructor_virtual = True
            if re.search(r"\boperator\s+new\b", stripped):
                has_operator_new = True
            if re.search(r"\boperator\s+delete\b", stripped):
                has_operator_delete = True
            if "(" in stripped and ")" in stripped and "{" in stripped_no_strings:
                inline_body_depth = stripped_no_strings.count("{") - stripped_no_strings.count("}")
                inline_body_depth = max(0, inline_body_depth)
            elif "(" in stripped and not stripped.rstrip().endswith(";") and "{" not in stripped_no_strings:
                pending_inline_body = True
            if ";" in stripped and "(" not in stripped and ")" not in stripped and not stripped.startswith(("using ", "typedef ", "static_assert")):
                member_name = extract_declared_name(stripped)
                is_static_member = re.search(r"\bstatic\b", stripped) is not None
                if access in {"private", "protected"} and member_name and not is_static_member and not member_name.startswith("m_"):
                    issues.append(Issue(path, line_no, "error", f"{access} 数据成员 {member_name} 应使用 m_ 前缀"))
                if access in {"private", "protected"} and member_name and has_pointer_type(stripped) and not member_name.startswith("m_p"):
                    issues.append(Issue(path, line_no, "error", f"{access} 指针数据成员 {member_name} 应使用 m_p 前缀"))
                if access in {"private", "protected"} and member_name and not has_pointer_type(stripped):
                    primitive_prefix = expected_primitive_prefix(stripped)
                    if primitive_prefix and member_name.startswith("m_") and not member_name[2:].startswith(primitive_prefix):
                        issues.append(Issue(path, line_no, "warning", f"数据成员 {member_name} 建议使用 m_{primitive_prefix} 前缀"))
                if access == "public":
                    is_const_ref = "const" in stripped and "&" in stripped
                    if not is_const_ref:
                        public_data_seen = True
                        issues.append(Issue(path, line_no, "error", "类中不应有 public 数据成员，除非是无读写规则的 public 常引用"))
        if public_data_seen:
            issues.append(Issue(path, class_info.line, "error", f"类 {class_info.name} 对外接口应功能化，不应暴露 public 数据成员"))
        if not has_default_ctor and not has_inherited_ctor:
            issues.append(Issue(path, class_info.line, "error", f"类 {class_info.name} 应显式定义默认构造函数，除非明确禁止默认构造"))
        if not has_copy_ctor:
            issues.append(Issue(path, class_info.line, "error", f"类 {class_info.name} 应显式定义拷贝构造函数，或显式 = delete"))
        if not has_assignment:
            issues.append(Issue(path, class_info.line, "error", f"类 {class_info.name} 应显式重载 operator=，或显式 = delete"))
        if not has_destructor:
            issues.append(Issue(path, class_info.line, "error", f"类 {class_info.name} 应显式定义析构函数"))
        if class_info.name in base_names and has_destructor and not destructor_virtual:
            issues.append(Issue(path, class_info.line, "error", f"作为基类使用的 {class_info.name} 析构函数必须为 virtual"))
        if has_operator_new and not has_operator_delete:
            issues.append(Issue(path, class_info.line, "error", "重载 operator new 时也应该重载 operator delete"))
    return issues


def lint_misc(path: Path, lines: list[str], code_lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for index, code in enumerate(code_lines):
        stripped = code.strip()
        if re.match(r"\s*#\s*define\s+\w+\s+[^(\n]+$", stripped):
            issues.append(Issue(path, index + 1, "error", "无参数宏常量应改用 const/constexpr 常量"))
        if re.match(r"\s*#\s*define\s+\w+\s*\(", stripped):
            issues.append(Issue(path, index + 1, "error", "有参数宏应优先改用 inline 函数"))
        if not stripped.startswith(("if ", "for ", "while ", "switch ")) and re.search(r"\([A-Za-z_]\w*(\s*\*)?\)\s*[A-Za-z_]\w*", stripped):
            issues.append(Issue(path, index + 1, "warning", "类型转换建议使用 C++ 风格 cast，如 static_cast"))
        raw = lines[index].strip()
        if raw.startswith("//") and re.search(r";\s*$|\{\s*$", raw):
            issues.append(Issue(path, index + 1, "warning", "不再使用的代码不要长期注释保留，应及时清理或移到备份"))
    return issues


def lint_file(path: Path) -> list[Issue]:
    text = read_text(path)
    lines = text.splitlines()
    code_lines = code_lines_without_comments(lines)
    functions = collect_functions(code_lines)
    declarations = collect_function_declarations(code_lines, functions)
    classes = collect_classes(code_lines)
    issues: list[Issue] = []
    issues.extend(lint_comments(path, lines, code_lines, functions, declarations, classes))
    issues.extend(lint_format(path, lines, code_lines))
    issues.extend(lint_control_blocks(path, code_lines))
    issues.extend(lint_switches(path, lines, code_lines))
    issues.extend(lint_statements(path, code_lines))
    issues.extend(lint_names(path, code_lines, functions, classes))
    issues.extend(lint_declarations(path, code_lines, functions))
    issues.extend(lint_file_organization(path, code_lines, classes, functions))
    issues.extend(lint_classes(path, classes))
    issues.extend(lint_misc(path, lines, code_lines))
    return sorted(issues, key=lambda issue: (issue.path.as_posix(), issue.line, issue.message))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lint C++ source files against the OOP course style rules."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to lint. Defaults to the repository root.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Project root used for relative output and default search.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Path to write the full lint report. Defaults to oop-lint-report.txt under --root.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Do not write a report file.",
    )
    parser.add_argument(
        "--max-output",
        type=int,
        default=10,
        help="Maximum number of issues printed to the terminal. The report still contains all issues.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global ROOT

    args = parse_args(sys.argv[1:] if argv is None else argv)
    ROOT = args.root.resolve()
    targets = [
        path.resolve() if path.is_absolute() else (ROOT / path).resolve()
        for path in args.paths
    ]

    issues: list[Issue] = []
    for path in iter_source_files(targets):
        issues.extend(lint_file(path))

    errors = sum(1 for issue in issues if issue.severity == "error")
    warnings = sum(1 for issue in issues if issue.severity == "warning")
    summary = f"C++ style lint: {errors} error(s), {warnings} warning(s)"

    report_path: Path | None = None
    if not args.no_report:
        report_path = args.report or (ROOT / "oop-lint-report.txt")
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_lines = [issue.format() for issue in issues]
        report_lines.append("")
        report_lines.append(summary)
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    max_output = max(0, args.max_output)
    for issue in issues[:max_output]:
        print(issue.format())

    hidden = len(issues) - max_output
    if hidden > 0:
        print(f"... {hidden} more issue(s) hidden from terminal output")
    if report_path is not None:
        print(f"Full report: {report_path}")

    print(f"\n{summary}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
