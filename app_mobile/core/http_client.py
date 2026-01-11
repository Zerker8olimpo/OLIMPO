# core/http_client.py
import requests
from core.errors import from_http, OlimpoError


class OlimpoHTTPClient:

    def __init__(self, base_url, device_id, token=None):
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.token = token

    def set_token(self, token):
        self.token = token

    def _headers(self):
        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": self.device_id
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def post(self, endpoint, payload, timeout=15):
        try:
            r = requests.post(
                self.base_url + endpoint,
                json=payload,
                headers=self._headers(),
                timeout=timeout
            )
        except requests.RequestException as e:
            raise OlimpoError("NETWORK_ERROR", str(e))

        if not r.ok:
            try:
                data = r.json()
            except Exception:
                data = None
            raise from_http(r.status_code, data)

        return r.json()
