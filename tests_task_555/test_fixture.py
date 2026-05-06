import os
import pytest
import dotenv
import requests

from faker import Faker

fake = Faker()
dotenv.load_dotenv()
creds = os.getenv("REQRES_API_KEY")


@pytest.fixture
def user_data():
    return {"name": fake.name(), "job": fake.job()}


def create_user(req_body):
    response = requests.post(f'https://reqres.in/api/users',
                            headers={"x-api-key": creds},
                            json=req_body
                            )
    return response


def test_create_user(user_data):
    name, job = user_data.values()
    response = create_user(user_data)
    assert response.status_code == 201, f"Ожидался статус-код 201, но получен {response.status_code}"
    response_body = response.json()
    assert response_body["name"] == name, f"Ожидался name={name}, но получен {response_body['name']}"
    assert response_body["job"] == job,  f"Ожидался job={job}, но получен {response_body['job']}"