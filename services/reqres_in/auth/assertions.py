import allure
from requests import Response

from services.reqres_in.auth.models.auth import ErrorResponse, LoginResponse, RegisterResponse
from utils.assertions import assert_status_code


@allure.step("Проверка успешной авторизации")
def assert_login_successful(response: Response, validated: LoginResponse) -> None:
    assert_status_code(response, 200)
    assert validated.token, "Токен отсутствует в ответе"


@allure.step("Проверка ошибки авторизации: {expected_error}")
def assert_login_failed(response: Response, validated: ErrorResponse, expected_error: str) -> None:
    assert_status_code(response, 400)
    assert validated.error == expected_error, f"Ожидалась ошибка '{expected_error}', получено '{validated.error}'"


@allure.step("Проверка успешной регистрации")
def assert_register_successful(response: Response, validated: RegisterResponse) -> None:
    assert_status_code(response, 200)
    assert validated.token, "Токен отсутствует в ответе"


@allure.step("Проверка ошибки регистрации: {expected_error}")
def assert_register_failed(response: Response, validated: ErrorResponse, expected_error: str) -> None:
    assert_status_code(response, 400)
    assert validated.error == expected_error, f"Ожидалась ошибка '{expected_error}', получено '{validated.error}'"
