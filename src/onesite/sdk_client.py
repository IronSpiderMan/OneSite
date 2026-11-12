"""HTTP transport bundled in each OneSite SDK."""

from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import quote

import httpx
from typing_extensions import Self


class Unset:
    """An omitted request body, distinct from JSON null."""


_UNSET = Unset()


class APIError(Exception):
    """An HTTP request was rejected by the server."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.status_code = response.status_code
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        self.detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
        super().__init__(f"HTTP {response.status_code} {response.request.method} "
                         f"{response.request.url.path}")


class AuthenticationExpired(APIError):
    """The server no longer accepts the client's bearer token."""


def _wire_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_wire_value(item) for item in value]
    return value


def _path_segment(value: Any) -> str:
    segment = str(_wire_value(value))
    encoded = quote(segment, safe="")
    return encoded.replace(".", "%2E") if segment in {".", ".."} else encoded


class HTTPClient:
    """A synchronous client with an in-memory bearer token and connection pool."""

    _token_path: str

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        url = httpx.URL(base_url)
        if url.scheme not in {"http", "https"} or not url.host or url.query or url.fragment:
            raise ValueError("base_url must be an HTTP(S) service URL without a query or fragment")
        self._http = httpx.Client(base_url=url, timeout=timeout, transport=transport)
        self._token = token

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self.logout()
        self._http.close()

    def logout(self) -> None:
        """Clear the local token."""
        self._token = None

    def login(self, email: str, password: str) -> None:
        """Sign in and use the returned token for subsequent calls."""
        response = self._http.post(
            self._token_path,
            data={"grant_type": "password", "username": email, "password": password},
        )
        self._check_status(response, None)
        payload = response.json()
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise ValueError("Login response did not contain an access token")
        self._token = token

    def _check_status(self, response: httpx.Response, token: str | None) -> None:
        if response.is_success:
            return
        if response.status_code == 401 and token:
            if self._token == token:
                self.logout()
            raise AuthenticationExpired(response)
        raise APIError(response)

    def _request(
        self,
        method: str,
        path: str,
        *,
        path_params: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: Any = _UNSET,
    ) -> Any:
        if path_params:
            path = path.format_map({name: _path_segment(value) for name, value in path_params.items()})
        token = self._token
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        options: dict[str, Any] = {}
        if body is None:
            # httpx treats json=None as an absent body.
            options["content"] = b"null"
            headers["Content-Type"] = "application/json"
        elif body is not _UNSET:
            options["json"] = body
        response = self._http.request(
            method,
            path,
            headers=headers,
            params={key: _wire_value(value) for key, value in (query or {}).items() if value is not None},
            **options,
        )
        self._check_status(response, token)
        return response.json() if response.content else None
