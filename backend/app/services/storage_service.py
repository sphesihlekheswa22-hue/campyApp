import os
import tempfile
from pathlib import Path

from app.config import get_settings

settings = get_settings()


class StorageService:
    """Unified file storage — local disk or S3-compatible (R2, AWS)."""

    def __init__(self) -> None:
        self.backend = (settings.storage_backend or "local").lower()
        self._s3 = None

    def _get_s3(self):
        if self._s3 is None:
            import boto3
            from botocore.config import Config
            kwargs = {
                "aws_access_key_id": settings.s3_access_key,
                "aws_secret_access_key": settings.s3_secret_key,
                "region_name": settings.s3_region or "auto",
                "config": Config(signature_version="s3v4"),
            }
            if settings.s3_endpoint_url:
                kwargs["endpoint_url"] = settings.s3_endpoint_url
            self._s3 = boto3.client("s3", **kwargs)
        return self._s3

    def save(self, key: str, data: bytes) -> str:
        normalized = key.replace("\\", "/").lstrip("/")
        if self.backend == "s3" and settings.s3_bucket:
            self._get_s3().put_object(Bucket=settings.s3_bucket, Key=normalized, Body=data, ContentType=self._content_type(normalized))
            return normalized
        full = os.path.join(settings.upload_dir, normalized)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)
        return normalized

    def read(self, key: str) -> bytes:
        normalized = key.replace("\\", "/").lstrip("/")
        if normalized.startswith("uploads/"):
            normalized = normalized[len("uploads/"):]
        if self.backend == "s3" and settings.s3_bucket:
            resp = self._get_s3().get_object(Bucket=settings.s3_bucket, Key=normalized)
            return resp["Body"].read()
        full = os.path.join(settings.upload_dir, normalized)
        with open(full, "rb") as f:
            return f.read()

    def delete(self, key: str) -> None:
        normalized = key.replace("\\", "/").lstrip("/")
        if normalized.startswith("uploads/"):
            normalized = normalized[len("uploads/"):]
        if self.backend == "s3" and settings.s3_bucket:
            try:
                self._get_s3().delete_object(Bucket=settings.s3_bucket, Key=normalized)
            except Exception:
                pass
            return
        full = os.path.join(settings.upload_dir, normalized)
        if os.path.isfile(full):
            os.remove(full)

    def exists(self, key: str) -> bool:
        normalized = key.replace("\\", "/").lstrip("/")
        if normalized.startswith("uploads/"):
            normalized = normalized[len("uploads/"):]
        if self.backend == "s3" and settings.s3_bucket:
            try:
                self._get_s3().head_object(Bucket=settings.s3_bucket, Key=normalized)
                return True
            except Exception:
                return False
        return os.path.exists(os.path.join(settings.upload_dir, normalized))

    def resolve_local_path(self, key: str) -> str:
        """Return a local filesystem path for tools that need a file (pdfplumber)."""
        normalized = key.replace("\\", "/").lstrip("/")
        if normalized.startswith("uploads/"):
            normalized = normalized[len("uploads/"):]
        if self.backend == "s3" and settings.s3_bucket:
            if not self.exists(normalized):
                raise FileNotFoundError(normalized)
            suffix = Path(normalized).suffix or ".bin"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(self.read(normalized))
            tmp.close()
            return tmp.name
        return os.path.join(settings.upload_dir, normalized)

    def public_url(self, key: str) -> str:
        normalized = key.replace("\\", "/").lstrip("/")
        return f"/api/files/{normalized}"

    @staticmethod
    def content_type(path: str) -> str:
        return StorageService._content_type(path)

    @staticmethod
    def _content_type(path: str) -> str:
        ext = Path(path).suffix.lower()
        return {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }.get(ext, "application/octet-stream")


storage = StorageService()
