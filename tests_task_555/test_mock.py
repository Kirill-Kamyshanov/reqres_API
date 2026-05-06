import os
import pook
import requests

from pydantic import BaseModel
user_id = 134

mock_response_body = {
    "data": {
        "id": user_id,
        "email": "janet.weaver@reqres.in",
        "first_name": "Janet",
        "last_name": "Weaver",
        "avatar": "https://reqres.in/img/faces/2-image.jpg"
    },
    "support": {
        "url": "https://benhowdle.im/first-cto-playbook?utm_source=reqres&utm_medium=json&utm_campaign=referral",
        "text": "Become a better CTO. A playbook of painful stories and practical advice from a two-time startup CTO."
    },
    "_meta": {
        "powered_by": "ReqRes",
        "docs_url": "https://app.reqres.in/documentation",
        "upgrade_url": "https://app.reqres.in/upgrade",
        "example_url": "https://app.reqres.in/examples/notes-app",
        "variant": "v1_b",
        "message": "This is a read-only demo endpoint. Sign up to create your own collections with full CRUD and auth.",
        "cta": {
            "label": "Get started",
            "url": "https://app.reqres.in/upgrade"
        },
        "context": "legacy_success"
    }
}

class UserData(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    avatar: str



def process_user_data(user_id: int):
    creds = os.getenv("REQRES_API_KEY")
    response = requests.get(f'https://reqres.in/api/users/{user_id}',
                            headers={"x-api-key": creds})
    return response.status_code, UserData(**response.json()["data"])


@pook.on
def test_using_mock():
    pook.get(f'https://reqres.in/api/users/{user_id}',
              status=200,
              response_json=mock_response_body
              )
    status_code, validated_resp_body = process_user_data(user_id)
    assert status_code == 200, f"Ожидался статус-код= 200, но получен {status_code}"
    assert validated_resp_body.id == user_id, f"Ожидался id={user_id}, но получен {validated_resp_body.id}"
