import pytest
import requests
import os
from faker import Faker
import dotenv

fake = Faker()
dotenv.load_dotenv()
creds = os.getenv("REQRES_API_KEY")


@pytest.mark.smoke
@pytest.mark.regression
def test_get_user_list(page=1):
    response = requests.get(f'https://reqres.in/api/users?page={page}',
                            headers={"x-api-key": creds})
    assert response.status_code == 200, f"Ожидался статус-код 200, но получен {response.status_code}"



@pytest.mark.smoke
@pytest.mark.regression
def test_create_user():
    req_body = {"name": fake.name(), "job": fake.job()}
    response = requests.post(f'https://reqres.in/api/users',
                             headers={"x-api-key": creds},
                             json=req_body
                             )
    assert response.status_code == 201, f"Ожидался статус-код 201, но получен {response.status_code}"
    response_body = response.json()
    assert response_body["name"] == req_body["name"], f"Ожидался name={req_body["name"]}, но получен {response_body['name']}"
    assert response_body["job"] == req_body["job"],  f"Ожидался job={req_body["job"]}, но получен {response_body['job']}"



@pytest.mark.skipif(os.name == 'nt', reason="Test not for Windows")
@pytest.mark.regression
def test_update_user():
    req_body = {"name": "new_name", "job": "new_job"}
    user_id = 2
    response = requests.patch(f'https://reqres.in/api/users/{user_id}',
                             headers={"x-api-key": creds},
                             json=req_body
                             )
    assert response.status_code == 200, f"Ожидался статус-код 201, но получен {response.status_code}"
    response_body = response.json()
    assert response_body["name"] == req_body["name"], f"Ожидался name={req_body["name"]}, но получен {response_body['name']}"
    assert response_body["job"] == req_body["job"], f"Ожидался job={req_body["job"]}, но получен {response_body['job']}"
