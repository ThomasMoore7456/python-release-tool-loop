from tool_loop import choose_release_action


def test_release_is_held_with_a_failed_check() -> None:
    decision = choose_release_action(("passed", "security review"))
    assert decision.action == "hold"
    assert decision.diagnostics == ("security review",)


def test_release_proceeds_when_checks_are_green() -> None:
    decision = choose_release_action(("pass", "green"))
    assert decision.action == "release"
    assert decision.diagnostics == ()

