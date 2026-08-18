import allure
import pytest

from services.reqres_in.users.assertions import (
    assert_user_created,
    assert_user_data,
    assert_user_deleted,
    assert_user_updated,
    assert_users_list,
)
from services.reqres_in.users.models.user import CreateUserRequest, UpdateUserRequest
from utils.assertions import assert_status_code


@pytest.mark.regression
@allure.feature("Users")
class TestUsers:
    @allure.title("Проверка корректности пагинации")
    def test_users_pagination(self, api, test_data: dict):
        with allure.step("Отправка GET-запроса с пагинацией"):
            page = test_data["users"]["pagination_page"]
            response, validated = api.users.list(page)

        with allure.step("Валидация тела ответа"):
            assert_users_list(response, validated, page)

    @pytest.mark.smoke
    @allure.title("Получение данных о существующем пользователе по ID")
    def test_get_user(self, api, test_data: dict):
        with allure.step("Получение данных о пользователе"):
            user_id = test_data["users"]["valid_id"]
            response, validated = api.users.get_by_id(user_id)

        with allure.step("Проверка корректности ответа"):
            assert_user_data(response, validated, user_id)

    @allure.title("Получение данных о несуществующем пользователе")
    def test_get_user_negative(self, api, test_data: dict):
        with allure.step("Попытка получить данные о несуществующем пользователе"):
            invalid_id = test_data["users"]["invalid_id"]
            response, _ = api.users.get_by_id(invalid_id, validate=False)

        with allure.step("Проверка статус-кода от сервера"):
            assert_status_code(response, 404)

    @pytest.mark.smoke
    @allure.title("Создание нового пользователя")
    def test_create_user(self, api, cleanup):
        with allure.step("Создаём нового пользователя"):
            new_user = CreateUserRequest()
            response, validated = api.users.create(**new_user.model_dump())
            cleanup.append(lambda: api.users.remove(validated.id))

        with allure.step("Проверка корректности создания"):
            assert_user_created(response, validated, new_user.name, new_user.job)

    @allure.title("Полное обновление данных пользователя методом PUT")
    def test_update_user_put(self, api, test_data: dict):
        with allure.step("Подготовка данных для обновления"):
            user_id = test_data["users"]["valid_id"]
            new_data = UpdateUserRequest()

        with allure.step("Отправка PUT-запроса на обновление"):
            response, validated = api.users.update_put(user_id=user_id, **new_data.model_dump())

        with allure.step("Проверка корректности обновления данных"):
            assert_user_updated(response, validated, **new_data.model_dump())

    @allure.title("Частичное обновление данных пользователя методом PATCH")
    def test_update_user_patch(self, api, test_data: dict):
        with allure.step("Подготовка данных для обновления"):
            user_id = test_data["users"]["valid_id"]
            new_data = UpdateUserRequest()

        with allure.step("Отправка PATCH-запроса на обновление"):
            response, validated = api.users.update_patch(user_id=user_id, **new_data.model_dump())

        with allure.step("Проверка корректности обновления данных"):
            assert_user_updated(response, validated, **new_data.model_dump())

    @allure.title("Успешное удаление пользователя")
    def test_delete_user(self, api):
        with allure.step("Создание пользователя для удаления"):
            new_user = CreateUserRequest()
            _, created = api.users.create(**new_user.model_dump())

        with allure.step("Удаление созданного пользователя"):
            response = api.users.remove(created.id)

        with allure.step("Проверка статус-кода"):
            assert_user_deleted(response)
