from datetime import datetime

from faker import Faker
from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

fake = Faker()


class Support(BaseModel):
    """вспомогательная структура с полями url и text"""

    url: HttpUrl
    text: str


class UserData(BaseModel):
    """данные пользователя с полями id, email, first_name, last_name, avatar"""

    id: int = Field(gt=0)
    email: EmailStr
    first_name: str
    last_name: str
    avatar: HttpUrl


class SingleUserResponse(BaseModel):
    """ответ при получении одного пользователя"""

    data: UserData
    support: Support


class UsersListResponse(BaseModel):
    """ответ при получении списка пользователей"""

    page: int = Field(gt=0)
    per_page: int = Field(gt=0)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    data: list[UserData]
    support: Support


class CreateUserRequest(BaseModel):
    """запрос на создание пользователя"""

    name: str = Field(default_factory=fake.name, min_length=2, max_length=25)
    job: str = Field(default_factory=fake.job)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Преобразует имя в Title Case ДО основной валидации."""
        return v.title()


class CreateUserResponse(BaseModel):
    """ответ при создании пользователя"""

    name: str
    job: str
    id: int = Field(gt=0)
    createdAt: datetime


class UpdateUserRequest(BaseModel):
    """запрос на обновление пользователя"""

    name: str = Field(default_factory=fake.name, min_length=2, max_length=25)
    job: str = Field(default_factory=fake.job)


class UpdateUserResponse(BaseModel):
    """ответ при обновлении пользователя"""

    name: str | None
    job: str | None
    updatedAt: datetime
