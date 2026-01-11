# core/auth_client.py
from core.storage import save_json


def login_google(http_client, google_token):
    response = http_client.post(
        "/auth/google",
        {"google_token": google_token}
    )

    jwt = response["access_token"]
    http_client.set_token(jwt)

    save_json("data/session.json", {
        "jwt": jwt
    })

    return jwt
