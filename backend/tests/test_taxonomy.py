from app.taxonomy import category_for_intent


def test_category_is_derived_from_intent() -> None:
    assert category_for_intent("course_pricing_payment") == "relevant"
    assert category_for_intent("neutral") == "neutral"
    assert category_for_intent("irrelevant") == "irrelevant"
    assert category_for_intent("not_real") == "unknown"
