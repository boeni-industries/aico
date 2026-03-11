import os
from dataclasses import dataclass
from typing import Iterator

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from aico.security.credential_provider import CredentialProvider


@dataclass(frozen=True)
class ArtifactStoreConfig:
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str


class ArtifactStoreClient:
    def __init__(self, cfg: ArtifactStoreConfig):
        self._cfg = cfg
        self._s3 = boto3.client(
            "s3",
            endpoint_url=cfg.endpoint,
            aws_access_key_id=cfg.access_key,
            aws_secret_access_key=cfg.secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4"),
        )

    @property
    def bucket(self) -> str:
        return self._cfg.bucket

    def put_file(self, *, key: str, file_path: str, content_type: str | None = None) -> None:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        self._s3.upload_file(file_path, self._cfg.bucket, key, ExtraArgs=extra_args or None)

    def delete_object(self, *, key: str) -> None:
        self._s3.delete_object(Bucket=self._cfg.bucket, Key=key)

    def copy_object(self, *, source_key: str, dest_key: str) -> None:
        self._s3.copy_object(
            Bucket=self._cfg.bucket,
            Key=dest_key,
            CopySource={"Bucket": self._cfg.bucket, "Key": source_key},
        )

    def move_object(self, *, source_key: str, dest_key: str) -> None:
        # S3/MinIO has no atomic rename; move is implemented as copy+delete.
        self.copy_object(source_key=source_key, dest_key=dest_key)
        self.delete_object(key=source_key)

    def object_exists(self, *, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self._cfg.bucket, Key=key)
            return True
        except ClientError as e:
            code = str(e.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def get_object_iter(self, *, key: str, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        resp = self._s3.get_object(Bucket=self._cfg.bucket, Key=key)
        body = resp["Body"]
        for chunk in body.iter_chunks(chunk_size=chunk_size):
            if chunk:
                yield chunk

    def generate_presigned_get_url(self, *, key: str, expires_seconds: int = 300) -> str:
        return self._s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._cfg.bucket, "Key": key},
            ExpiresIn=int(expires_seconds),
        )


_client: ArtifactStoreClient | None = None


def get_artifact_store_config() -> ArtifactStoreConfig:
    endpoint = os.getenv("AICO_ARTIFACT_STORE_ENDPOINT") or ""
    bucket = os.getenv("AICO_ARTIFACT_STORE_BUCKET") or ""

    provider = CredentialProvider()
    access_key = provider.get("artifact_store_access_key") or ""
    secret_key = provider.get("artifact_store_secret_key") or ""

    if not endpoint:
        raise RuntimeError("Missing AICO_ARTIFACT_STORE_ENDPOINT")
    if not bucket:
        raise RuntimeError("Missing AICO_ARTIFACT_STORE_BUCKET")
    if not access_key:
        raise RuntimeError("Missing artifact_store_access_key secret")
    if not secret_key:
        raise RuntimeError("Missing artifact_store_secret_key secret")

    return ArtifactStoreConfig(
        endpoint=endpoint,
        bucket=bucket,
        access_key=access_key,
        secret_key=secret_key,
    )


def get_artifact_store_client() -> ArtifactStoreClient:
    global _client
    if _client is None:
        _client = ArtifactStoreClient(get_artifact_store_config())
    return _client
