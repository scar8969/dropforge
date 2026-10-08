import hashlib, os, shutil
from .. import paths

class StorageBackend:
    def save(self, fileobj, name: str) -> tuple:
        """Return (path, sha256, size)."""
        raise NotImplementedError

    def open(self, path: str):
        raise NotImplementedError

    def delete(self, path: str) -> None:
        raise NotImplementedError

    def exists(self, path: str) -> bool:
        raise NotImplementedError

class LocalStorage(StorageBackend):
    def __init__(self, root=str(paths.DATA_DIR)):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def save(self, fileobj, name):
        sha = hashlib.sha256()
        size = 0
        path = os.path.join(self.root, f"{os.urandom(8).hex()}_{os.path.basename(name)}")
        with open(path, "wb") as out:
            while chunk := fileobj.read(65536):
                sha.update(chunk); size += len(chunk); out.write(chunk)
        return path, sha.hexdigest(), size

    def open(self, path): return open(path, "rb")

    def delete(self, path):
        if os.path.exists(path): os.unlink(path)

    def exists(self, path): return os.path.exists(path)

class S3Storage(StorageBackend):
    def __init__(self, bucket):
        import boto3
        self.s3 = boto3.client("s3"); self.bucket = bucket

    def save(self, fileobj, name):
        import hashlib
        sha = hashlib.sha256()
        data = fileobj.read()
        sha.update(data)
        key = f"{os.urandom(8).hex()}_{os.path.basename(name)}"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key, sha.hexdigest(), len(data)

    def open(self, path):
        import io
        return io.BytesIO(self.s3.get_object(Bucket=self.bucket, Key=path)["Body"].read())

    def delete(self, path): self.s3.delete_object(Bucket=self.bucket, Key=path)

    def exists(self, path):
        try: self.s3.head_object(Bucket=self.bucket, Key=path); return True
        except Exception: return False
