import os

from minio import Minio


def get_minio() -> Minio:
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    secure = endpoint.startswith("https")
    host = endpoint.replace("https://", "").replace("http://", "")
    return Minio(
        host,
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=secure,
    )
