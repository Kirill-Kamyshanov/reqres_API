import allure
import pytest

from services.reqres_in.resources.assertions import (
    assert_resource_data,
    assert_resources_list,
)
from utils.assertions import assert_status_code


@pytest.mark.regression
@allure.feature("Resources")
class TestResources:

    @allure.title("Получение списка ресурсов")
    @allure.testcase("https://jira.example.com/TC-8", "TC-8")
    def test_get_resources_list(self, api, test_data):
        """Проверяет получение списка ресурсов с корректными данными пагинации."""
        with allure.step("Отправка запроса и валидация структуры ответа"):
            page = test_data["resources"]["pagination_page"]
            response, validated = api.resources.list(page)

        with allure.step("Проверка корректности полученных данных"):
            assert_resources_list(response, validated, page)

    @pytest.mark.smoke
    @allure.title("Получение одного ресурса")
    @allure.testcase("https://jira.example.com/TC-9", "TC-9")
    def test_get_resource(self, api, test_data):
        """Проверяет успешное получение данных существующего ресурса по ID."""
        with allure.step("Отправка запроса и валидация структуры ответа"):
            resource_id = test_data["resources"]["valid_id"]
            response, validated = api.resources.get_by_id(resource_id)

        with allure.step("Проверка корректности полученных данных"):
            assert_resource_data(response, validated, resource_id)


    @allure.title("Получение несуществующего ресурса")
    @allure.testcase("https://jira.example.com/TC-10", "TC-10")
    def test_get_unexisted_resource(self, api, test_data):
        """Проверяет, что запрос несуществующего ресурса возвращает 404."""
        with allure.step("Отправка запроса на получение несуществующего ресурса"):
            invalid_id = test_data["resources"]["invalid_id"]
            response, _ = api.resources.get_by_id(invalid_id, validate=False)

        with allure.step("Проверка статус-кода"):
            assert_status_code(response, 404)
