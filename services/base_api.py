import json as json_lib
import logging
import time
import uuid
from typing import Any

import allure
from requests import ConnectionError as RequestsConnectionError
from requests import Response, Session, Timeout
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib3.util.retry import Retry

from config.environments import EnvironmentConfig
from services.exceptions import ApiConnectionError, ApiError, ApiTimeoutError

logger = logging.getLogger("api")

DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.3
RETRY_STATUSES = (500, 502, 503, 504)


class BaseAPI:
    """Базовый HTTP-клиент: единый _request с retry, structured-logging и request_id."""

    def __init__(self, env_config: EnvironmentConfig, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Инициализирует клиент с базовым URL, таймаутом и преднастроенной requests.Session."""
        self.base_url = env_config.reqres_url.rstrip("/")
        self.timeout = timeout
        self.session = self._build_session(env_config)

    @staticmethod
    def _build_session(env_config: EnvironmentConfig) -> Session:
        """Создаёт requests.Session с retry-политикой для 5xx, пулом соединений и дефолтными заголовками."""
        session = Session()
        retry = Retry(
            total=DEFAULT_RETRIES,
            backoff_factor=DEFAULT_BACKOFF,
            status_forcelist=RETRY_STATUSES,
            allowed_methods=("HEAD", "GET", "OPTIONS", "PUT", "DELETE"),
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        if getattr(env_config, "reqres_api_key", ""):
            session.headers["x-api-key"] = env_config.reqres_api_key
        return session

    def _request(self, method: str, path: str, **kwargs: Any) -> Response:
        """Выполняет HTTP-запрос: генерирует X-Request-Id, логирует, ловит транспортные ошибки.

        В Allure-отчёт прикрепляются и REQUEST, и RESPONSE с тем же request_id, чтобы их легко сопоставить.
        Бросает ApiTimeoutError / ApiConnectionError / ApiError при сбое транспорта.
        """
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        request_id = uuid.uuid4().hex
        kwargs.setdefault("timeout", self.timeout)
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["X-Request-Id"] = request_id
        kwargs["headers"] = headers

        self._attach_request(
            method=method,
            url=url,
            headers=self._hide_secret_header("x-api-key", {**self.session.headers, **headers}),
            body=kwargs.get("json"),
            params=kwargs.get("params"),
            request_id=request_id,
        )

        start = time.monotonic()
        try:
            response = self.session.request(method, url, **kwargs)
        except Timeout as exc:
            elapsed = (time.monotonic() - start) * 1000
            logger.error(
                "api_request_timeout method=%s url=%s request_id=%s elapsed_ms=%.0f",
                method,
                url,
                request_id,
                elapsed,
            )
            raise ApiTimeoutError(f"{method} {url} timed out after {kwargs['timeout']}s") from exc
        except RequestsConnectionError as exc:
            logger.error("api_connection_error method=%s url=%s request_id=%s error=%s", method, url, request_id, exc)
            raise ApiConnectionError(f"{method} {url} connection error: {exc}") from exc
        except RequestException as exc:
            logger.error("api_request_failed method=%s url=%s request_id=%s error=%s", method, url, request_id, exc)
            raise ApiError(f"{method} {url} failed: {exc}") from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "api_request method=%s url=%s status=%s request_id=%s elapsed_ms=%.0f",
            method,
            url,
            response.status_code,
            request_id,
            elapsed_ms,
        )
        self._attach_response(response, elapsed_ms, request_id)
        return response

    @staticmethod
    def _hide_secret_header(secret_header: str, headers: dict) -> dict | None:
        """Скрывает секретный хедер запроса в Allure отчёте при сохранении длины значения"""
        if headers.get(secret_header):
            headers[secret_header] = "*" * len(headers[secret_header])
        return headers

    @staticmethod
    def _attach_request(
        method: str,
        url: str,
        headers: Any,
        body: Any,
        params: Any,
        request_id: str,
    ) -> None:
        """Прикрепляет к Allure JSON-описание исходящего запроса."""
        info = {
            "request_id": request_id,
            "method": method,
            "url": url,
            "headers": dict(headers),
            "params": params,
            "body": body,
        }
        allure.attach(
            body=json_lib.dumps(info, indent=2, ensure_ascii=False, default=str),
            name=f"REQUEST {method} {url}",
            attachment_type=allure.attachment_type.JSON,
        )

    @staticmethod
    def _attach_response(response: Response, elapsed_ms: float, request_id: str) -> None:
        """Прикрепляет к Allure тело ответа c request_id, статусом и длительностью; не-JSON отдаёт как текст."""
        try:
            payload = json_lib.dumps(response.json(), indent=2, ensure_ascii=False)
            atype = allure.attachment_type.JSON
        except (ValueError, json_lib.JSONDecodeError):
            payload = response.text or f"<empty body, status {response.status_code}>"
            atype = allure.attachment_type.TEXT
        body = f"# request_id={request_id} status={response.status_code} elapsed_ms={elapsed_ms:.0f}\n{payload}"
        allure.attach(body=body, name=f"RESPONSE {response.status_code}", attachment_type=atype)

    def get(self, path: str, **kwargs: Any) -> Response:
        """Шорткат над _request для GET-запроса."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Response:
        """Шорткат над _request для POST-запроса."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Response:
        """Шорткат над _request для PUT-запроса."""
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Response:
        """Шорткат над _request для PATCH-запроса."""
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Response:
        """Шорткат над _request для DELETE-запроса."""
        return self._request("DELETE", path, **kwargs)
