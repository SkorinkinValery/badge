"""S3/MinIO object storage wrapper — single point for audio file I/O."""

from __future__ import annotations

import uuid
from io import BytesIO
from typing import IO

import boto3
from botocore.exceptions import ClientError


class StorageKeyNotFoundError(Exception):
    pass


class ObjectStorage:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )

    # ------------------------------------------------------------------
    # Bucket lifecycle
    # ------------------------------------------------------------------

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("404", "NoSuchBucket"):
                self._client.create_bucket(Bucket=self._bucket)
            else:
                raise

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    @staticmethod
    def make_key(recording_id: uuid.UUID, name: str, ext: str) -> str:
        """Deterministic namespaced key: recordings/{id}/{name}{ext}."""
        ext = ext if ext.startswith(".") else f".{ext}"
        return f"recordings/{recording_id}/{name}{ext}"

    # ------------------------------------------------------------------
    # Object operations
    # ------------------------------------------------------------------

    def put_object(
        self,
        key: str,
        data: IO[bytes],
        size: int,
        content_type: str = "application/octet-stream",
    ) -> str:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentLength=size,
            ContentType=content_type,
        )
        return key

    def get_object(self, key: str) -> BytesIO:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return BytesIO(resp["Body"].read())
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("NoSuchKey", "404"):
                raise StorageKeyNotFoundError(key) from exc
            raise

    def presigned_url(self, key: str, expiry: int = 3600) -> str:
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expiry,
        )
        return url

    def delete_object(self, key: str) -> None:
        """Delete a single object from the bucket. No-op if key does not exist."""
        self._client.delete_object(Bucket=self._bucket, Key=key)
