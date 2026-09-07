"""Shared validation for administrator forms."""

import re
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PersonInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=7, max_length=30)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        if re.search(r"[^\d+()\s-]", value):
            raise ValueError("Телефон должен содержать только цифры и код страны")
        digits = re.sub(r"\D", "", value)
        if len(digits) == 10:
            digits = "7" + digits
        if len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        if not 10 <= len(digits) <= 15:
            raise ValueError("Укажите телефон с кодом страны, от 10 до 15 цифр")
        return "+" + digits
