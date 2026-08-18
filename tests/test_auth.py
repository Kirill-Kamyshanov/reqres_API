import allure
import pytest

from services.reqres_in.auth.assertions import (
    assert_login_failed,
    assert_login_successful,
    assert_register_failed,
    assert_register_successful,
)
from services.reqres_in.auth.models.auth import LoginRequest, RegisterRequest


@pytest.mark.regression
@allure.feature("Authentication")
class TestAuth:
    @pytest.mark.smoke
    @allure.title("Успешная регистрация")
    def test_register_successful(self, api, test_data: dict):
        with allure.step("Подготовка тела запроса"):
            body = RegisterRequest(**test_data["auth"]["register_valid"]).model_dump()

        with allure.step("Отправка запроса на регистрацию"):
            response, validated = api.auth.register(body)

        with allure.step("Валидация ответа"):
            assert_register_successful(response, validated)

    @allure.title("Регистрация с невалидными входными данными")
    def test_register_negative(self, api, test_data: dict):
        with allure.step("Отправка запроса без пароля"):
            response, validated = api.auth.register_expect_error(test_data["auth"]["register_invalid"])

        with allure.step("Валидация ответа"):
            assert_register_failed(response, validated, test_data["auth"]["expected_error"])

    @pytest.mark.smoke
    @allure.title("Успешная авторизация")
    def test_auth_successful(self, api, test_data: dict):
        with allure.step("Подготовка тела запроса"):
            body = LoginRequest.model_validate(test_data["auth"]["login_valid"]).model_dump()

        with allure.step("Отправка запроса на авторизацию"):
            response, validated = api.auth.login(body)

        with allure.step("Валидация ответа"):
            assert_login_successful(response, validated)

    @allure.title("Авторизация с невалидными входными данными")
    def test_auth_negative(self, api, test_data: dict):
        with allure.step("Отправка запроса без пароля"):
            response, validated = api.auth.login_expect_error(test_data["auth"]["login_invalid"])

        with allure.step("Валидация ответа"):
            assert_login_failed(response, validated, test_data["auth"]["expected_error"])
