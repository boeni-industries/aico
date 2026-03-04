#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from nacl.public import PrivateKey, PublicKey, Box
from nacl.secret import SecretBox
from nacl.signing import SigningKey
from nacl.utils import random


@dataclass
class TestUser:
    uuid: str
    pin: str


class EncryptedGatewayClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.handshake_url = f"{self.base_url}/api/v1/handshake"

        self.session_box: Optional[SecretBox] = None
        self.server_public_key: Optional[PublicKey] = None

        self.jwt_token: Optional[str] = None

        self.signing_key = SigningKey.generate()
        self.verify_key = self.signing_key.verify_key

    def perform_handshake(self) -> None:
        client_private_key = PrivateKey.generate()
        client_public_key = client_private_key.public_key

        challenge_bytes = random(32)
        handshake_request: Dict[str, Any] = {
            "component": "rate_limit_e2e_test",
            "identity_key": base64.b64encode(bytes(self.verify_key)).decode(),
            "public_key": base64.b64encode(bytes(client_public_key)).decode(),
            "timestamp": int(time.time()),
            "challenge": base64.b64encode(challenge_bytes).decode(),
        }

        signature = self.signing_key.sign(challenge_bytes).signature
        handshake_request["signature"] = base64.b64encode(signature).decode()

        resp = requests.post(
            self.handshake_url,
            json={"handshake_request": handshake_request},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()

        data = resp.json()
        if data.get("status") != "session_established":
            raise RuntimeError(f"Handshake rejected: {data.get('error') or data}")

        response_data = data["handshake_response"]
        server_public_key_b64 = response_data["public_key"]
        self.server_public_key = PublicKey(base64.b64decode(server_public_key_b64))

        shared_box = Box(client_private_key, self.server_public_key)
        session_key = shared_box.shared_key()
        self.session_box = SecretBox(session_key)

    def encrypt_payload(self, payload: Dict[str, Any]) -> str:
        if not self.session_box:
            raise RuntimeError("No active session")
        plaintext = json.dumps(payload).encode()
        encrypted = self.session_box.encrypt(plaintext)
        return base64.b64encode(encrypted).decode()

    def decrypt_payload(self, encrypted_b64: str) -> Dict[str, Any]:
        if not self.session_box:
            raise RuntimeError("No active session")
        encrypted = base64.b64decode(encrypted_b64)
        plaintext = self.session_box.decrypt(encrypted)
        return json.loads(plaintext.decode())

    def request(self, method: str, path: str, *, json_body: Optional[Dict[str, Any]] = None) -> requests.Response:
        if not path.startswith("/"):
            path = "/" + path

        envelope: Dict[str, Any]
        if json_body is None:
            envelope = {
                "encrypted": True,
                "payload": self.encrypt_payload({}),
                "client_id": self.verify_key.encode().hex()[:16],
            }
        else:
            envelope = {
                "encrypted": True,
                "payload": self.encrypt_payload(json_body),
                "client_id": self.verify_key.encode().hex()[:16],
            }

        headers = {"Content-Type": "application/json"}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

        url = f"{self.base_url}{path}"
        return requests.request(method.upper(), url, json=envelope, headers=headers, timeout=30)

    def authenticate(self, *, user_uuid: str, pin: str) -> None:
        resp = self.request(
            "POST",
            "/api/v1/users/authenticate",
            json_body={
                "user_uuid": user_uuid,
                "pin": pin,
                "timestamp": int(time.time()),
            },
        )
        if resp.status_code != 200:
            try:
                data = resp.json() if resp.content else {}
                if isinstance(data, dict) and data.get("encrypted") and "payload" in data:
                    data = self.decrypt_payload(data["payload"])
                raise RuntimeError(f"Auth HTTP {resp.status_code}: {data}")
            except Exception:
                raise RuntimeError(f"Auth HTTP {resp.status_code}: {resp.text}")

        data = resp.json() if resp.content else {}
        if isinstance(data, dict) and data.get("encrypted") and "payload" in data:
            data = self.decrypt_payload(data["payload"])

        if not isinstance(data, dict) or not data.get("success"):
            raise RuntimeError(f"Auth failed: {data}")

        token = data.get("jwt_token") or data.get("token") or data.get("access_token")
        if not token:
            raise RuntimeError(f"Auth succeeded but no token returned: {data}")
        self.jwt_token = token


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).parent.parent
    cmd = ["uv", "--project", str(repo_root / "cli"), "run", "python", "-m", "cli.aico_main", *args]
    return subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def create_test_user(*, full_name: str, pin: str) -> TestUser:
    proc = _run_cli(["security", "user-create", full_name, "--pin", pin])
    if proc.returncode != 0:
        raise RuntimeError(f"user-create failed: {proc.stdout}\n{proc.stderr}")

    user_uuid: Optional[str] = None
    for line in proc.stdout.splitlines():
        if line.startswith("UUID: "):
            user_uuid = line.replace("UUID: ", "").strip()
            break

    if not user_uuid:
        raise RuntimeError(f"user-create did not print UUID: {proc.stdout}")

    return TestUser(uuid=user_uuid, pin=pin)


def soft_delete_user(user_uuid: str) -> None:
    from cli.utils.pg_connection import get_pg_connection

    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE aico_core.user_profiles
                SET is_active = FALSE, updated_at = NOW()
                WHERE uuid = %s;
                """,
                (user_uuid,),
            )
        conn.commit()
    finally:
        conn.close()


def create_tenant(*, display_name: str) -> str:
    proc = _run_cli(["tenant", "create", "--display-name", display_name])
    if proc.returncode != 0:
        raise RuntimeError(f"tenant create failed: {proc.stdout}\n{proc.stderr}")

    m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", proc.stdout)
    if not m:
        raise RuntimeError(f"tenant create did not print tenant_id: {proc.stdout}")
    return m.group(1)


def tenant_member_add(*, tenant_id: str, user_id: str, role: str = "owner") -> None:
    proc = _run_cli([
        "tenant",
        "member-add",
        "--tenant-id",
        tenant_id,
        "--user-id",
        user_id,
        "--role",
        role,
    ])
    if proc.returncode != 0:
        raise RuntimeError(f"tenant member-add failed: {proc.stdout}\n{proc.stderr}")


def set_rate_limit_config(*, valkey_url: str, rpm: int, window_seconds: int) -> None:
    updates: list[Tuple[str, str]] = [
        ("api_gateway.rate_limiting.enabled", "true"),
        ("api_gateway.rate_limiting.valkey_url", json.dumps(valkey_url)),
        ("api_gateway.rate_limiting.window_seconds", str(window_seconds)),
        ("api_gateway.rate_limiting.default_requests_per_minute", str(rpm)),
    ]

    # Best-effort: if the gateway is running in Docker, write runtime config directly
    # in the container so the in-container ConfigurationManager sees the change.
    # Fallback to CLI config set (host-side) if docker isn't available.
    runtime_yaml = "api_gateway:\n  rate_limiting:\n    enabled: true\n"
    runtime_yaml += f"    valkey_url: {json.dumps(valkey_url)}\n"
    runtime_yaml += f"    window_seconds: {int(window_seconds)}\n"
    runtime_yaml += f"    default_requests_per_minute: {int(rpm)}\n"

    try:
        repo_root = Path(__file__).parent.parent
        gateway_container = os.environ.get("AICO_GATEWAY_CONTAINER", "aico-gateway")
        proc = subprocess.run(
            [
                "docker",
                "exec",
                gateway_container,
                "sh",
                "-lc",
                "mkdir -p /var/lib/aico/runtime && cat > /var/lib/aico/runtime/runtime.yaml <<'EOF'\n"
                + runtime_yaml
                + "EOF\n",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0:
            return
    except Exception:
        pass

    for key, value in updates:
        proc = _run_cli(["config", "set", key, value, "--no-persist"])
        if proc.returncode != 0:
            raise RuntimeError(f"config set failed for {key}: {proc.stdout}\n{proc.stderr}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8771")
    parser.add_argument("--valkey-url", default=os.environ.get("AICO_VALKEY_URL", "redis://127.0.0.1:6379/0"))
    parser.add_argument("--rpm", type=int, default=2)
    parser.add_argument("--window-seconds", type=int, default=60)
    parser.add_argument("--requests", type=int, default=5)
    parser.add_argument("--endpoint", default="/api/v1/users-sessions/sessions")
    parser.add_argument("--method", default="GET")
    parser.add_argument("--pin", default=None)
    parser.add_argument("--user-full-name", default=None)
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    user_full_name = args.user_full_name or f"RateLimitTestUser-{int(time.time())}"
    user_pin = str(args.pin or "TestPass123!a")
    user_pin = user_pin.strip()
    if len(user_pin.encode("utf-8")) > 72:
        user_pin = user_pin.encode("utf-8")[:72].decode("utf-8", errors="ignore")

    pin_bytes_len = len(user_pin.encode("utf-8"))
    print(f"[config] Using test PIN length: {pin_bytes_len} bytes")

    if len(user_pin) < 12:
        raise RuntimeError("PIN/password too short for user-create policy (min 12 chars)")

    test_user: Optional[TestUser] = None
    tenant_id: Optional[str] = None

    try:
        print("[1/5] Creating test user...")
        test_user = create_test_user(full_name=user_full_name, pin=user_pin)
        print(f"      uuid={test_user.uuid}")

        print("[1b/5] Ensuring tenant membership...")
        tenant_id = str(args.tenant_id) if args.tenant_id else None
        if not tenant_id:
            tenant_id = create_tenant(display_name=f"RateLimitTestTenant-{int(time.time())}")
            print(f"      tenant_id={tenant_id}")
        tenant_member_add(tenant_id=tenant_id, user_id=test_user.uuid, role="owner")

        print("[2/5] Applying rate limiting config (runtime-only)...")
        set_rate_limit_config(valkey_url=args.valkey_url, rpm=args.rpm, window_seconds=args.window_seconds)

        print("[3/5] Handshake...")
        client = EncryptedGatewayClient(args.base_url)
        client.perform_handshake()

        print("[4/5] Authenticate...")
        client.authenticate(user_uuid=test_user.uuid, pin=test_user.pin)

        print("[5/5] Hammering endpoint...")
        saw_429 = False
        statuses: list[int] = []
        printed_decrypt_error = False

        method = str(args.method or "GET").upper()

        for i in range(args.requests):
            if method == "GET":
                resp = client.request(method, args.endpoint, json_body=None)
            else:
                resp = client.request(method, args.endpoint, json_body={"timestamp": int(time.time()), "i": i})
            statuses.append(resp.status_code)
            print(f"      {i+1}/{args.requests}: {resp.status_code}")
            if resp.status_code == 429:
                saw_429 = True
                break
            # Some middleware stacks may return HTTP 200 with an encrypted error payload.
            # Try to decode/decrypt and detect embedded rate limit errors.
            try:
                data: Any = resp.json() if resp.content else None
                if isinstance(data, dict) and data.get("encrypted") and "payload" in data:
                    try:
                        data = client.decrypt_payload(data["payload"])
                    except Exception as e:
                        if not printed_decrypt_error:
                            printed_decrypt_error = True
                            print(f"      decrypt_failed={type(e).__name__}: {str(e)[:120]}")

                if i == 0 and isinstance(data, dict):
                    print(f"      decrypted_body_sample={json.dumps(data)[:300]}")

                if isinstance(data, dict):
                    haystack = json.dumps(data)
                    if "Rate limit exceeded" in haystack:
                        print("      detected_rate_limit_in_payload")
                        saw_429 = True
                        break

                    # Generic error detection for payload-wrapped errors
                    if data.get("success") is False or "error" in data:
                        msg = str(data.get("detail") or data.get("message") or data.get("error") or "")
                        if "rate" in msg.lower() and "limit" in msg.lower():
                            print(f"      detected_rate_limit_like_error={msg}")
                            saw_429 = True
                            break
            except Exception:
                # Ignore parse errors; we'll rely on status code and server_error_body for diagnostics.
                pass
            if resp.status_code >= 500:
                try:
                    print(f"      server_error_body={resp.text[:300]}")
                except Exception:
                    pass

        if not saw_429:
            print(f"❌ Did not observe HTTP 429. Statuses: {statuses}")
            return 1

        print(f"✅ Observed HTTP 429. Statuses: {statuses}")
        return 0

    finally:
        if args.cleanup and test_user is not None:
            print("[cleanup] Soft deleting test user...")
            try:
                soft_delete_user(test_user.uuid)
                print("[cleanup] Done")
            except Exception as e:
                print(f"[cleanup] Failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    sys.exit(main())
