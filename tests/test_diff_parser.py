from app.github.diff_parser import DiffParser, should_skip_file


def test_should_skip_files():
    assert should_skip_file("package-lock.json") is True
    assert should_skip_file("poetry.lock") is True
    assert should_skip_file("assets/image.png") is True
    assert should_skip_file("bundle.min.js") is True
    assert should_skip_file("src/main.py") is False


def test_parse_diff():
    raw_diff = """diff --git a/app/main.py b/app/main.py
index 1111111..2222222 100644
--- a/app/main.py
+++ b/app/main.py
@@ -10,4 +10,5 @@ def run():
     x = 1
+    y = 2
     return x
"""
    result = DiffParser.parse(raw_diff)
    assert "app/main.py" in result
    hunks = result["app/main.py"]
    assert len(hunks) == 1
    added = hunks[0].added_lines
    assert len(added) == 1
    assert added[0][1].strip() == "y = 2"
