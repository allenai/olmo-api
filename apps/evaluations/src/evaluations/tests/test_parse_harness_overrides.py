"""Tests for parse_harness_overrides function."""

import pytest

from evaluations.configs.base import parse_harness_overrides


class TestParseHarnessOverrides:
    """Tests for parsing harness override strings."""

    def test_single_override(self):
        """Single key:value pair parses correctly."""
        result = parse_harness_overrides("metrics.enabled:true")
        assert result == {"metrics.enabled": "true"}

    def test_multiple_overrides(self):
        """Multiple semicolon-separated pairs parse correctly."""
        result = parse_harness_overrides("metrics.enabled:true;limit:10;batch_size:4")
        assert result == {
            "metrics.enabled": "true",
            "limit": "10",
            "batch_size": "4",
        }

    def test_whitespace_handling(self):
        """Whitespace around keys and values is stripped."""
        result = parse_harness_overrides("  key1 : value1 ; key2 : value2  ")
        assert result == {"key1": "value1", "key2": "value2"}

    def test_empty_string(self):
        """Empty string returns empty dict."""
        result = parse_harness_overrides("")
        assert result == {}

    def test_value_with_colons(self):
        """Values containing colons are preserved (split on first colon only)."""
        result = parse_harness_overrides("url:http://example.com:8080")
        assert result == {"url": "http://example.com:8080"}

    def test_dotted_keys(self):
        """Dotted config path keys work correctly."""
        result = parse_harness_overrides("provider.model:gpt-4;metrics.reporters:[console]")
        assert result == {
            "provider.model": "gpt-4",
            "metrics.reporters": "[console]",
        }


class TestParseHarnessOverridesValidationErrors:
    """Tests for error handling in parse_harness_overrides."""

    def test_missing_colon_raises_error(self):
        """Missing colon delimiter raises ValueError."""
        with pytest.raises(ValueError, match="missing ':' delimiter"):
            parse_harness_overrides("invalid_no_colon")

    def test_missing_colon_second_arg_raises_error(self):
        """Error in second override is caught."""
        with pytest.raises(ValueError, match="invalid_no_colon"):
            parse_harness_overrides("valid:ok;invalid_no_colon")

    def test_empty_key_raises_error(self):
        """Empty key raises ValueError."""
        with pytest.raises(ValueError, match="empty key"):
            parse_harness_overrides(":value")

    def test_empty_value_raises_error(self):
        """Empty value raises ValueError."""
        with pytest.raises(ValueError, match="empty value"):
            parse_harness_overrides("key:")
