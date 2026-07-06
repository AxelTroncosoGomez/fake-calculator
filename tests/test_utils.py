from src.utils import debounce, truncate_string, validate_email


class TestValidateEmail:
    def test_accepts_valid_email(self):
        assert validate_email("test@example.com") is True

    def test_rejects_missing_at(self):
        assert validate_email("testexample.com") is False

    def test_rejects_missing_domain(self):
        assert validate_email("test@") is False


class TestTruncateString:
    def test_returns_short_strings_unchanged(self):
        assert truncate_string("hello", 10) == "hello"

    def test_truncates_long_strings_with_ellipsis(self):
        assert truncate_string("hello world this is long", 10) == "hello worl..."


class TestDebounce:
    def test_calls_function_after_delay(self):
        calls = []

        @debounce(0.1)
        def fn():
            calls.append(1)

        fn()
        assert len(calls) == 1
        fn()
        assert len(calls) == 1

    def test_prevents_rapid_calls(self):
        calls = []

        @debounce(10.0)
        def fn():
            calls.append(1)

        fn()
        fn()
        fn()
        assert len(calls) == 1
