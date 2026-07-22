from notifier.group_filter import is_chat_in_allowlist


class TestIsChatInAllowlist:
    def test_empty_allowlist_allows_everything(self):
        assert is_chat_in_allowlist(-100123456, {}) is True
        assert is_chat_in_allowlist(999, {}) is True

    def test_listed_chat_is_allowed(self):
        allowed = {-100123456: "My Group"}
        assert is_chat_in_allowlist(-100123456, allowed) is True

    def test_unlisted_chat_is_blocked_once_allowlist_is_non_empty(self):
        allowed = {-100123456: "My Group"}
        assert is_chat_in_allowlist(-100999999, allowed) is False

    def test_works_with_a_plain_set_of_ids_too(self):
        allowed = {-100123456, -100999999}
        assert is_chat_in_allowlist(-100123456, allowed) is True
        assert is_chat_in_allowlist(111, allowed) is False
