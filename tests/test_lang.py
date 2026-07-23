from notifier import lang


def test_welcome_message_mentions_help():
    assert "/help" in lang.WELCOME_MESSAGE


def test_unknown_command_header_has_command_placeholder():
    assert "{command}" in lang.UNKNOWN_COMMAND_HEADER


def test_unknown_command_suggestion_has_placeholders():
    assert "{suggestion}" in lang.UNKNOWN_COMMAND_SUGGESTION
    assert "{usage}" in lang.UNKNOWN_COMMAND_SUGGESTION


def test_unknown_command_fallback_has_help_text_placeholder():
    assert "{help_text}" in lang.UNKNOWN_COMMAND_FALLBACK


def test_non_command_nudge_has_help_text_placeholder():
    assert "{help_text}" in lang.NON_COMMAND_NUDGE


def test_all_strings_are_non_empty():
    for name in lang.__all__:
        value = getattr(lang, name)
        assert isinstance(value, str) and len(value) > 0
