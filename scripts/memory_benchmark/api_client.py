"""Encrypted HTTP client for the memory benchmark.

This client talks to the running AICO backend through the API gateway and uses:
- Transport encryption handshake at /api/v1/handshake
- Encrypted JSON request/response envelopes handled by EncryptionMiddleware
- JWT authentication (obtained via /api/v1/users/authenticate)

It intentionally avoids any direct DB access to ensure end-to-end coverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from aico.core.config import ConfigurationManager
from aico.security.key_manager import AICOKeyManager
from aico.security.transport import TransportIdentityManager, SecureTransportChannel
from aico.security.exceptions import EncryptionError, DecryptionError


@dataclass
class AuthResult:
    user_uuid: str
    jwt_token: str
    refresh_token: Optional[str] = None


class EncryptedBenchmarkClient:
    """Encrypted API client that follows AICO's transport security requirements."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

        self._config = ConfigurationManager()
        self._config.initialize()
        self._key_manager = AICOKeyManager(self._config)
        self._identity_manager = TransportIdentityManager(self._key_manager)

        self._secure_channel: SecureTransportChannel = self._identity_manager.create_secure_channel("backend")
        identity = self._identity_manager.get_component_identity("backend")
        self._client_id = bytes(identity.verify_key).hex()[:16]

        self._jwt_token: Optional[str] = None
        self._session_established = False

    @property
    def client_id(self) -> str:
        return self._client_id

    async def close(self) -> None:
        return

    async def ensure_handshake(self) -> None:
        if self._session_established and self._secure_channel.is_session_valid():
            return

        handshake_payload = {"handshake_request": self._secure_channel.create_handshake_request()}

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/api/v1/handshake", json=handshake_payload)

        if response.status_code != 200:
            raise EncryptionError(f"Handshake failed: HTTP {response.status_code} - {response.text}")

        data = response.json()
        if data.get("status") != "session_established" or "handshake_response" not in data:
            raise EncryptionError(f"Handshake failed: {data}")

        ok = self._secure_channel.process_handshake_response(data["handshake_response"])
        if not ok:
            raise EncryptionError("Handshake response verification failed")

        self._session_established = True

    def _headers(self) -> Dict[str, str]:
        headers = {
            "X-Client-ID": self._client_id,
            "Content-Type": "application/json",
        }
        if self._jwt_token:
            headers["Authorization"] = f"Bearer {self._jwt_token}"
        return headers

    async def request(self, method: str, path: str, *, json_body: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        await self.ensure_handshake()

        url = f"{self.base_url}{path}"
        request_data: Dict[str, Any]

        if json_body is None:
            request_data = {"encrypted": True, "client_id": self._client_id}
        else:
            encrypted_payload = self._secure_channel.encrypt_json_payload(json_body)
            request_data = {
                "encrypted": True,
                "payload": encrypted_payload,
                "client_id": self._client_id,
            }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.request(method.upper(), url, headers=self._headers(), json=request_data, params=params)

        data = resp.json() if resp.content else {}
        if isinstance(data, dict) and data.get("encrypted") and "payload" in data:
            try:
                data = self._secure_channel.decrypt_json_payload(data["payload"])
            except DecryptionError:
                raise
            except Exception as e:
                raise DecryptionError(str(e)) from e

        if resp.status_code == 408:
            if isinstance(data, dict):
                data.setdefault("success", False)
                data.setdefault("status", "timeout")
                # Normalize into conversation-like shape for upstream evaluator/reporters
                detail = data.get("detail") or data.get("message") or "Conversation request timed out"
                data.setdefault("message", str(detail))
                data.setdefault("ai_response", f"[TIMEOUT] {detail}")
                data.setdefault("conversation_action", "timeout")
            return data if isinstance(data, dict) else {"success": False, "status": "timeout", "detail": str(data)}

        resp.raise_for_status()
        return data

    async def authenticate_user(self, *, user_uuid: str, pin: str) -> AuthResult:
        """Authenticate via /api/v1/users/authenticate and store JWT for subsequent calls."""
        data = await self.request(
            "POST",
            "/api/v1/users/authenticate",
            json_body={
                "user_uuid": user_uuid,
                "pin": pin,
            },
        )

        if not data.get("success"):
            raise PermissionError(data.get("error") or "Authentication failed")

        jwt_token = data.get("jwt_token")
        if not jwt_token:
            raise PermissionError("Authentication succeeded but no jwt_token returned")

        self._jwt_token = jwt_token
        return AuthResult(user_uuid=user_uuid, jwt_token=jwt_token, refresh_token=data.get("refresh_token"))

    async def send_conversation_message(self, *, message: str, conversation_id: Optional[str] = None, stream: bool = False) -> Dict[str, Any]:
        params = {"stream": "true" if stream else "false"}
        body: Dict[str, Any] = {"message": message}
        if conversation_id:
            body["conversation_id"] = conversation_id

        return await self.request("POST", "/api/v1/conversation/messages", json_body=body, params=params)
