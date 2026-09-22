from typing import Any


def to_laya_questions(questions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {key: value.model_dump(exclude_none=True) for key, value in questions.items()}


def to_jev_response(result: dict[str, Any]) -> dict[str, Any]:
    answers: dict[str, dict[str, Any]] = {}
    for key, answer in result.get("answers", {}).items():
        answers[key] = {field: value for field, value in answer.items() if field != "action"}
    usage = result.get("usage") or {}
    return {
        "model": result.get("model", "laya-rl-agent"),
        "answers": answers,
        "usage": {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens", 0),
        },
    }

