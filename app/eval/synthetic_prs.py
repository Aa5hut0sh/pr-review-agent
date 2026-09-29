from typing import Any

from pydantic import BaseModel


class SyntheticPR(BaseModel):
    id: str
    title: str
    description: str
    changed_files: list[str]
    diff: str
    ground_truth_bugs: list[dict[str, Any]]


SYNTHETIC_BENCHMARK_SUITE: list[SyntheticPR] = [
    SyntheticPR(
        id="pr-101-off-by-one",
        title="feat: add pagination helper for user listing",
        description="Implements page slice pagination helper for the API.",
        changed_files=["api/pagination.py"],
        diff="""diff --git a/api/pagination.py b/api/pagination.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/api/pagination.py
@@ -1,10 +1,10 @@
 def paginate_items(items: list, page: int, page_size: int = 10) -> list:
     \"\"\"Paginate a list of items based on page number and page size.\"\"\"
-    start_index = (page - 1) * page_size
-    end_index = start_index + page_size
+    start_index = page * page_size
+    end_index = start_index + page_size + 1
     return items[start_index:end_index]
""",
        ground_truth_bugs=[
            {
                "file": "api/pagination.py",
                "line": 4,
                "category": "bug",
                "type": "off_by_one",
                "description": "0-based indexing skipped first page and end_index has +1 off-by-one error",
            }
        ],
    ),
    SyntheticPR(
        id="pr-102-missing-auth",
        title="feat: add internal user deletion endpoint",
        description="Adds an endpoint to remove deactivated users.",
        changed_files=["api/users.py"],
        diff="""diff --git a/api/users.py b/api/users.py
index 1111111..2222222 100644
--- a/api/users.py
+++ b/api/users.py
@@ -20,6 +20,13 @@ async def get_user_profile(user_id: str):
     return db.fetch_user(user_id)

+@router.delete("/users/{user_id}")
+async def delete_user(user_id: str):
+    # Missing authorization check to ensure caller is an admin
+    db.delete_user_record(user_id)
+    return {"status": "deleted"}
""",
        ground_truth_bugs=[
            {
                "file": "api/users.py",
                "line": 23,
                "category": "security",
                "type": "missing_auth",
                "description": "Missing authorization check before deleting user record",
            }
        ],
    ),
    SyntheticPR(
        id="pr-103-sql-injection",
        title="feat: custom search filter for orders",
        description="Allows dynamic searching by customer keyword.",
        changed_files=["db/orders.py"],
        diff="""diff --git a/db/orders.py b/db/orders.py
index 3333333..4444444 100644
--- a/db/orders.py
+++ b/db/orders.py
@@ -15,6 +15,11 @@ def search_orders(query_str: str):
-    cursor.execute("SELECT * FROM orders WHERE status = %s", (query_str,))
+    raw_query = f"SELECT * FROM orders WHERE customer_name LIKE '%{query_str}%'"
+    cursor.execute(raw_query)
     return cursor.fetchall()
""",
        ground_truth_bugs=[
            {
                "file": "db/orders.py",
                "line": 16,
                "category": "security",
                "type": "sql_injection",
                "description": "SQL string formatting introduces SQL injection vulnerability",
            }
        ],
    ),
    SyntheticPR(
        id="pr-104-clean-refactor",
        title="refactor: improve docstrings and variable names in math utils",
        description="Clean documentation and rename temp variable.",
        changed_files=["utils/math_utils.py"],
        diff="""diff --git a/utils/math_utils.py b/utils/math_utils.py
index 5555555..6666666 100644
--- a/utils/math_utils.py
+++ b/utils/math_utils.py
@@ -5,7 +5,7 @@ def calculate_geometric_mean(numbers: list[float]) -> float:
     \"\"\"Calculate the geometric mean of a list of positive numbers.\"\"\"
     if not numbers:
         return 0.0
-    t = 1.0
-    for n in numbers:
-        t *= n
-    return t ** (1.0 / len(numbers))
+    product = 1.0
+    for num in numbers:
+        product *= num
+    return product ** (1.0 / len(numbers))
""",
        ground_truth_bugs=[],  # Intentionally zero bugs (tests false positive rate!)
    ),
]
