import re
from typing import List, Dict, Any, Tuple
from app.core.models import DiffHunk

IGNORED_EXTENSIONS = {
    ".lock", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf",
    ".zip", ".tar", ".gz", ".pyc", ".whl", ".min.js", ".min.css", ".map"
}

IGNORED_FILES = {
    "package-lock.json", "yarn.lock", "poetry.lock", "pnpm-lock.yaml",
    "Cargo.lock", "go.sum", "Pipfile.lock", "composer.lock"
}


def should_skip_file(file_path: str) -> bool:
    """
    Skip lockfiles, generated files, vendored code, and binaries.
    """
    for ignored in IGNORED_FILES:
        if file_path.endswith(ignored):
            return True
    for ext in IGNORED_EXTENSIONS:
        if file_path.endswith(ext):
            return True
    if "/vendor/" in file_path or "/node_modules/" in file_path or "/.git/" in file_path:
        return True
    return False


class DiffParser:
    """
    Unified diff parser that extracts per-file changes, hunk line ranges,
    and maps added/modified lines for accurate inline comment anchoring.
    """

    @classmethod
    def parse(cls, raw_diff: str) -> Dict[str, List[DiffHunk]]:
        file_hunks: Dict[str, List[DiffHunk]] = {}
        current_file: str = ""
        current_hunk: DiffHunk | None = None

        hunk_header_regex = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$")

        for line in raw_diff.splitlines():
            if line.startswith("diff --git"):
                current_hunk = None
                # Try to extract from diff --git a/path b/path
                parts = line.split(" ")
                if len(parts) >= 4 and parts[3].startswith("b/"):
                    candidate = parts[3][2:].strip()
                    if not should_skip_file(candidate):
                        current_file = candidate
                        if current_file not in file_hunks:
                            file_hunks[current_file] = []
                    else:
                        current_file = ""
                else:
                    current_file = ""
            elif line.startswith("+++ b/"):
                filepath = line[6:].strip()
                if not should_skip_file(filepath):
                    current_file = filepath
                    if current_file not in file_hunks:
                        file_hunks[current_file] = []
                else:
                    current_file = ""
            elif current_file and line.startswith("@@"):
                match = hunk_header_regex.match(line)
                if match:
                    old_start = int(match.group(1))
                    new_start = int(match.group(2))
                    current_hunk = DiffHunk(
                        file=current_file,
                        old_start=old_start,
                        new_start=new_start,
                        hunk_header=line,
                        diff_lines=[],
                        added_lines=[],
                    )
                    file_hunks[current_file].append(current_hunk)
            elif current_hunk is not None:
                current_hunk.diff_lines.append(line)
                # Keep track of line numbers for lines in the new file
                if line.startswith("+"):
                    # Current line number in the new file
                    # Count existing + and space lines in this hunk
                    line_offset = sum(
                        1 for l in current_hunk.diff_lines[:-1]
                        if l.startswith("+") or l.startswith(" ")
                    )
                    target_line = current_hunk.new_start + line_offset
                    current_hunk.added_lines.append((target_line, line[1:]))

        return file_hunks
