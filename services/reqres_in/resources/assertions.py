import allure
from requests import Response

from services.reqres_in.resources.models.resource import (
    ResourcesListResponse,
    SingleResourceResponse,
)
from utils.assertions import assert_status_code


@allure.step("Проверка данных ресурса: ID={resource_id}")
def assert_resource_data(response: Response, validated: SingleResourceResponse, resource_id: int) -> None:
    assert_status_code(response, 200)
    assert validated.data.id == resource_id, f"Ожидался id={resource_id}, получен {validated.data.id}"


@allure.step("Проверка списка ресурсов на странице {page}")
def assert_resources_list(response: Response, validated: ResourcesListResponse, page: int) -> None:
    assert_status_code(response, 200)
    assert validated.page == page, f"Ожидался page={page}, получен {validated.page}"

    expected_pages = -(-validated.total // validated.per_page)
    assert validated.total_pages == expected_pages, (
        f"Ожидалось total_pages={expected_pages}, получено {validated.total_pages}"
    )
