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
    @allure.testcase("https://jira.example.com/TC-2", "TC-2")
    def test_users_pagination(self, api, test_data):
        """Проверяет, что список пользователей возвращается постранично с корректными метаданными."""
        with allure.step("Отправка GET-запроса с пагинацией"):
            page = test_data["users"]["pagination_page"]
            response, validated = api.users.list(page)

        with allure.step("Валидация тела ответа"):
            assert_users_list(response, validated, page)

    @pytest.mark.smoke
    @allure.title("Получение данных о пользователе")
    @allure.testcase("https://jira.example.com/TC-3", "TC-3")
    def test_get_user(self, api, test_data):
        """Проверяет успешное получение данных существующего пользователя по ID."""
        with allure.step("Получение данных о пользователе"):
            user_id = test_data["users"]["valid_id"]
            response, validated = api.users.get_by_id(user_id)

        with allure.step("Проверка корректности ответа"):
            assert_user_data(response, validated, user_id)

    @allure.title("Получение данных о несуществующем пользователе")
    @allure.testcase("https://jira.example.com/TC-4", "TC-4")
    def test_get_user_negative(self, api, test_data):
        """Проверяет, что запрос несуществующего пользователя возвращает 404."""
        with allure.step("Попытка получить данные о несуществующем пользователе"):
            invalid_id = test_data["users"]["invalid_id"]
            response, _ = api.users.get_by_id(invalid_id, validate=False)

        with allure.step("Проверка статус-кода от сервера"):
            assert_status_code(response, 404)

    @pytest.mark.smoke
    @allure.title("Создание нового пользователя")
    @allure.testcase("https://jira.example.com/TC-1", "TC-1")
    def test_create_user(self, api, cleanup):
        """Проверяет успешное создание пользователя и корректность возвращаемых данных."""
        with allure.step("Создаём нового пользователя"):
            new_user = CreateUserRequest()
            response, validated = api.users.create(**new_user.model_dump())
            cleanup.append(lambda: api.users.remove(validated.id))

        with allure.step("Проверка корректности создания"):
            assert_user_created(response, validated, new_user.name, new_user.job)

    @allure.title("Обновление данных методом PUT")
    @allure.testcase("https://jira.example.com/TC-5", "TC-5")
    def test_update_user_put(self, api, test_data):
        """Проверяет полное обновление данных пользователя через PUT."""
        with allure.step("Подготовка данных для обновления"):
            user_id = test_data["users"]["valid_id"]
            new_data = UpdateUserRequest()

        with allure.step("Отправка PUT-запроса на обновление"):
            response, validated = api.users.update_put(user_id=user_id, **new_data.model_dump())

        with allure.step("Проверка корректности обновления данных"):
            assert_user_updated(response, validated, **new_data.model_dump())

    @allure.title("Обновление пользователя методом PATCH")
    @allure.testcase("https://jira.example.com/TC-6", "TC-6")
    def test_update_user_patch(self, api, test_data):
        """Проверяет частичное обновление данных пользователя через PATCH."""
        with allure.step("Подготовка данных для обновления"):
            user_id = test_data["users"]["valid_id"]
            new_data = UpdateUserRequest()

        with allure.step("Отправка PATCH-запроса на обновление"):
            response, validated = api.users.update_patch(user_id=user_id, **new_data.model_dump())

        with allure.step("Проверка корректности обновления данных"):
            assert_user_updated(response, validated, **new_data.model_dump())

    @allure.title("Удаление пользователя")
    @allure.testcase("https://jira.example.com/TC-7", "TC-7")
    def test_delete_user(self, api):
        """Проверяет успешное удаление ранее созданного пользователя."""
        with allure.step("Создание пользователя для удаления"):
            new_user = CreateUserRequest()
            _, created = api.users.create(**new_user.model_dump())

        with allure.step("Удаление созданного пользователя"):
            response = api.users.remove(created.id)

        with allure.step("Проверка статус-кода"):
            assert_user_deleted(response)
