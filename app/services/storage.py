import boto3
from botocore.config import Config
from pathlib import Path
from app.core.config import settings

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )

def upload_file(local_path: str, key: str) -> str:
    """Upload un fichier sur R2 et retourne son URL publique."""
    client = get_r2_client()
    client.upload_file(local_path, settings.R2_BUCKET_NAME, key)
    return f"{settings.R2_PUBLIC_URL}/{key}"

def upload_bytes(data: bytes, key: str, content_type: str = "application/pdf") -> str:
    client = get_r2_client()
    client.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"{settings.R2_PUBLIC_URL}/{key}"

def delete_file(key: str):
    client = get_r2_client()
    client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
