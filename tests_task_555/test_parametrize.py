import os
import pytest
import requests
import dotenv

from pydantic import BaseModel

users_ids = [1,2,3,4,5]
dotenv.load_dotenv()

class UserData(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    avatar: str




def get_user(user_id):
    creds = os.getenv("REQRES_API_KEY")
    response = requests.get(f'https://reqres.in/api/users/{user_id}',
                            headers={"x-api-key": creds})
    return response


@pytest.mark.parametrize("user_id", users_ids)
def test_get_user_parametrize(user_id):
    response = get_user(user_id)
    assert response.status_code == 200, f"Ожидался статус-код 200, но получен {response.status_code}"
    validated_data = UserData(**response.json()['data'])
    assert validated_data.id == user_id, f"ожидался id={user_id}, но получен {validated_data.id}"

