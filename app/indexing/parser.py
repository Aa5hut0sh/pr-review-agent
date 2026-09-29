import ast
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class CodeEntity(BaseModel):
    name: str
    entity_type: str  # function, class, method, module
    file_path: str
    start_line: int
    end_line: int
    code: str
    docstring: Optional[str] = None
    calls: List[str] = []
    imports: List[str] = []


class CodeParser:
    """
    Parses source code into semantic entities (Functions, Classes, Methods)
    with dependency tracking (calls, imports) for Graph and Vector indexing.
    """

    @classmethod
    def parse_python(cls, file_path: str, source_code: str) -> List[CodeEntity]:
        entities: List[CodeEntity] = []
        lines = source_code.splitlines()

        try:
            tree = ast.parse(source_code, filename=file_path)
        except Exception:
            # Fallback to naive chunking if syntax error or non-valid python
            return cls.parse_generic(file_path, source_code)

        # 1. Collect module-level imports
        file_imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    file_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    file_imports.append(f"{module}.{alias.name}")

        # 2. Extract functions, classes, and methods
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls = []
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call):
                        if isinstance(subnode.func, ast.Name):
                            calls.append(subnode.func.id)
                        elif isinstance(subnode.func, ast.Attribute):
                            calls.append(subnode.func.attr)

                start = node.lineno
                end = getattr(node, "end_lineno", start)
                snippet = "\n".join(lines[start - 1 : end])

                entities.append(
                    CodeEntity(
                        name=node.name,
                        entity_type="function",
                        file_path=file_path,
                        start_line=start,
                        end_line=end,
                        code=snippet,
                        docstring=ast.get_docstring(node),
                        calls=list(set(calls)),
                        imports=file_imports,
                    )
                )

            elif isinstance(node, ast.ClassDef):
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                snippet = "\n".join(lines[start - 1 : end])

                entities.append(
                    CodeEntity(
                        name=node.name,
                        entity_type="class",
                        file_path=file_path,
                        start_line=start,
                        end_line=end,
                        code=snippet,
                        docstring=ast.get_docstring(node),
                        calls=[],
                        imports=file_imports,
                    )
                )

        return entities

    @classmethod
    def parse_generic(cls, file_path: str, source_code: str) -> List[CodeEntity]:
        """
        Regex-based chunker for languages when AST is not applicable.
        """
        entities: List[CodeEntity] = []
        lines = source_code.splitlines()

        # Simple function pattern for JS/TS/Go/Java
        fn_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+([A-Za-z0-9_]+)|def\s+([A-Za-z0-9_]+)|const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\()")
        
        current_chunk: List[str] = []
        current_start = 1
        current_name = "block"

        for idx, line in enumerate(lines, start=1):
            match = fn_pattern.match(line)
            if match:
                if current_chunk:
                    entities.append(
                        CodeEntity(
                            name=current_name,
                            entity_type="code_block",
                            file_path=file_path,
                            start_line=current_start,
                            end_line=idx - 1,
                            code="\n".join(current_chunk),
                        )
                    )
                    current_chunk = []
                current_start = idx
                current_name = next(name for name in match.groups() if name is not None)
            current_chunk.append(line)

        if current_chunk:
            entities.append(
                CodeEntity(
                    name=current_name,
                    entity_type="code_block",
                    file_path=file_path,
                    start_line=current_start,
                    end_line=len(lines),
                    code="\n".join(current_chunk),
                )
            )

        return entities

    @classmethod
    def parse_file(cls, file_path: str, source_code: str) -> List[CodeEntity]:
        if file_path.endswith(".py"):
            return cls.parse_python(file_path, source_code)
        return cls.parse_generic(file_path, source_code)
