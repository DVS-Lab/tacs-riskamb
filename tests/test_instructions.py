import instructions


def test_safe_option_comprehension_answer_is_explicitly_zero():
    item = next(item for item in instructions.COMPREHENSION if "GUARANTEED $0" in item["question"])
    assert item["answers"][item["correct"]] == "Exactly $0"
    assert "always pays exactly $0" in item["correction"]


def test_incorrect_answer_shows_correction_then_retries(monkeypatch):
    item = {
        "question": "Test question",
        "answers": ["Correct", "Wrong", "Also wrong"],
        "correct": 0,
        "correction": "This is the explicit correction.",
    }
    responses = iter([2, 0])
    screens = []
    monkeypatch.setattr(instructions, "COMPREHENSION", [item])
    monkeypatch.setattr(instructions, "_ask_question", lambda renderer, current, auto: next(responses))
    monkeypatch.setattr(
        instructions,
        "_draw_lines",
        lambda renderer, lines, footer="": screens.append((list(lines), footer)),
    )
    monkeypatch.setattr(instructions, "_wait_for_navigation", lambda auto: "next")

    result = instructions.comprehension_check(object())

    assert result == {"passed": True, "attempts": 2, "errors": 1}
    assert screens == [
        (["Incorrect", "This is the explicit correction.", "Please try the question again."], "Press SPACE to retry")
    ]
