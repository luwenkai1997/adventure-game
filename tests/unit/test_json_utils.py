import pytest
from app.utils.json_utils import parse_json_response

def test_parse_json_response_clean():
    clean_json = '{"key": "value"}'
    result = parse_json_response(clean_json)
    assert result == {"key": "value"}

def test_parse_json_response_with_markdown():
    markdown_json = "```json\n{\"test\": 123}\n```"
    result = parse_json_response(markdown_json)
    assert result == {"test": 123}

def test_parse_json_response_missing_brace():
    # json_utils in this project usually auto-repairs missing trailing braces
    broken_json = '{"partial": "data"'
    try:
        result = parse_json_response(broken_json)
        assert result.get("partial") == "data"
    except Exception:
        pytest.fail("Failed to repair missing brace JSON")
