import asyncio
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from api.core.config import Settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class S3Storage:
    """S3-compatible storage (MinIO locally). boto3 is sync, so calls run in a thread."""

    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket_media
        self._client: S3Client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
            config=Config(
                signature_version="s3v4",
                connect_timeout=2,
                read_timeout=5,
                retries={"max_attempts": 2},
            ),
        )

    async def ping(self) -> None:
        await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)

    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get_object(self, key: str) -> bytes:
        response = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def presigned_get_url(self, key: str, expires_s: int = 900) -> str:
        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_s,
        )
