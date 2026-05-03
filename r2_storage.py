import os
from datetime import timezone
from typing import Iterable

import boto3
from botocore.config import Config


class R2ConfigError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise R2ConfigError(f"Missing required environment variable: {name}")
    return value


def _endpoint_url() -> str:
    explicit_endpoint = os.getenv("R2_ENDPOINT_URL")
    if explicit_endpoint:
        return explicit_endpoint.rstrip("/")

    account_id = _required_env("R2_ACCOUNT_ID")
    return f"https://{account_id}.r2.cloudflarestorage.com"


def _bucket_name() -> str:
    return _required_env("R2_BUCKET_NAME")


def _client():
    return boto3.client(
        "s3",
        endpoint_url=_endpoint_url(),
        aws_access_key_id=_required_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_required_env("R2_SECRET_ACCESS_KEY"),
        region_name=os.getenv("R2_REGION", "auto"),
        config=Config(signature_version="s3v4"),
    )


def public_url(key: str) -> str:
    public_base_url = os.getenv("R2_PUBLIC_BASE_URL")
    if public_base_url:
        return f"{public_base_url.rstrip('/')}/{key}"
    return key


def put_object(key: str, content: bytes, content_type: str | None = None) -> dict:
    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    _client().put_object(Bucket=_bucket_name(), Key=key, Body=content, **extra_args)
    return {"key": key, "url": public_url(key)}


def delete_object(key: str) -> None:
    _client().delete_object(Bucket=_bucket_name(), Key=key)


def delete_matching_filename(filename: str) -> None:
    for obj in list_objects():
        key = obj["key"]
        if key.endswith(f"_{filename}") or key == filename:
            print(f"Deleting existing R2 object: {key}")
            delete_object(key)


def list_objects() -> list[dict]:
    client = _client()
    paginator = client.get_paginator("list_objects_v2")
    objects = []

    for page in paginator.paginate(Bucket=_bucket_name()):
        for obj in page.get("Contents", []):
            last_modified = obj["LastModified"]
            if last_modified.tzinfo is None:
                last_modified = last_modified.replace(tzinfo=timezone.utc)

            objects.append(
                {
                    "key": obj["Key"],
                    "url": public_url(obj["Key"]),
                    "uploaded_at": last_modified,
                    "size": obj.get("Size", 0),
                }
            )

    return objects


def find_latest_by_filename(filename: str) -> dict | None:
    matches = [
        obj
        for obj in list_objects()
        if obj["key"].endswith(f"_{filename}") or obj["key"] == filename
    ]

    if not matches:
        return None

    return max(matches, key=lambda obj: obj["uploaded_at"])


def latest_object() -> dict | None:
    objects = list_objects()
    if not objects:
        return None

    return max(objects, key=lambda obj: obj["uploaded_at"])


def get_object_stream(key: str, byte_range: str | None = None):
    kwargs = {"Bucket": _bucket_name(), "Key": key}
    if byte_range:
        kwargs["Range"] = byte_range
    return _client().get_object(**kwargs)


def iter_body(body, chunk_size: int = 8192) -> Iterable[bytes]:
    try:
        for chunk in body.iter_chunks(chunk_size=chunk_size):
            if chunk:
                yield chunk
    finally:
        body.close()
