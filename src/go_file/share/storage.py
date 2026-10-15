import hashlib
import os
from typing import Any

from .. import paths


class StorageBackend:
    """The contract every storage backend implements.

    ``save`` streams the upload and returns ``(path, sha256, size)``; ``open``
    yields a readable binary handle; ``delete`` is best-effort; ``exists``
    answers whether a previously stored blob is still reachable.
    """

    def save(self, fileobj: Any, name: str) -> tuple[str, str, int]:
        """Return (path, sha256, size)."""
        raise NotImplementedError

    def open(self, path: str) -> Any:
        raise NotImplementedError

    def delete(self, path: str) -> None:
        raise NotImplementedError

    def exists(self, path: str) -> bool:
        raise NotImplementedError


class LocalStorage(StorageBackend):
    def __init__(self, root: str = str(paths.DATA_DIR)) -> None:
        self.root = root
        os.makedirs(root, exist_ok=True)

    def save(self, fileobj: Any, name: str) -> tuple[str, str, int]:
        sha = hashlib.sha256()
        size = 0
        path = os.path.join(self.root, f"{os.urandom(8).hex()}_{os.path.basename(name)}")
        with open(path, "wb") as out:
            while chunk := fileobj.read(65536):
                sha.update(chunk)
                size += len(chunk)
                out.write(chunk)
        return path, sha.hexdigest(), size

    def open(self, path: str) -> Any:
        return open(path, "rb")

    def delete(self, path: str) -> None:
        if os.path.exists(path):
            os.unlink(path)

    def exists(self, path: str) -> bool:
        return os.path.exists(path)


class S3Storage(StorageBackend):
    def __init__(self, bucket: str) -> None:
        import boto3

        self.s3 = boto3.client("s3")
        self.bucket = bucket

    def save(self, fileobj: Any, name: str) -> tuple[str, str, int]:
        sha = hashlib.sha256()
        data = fileobj.read()
        sha.update(data)
        key = f"{os.urandom(8).hex()}_{os.path.basename(name)}"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key, sha.hexdigest(), len(data)

    def open(self, path: str) -> Any:
        import io

        return io.BytesIO(self.s3.get_object(Bucket=self.bucket, Key=path)["Body"].read())

    def delete(self, path: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=path)

    def exists(self, path: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=path)
            return True
        except Exception:
            return False
