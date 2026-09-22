from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


JsonValue = str | int | float | bool | None | dict[str, Any] | list[Any]


class NoulQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["noul"]
    instructions: JsonValue
    criteria: dict[str, JsonValue] | None = None


class ChoiceQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["choice"]
    instructions: JsonValue
    criteria: dict[str, JsonValue]


class ScoreQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["score"]
    instructions: JsonValue
    criteria: list[JsonValue]

    @model_validator(mode="after")
    def validate_levels(self):
        if len(self.criteria) < 2:
            raise ValueError("score criteria must contain at least two levels")
        return self


Question = NoulQuestion | ChoiceQuestion | ScoreQuestion


class SystemOneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: str | dict[str, Any] | list[Any]
    model: str = "jev-latest"
    questions: dict[str, Question]

    @model_validator(mode="after")
    def validate_questions(self):
        if not self.questions:
            raise ValueError("questions must not be empty")
        return self


class Usage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None


class SystemOneResponse(BaseModel):
    model: str
    answers: dict[str, dict[str, Any]]
    usage: Usage

