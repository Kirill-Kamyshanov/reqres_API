import allure
from requests import Response

from services.reqres_in.users.models.user import (
    CreateUserResponse,
    SingleUserResponse,
    UpdateUserResponse,
    UsersListResponse,
)
from utils.assertions import assert_status_code


@allure.step("Проверка списка пользователей на странице {page}")
def assert_users_list(response: Response, validated: UsersListResponse, page: int) -> None:
    assert_status_code(response, 200)
    assert validated.data is not None, "В ответе отсутствует ключ data"
    assert validated.page == page, f"Ожидалось page={page}, но пришло {validated.page}"
    assert len(validated.data) == validated.per_page, (
        f"Несоответствие data({len(validated.data)}) и per_page={validated.per_page}"
    )


@allure.step("Проверка данных пользователя: ID={user_id}")
def assert_user_data(response: Response, validated: SingleUserResponse, user_id: int) -> None:
    assert_status_code(response, 200)
    assert validated.data.id == user_id, f"Ожидался id={user_id}, получен {validated.data.id}"


@allure.step("Проверка созданного пользователя: {expected_name}")
def assert_user_created(
    response: Response,
    validated: CreateUserResponse,
    expected_name: str,
    expected_job: str,
) -> None:
    assert_status_code(response, 201)
    assert validated.name == expected_name, f"Ожидалось name='{expected_name}', получено '{validated.name}'"
    assert validated.job == expected_job, f"Ожидалось job='{expected_job}', получено '{validated.job}'"
    assert validated.id is not None, "Поле 'id' отсутствует или пустое"
    assert validated.createdAt is not None, "Поле 'createdAt' отсутствует или пустое"


@allure.step("Проверка обновления пользователя: {name}")
def assert_user_updated(response: Response, validated: UpdateUserResponse, name: str, job: str) -> None:
    """Проверяет успешное обновление пользователя (PUT/PATCH)"""
    assert_status_code(response, 200)
    assert validated.name == name, f"Ожидалось name='{name}', получено '{validated.name}'"
    assert validated.job == job, f"Ожидалось job='{job}', получено '{validated.job}'"


@allure.step("Проверка удаления пользователя")
def assert_user_deleted(response: Response) -> None:
    assert_status_code(response, 204)
