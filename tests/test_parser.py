from app.indexing.parser import CodeParser


def test_parse_python_ast():
    sample_code = """
import os
from math import sqrt

class UserService:
    def get_user(self, user_id):
        return os.getenv("DB_URL")

def calculate(val):
    res = sqrt(val)
    return res
"""
    entities = CodeParser.parse_python("services/user.py", sample_code)
    names = [e.name for e in entities]
    assert "UserService" in names
    assert "get_user" in names
    assert "calculate" in names

    calc_entity = next(e for e in entities if e.name == "calculate")
    assert "sqrt" in calc_entity.calls
    assert "os" in calc_entity.imports
