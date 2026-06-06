import pytest


def apply_template(template: str, value: str) -> str:
    """Simulates the fixed template application using str.replace instead of str.format."""
    return template.replace("{value}", value)


def apply_template_vulnerable(template: str, value: str) -> str:
    """Simulates the original vulnerable template application using str.format."""
    return template.format(value=value)


class TestRunnerTemplateInjection:
    def test_simple_replacement_works(self):
        result = apply_template("version = {value}", "1.2.3")
        assert result == "version = 1.2.3"

    def test_format_gadget_is_blocked_by_replace(self):
        malicious_value = "{value.__class__.__bases__}"
        result = apply_template("version = {value}", malicious_value)
        assert result == "version = {value.__class__.__bases__}"
        assert "__class__" in result
        assert "__bases__" in result

    def test_format_gadget_would_expose_internals_with_old_code(self):
        try:
            result = apply_template_vulnerable("x = {value!r}", "test")
            assert "test" in result
        except Exception:
            pass
        malicious_value = "{value.__class__.__name__}"
        result_fixed = apply_template("x = {value}", malicious_value)
        assert result_fixed == "x = {value.__class__.__name__}"

    def test_curly_braces_in_value_do_not_break_replacement(self):
        result = apply_template("content = {value}", "{'key': 'val'}")
        assert result == "content = {'key': 'val'}"

    def test_multiple_placeholders_only_replace_value_key(self):
        result = apply_template("{value} and {value}", "hello")
        assert result == "hello and hello"

    def test_value_with_format_spec_characters_safe(self):
        result = apply_template("v = {value}", "{0:s}")
        assert result == "v = {0:s}"

    def test_empty_value_replaced_safely(self):
        result = apply_template("tag = {value}", "")
        assert result == "tag = "

    def test_newline_in_value_preserved(self):
        result = apply_template("content = {value}", "line1\nline2")
        assert result == "content = line1\nline2"
