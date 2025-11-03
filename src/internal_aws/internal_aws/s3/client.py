"""
S3 client for file operations.

Provides async S3 operations with aioboto3.
"""

import json
from typing import Optional, Dict, Any, List, BinaryIO, Union, Type, TypeVar
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

try:
    import aioboto3
except ImportError:
    raise ImportError(
        "aioboto3 is required for S3 operations. "
        "Install it with: pip install aioboto3"
    )

from ..auth.credentials import CredentialProvider, DefaultCredentialProvider


T = TypeVar('T', bound=BaseModel)


class S3ClientConfig(BaseModel):
    """S3 client configuration."""

    bucket_name: str = Field(description="S3 bucket name")
    region: str = Field(default="us-east-1", description="AWS region")
    endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom endpoint URL (for LocalStack, MinIO, etc.)"
    )


class S3Client:
    """
    S3 client for file operations.

    Provides async methods for S3 operations including upload, download, list, delete, etc.

    Example:
        from internal_aws import S3Client, S3ClientConfig

        config = S3ClientConfig(
            bucket_name="my-bucket",
            region="us-east-1"
        )

        client = S3Client(config)

        # Upload file
        await client.upload_file("local.txt", "remote.txt")

        # Download file
        await client.download_file("remote.txt", "local.txt")

        # List objects
        keys = await client.list_objects(prefix="data/")

        # Get object as bytes
        content = await client.get_object_as_bytes("file.txt")

        # Get object as JSON
        data = await client.get_object_as_json("config.json")

        # Delete object
        await client.delete_object("old-file.txt")
    """

    def __init__(
        self,
        config: S3ClientConfig,
        credential_provider: Optional[CredentialProvider] = None
    ):
        """
        Initialize S3 client.

        Args:
            config: S3 client configuration
            credential_provider: Optional credential provider (defaults to DefaultCredentialProvider)

        Example:
            config = S3ClientConfig(bucket_name="my-bucket", region="us-east-1")
            client = S3Client(config)
        """
        self.config = config
        self.credential_provider = credential_provider or DefaultCredentialProvider()

    async def _get_credentials(self):
        """Get AWS credentials from provider."""
        return await self.credential_provider.get_credentials()

    async def _get_client_kwargs(self) -> Dict[str, Any]:
        """
        Get client kwargs including credentials.

        Returns:
            Dictionary of kwargs for aioboto3 client creation
        """
        kwargs: Dict[str, Any] = {
            "service_name": "s3",
            "region_name": self.config.region,
        }

        if self.config.endpoint_url:
            kwargs["endpoint_url"] = self.config.endpoint_url

        creds = await self._get_credentials()
        if creds:
            creds_dict = creds.to_dict()
            kwargs.update(creds_dict)

        return kwargs

    @asynccontextmanager
    async def get_client(self):
        """
        Get S3 client as async context manager.

        Yields:
            aioboto3 S3 client

        Example:
            async with client.get_client() as s3:
                response = await s3.list_objects_v2(Bucket="my-bucket")
        """
        session = aioboto3.Session()
        kwargs = await self._get_client_kwargs()
        async with session.client(**kwargs) as s3_client:
            yield s3_client

    async def upload_file(
        self,
        local_path: str,
        s3_key: str,
        extra_args: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Upload file to S3.

        Args:
            local_path: Local file path
            s3_key: S3 object key
            extra_args: Extra arguments for upload (e.g., ContentType, Metadata)

        Returns:
            True if successful

        Example:
            await client.upload_file(
                "data.json",
                "uploads/data.json",
                extra_args={"ContentType": "application/json"}
            )
        """
        async with self.get_client() as s3:
            await s3.upload_file(
                local_path,
                self.config.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
        return True

    async def upload_fileobj(
        self,
        fileobj: BinaryIO,
        s3_key: str,
        extra_args: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Upload file object to S3.

        Args:
            fileobj: File-like object to upload
            s3_key: S3 object key
            extra_args: Extra arguments for upload

        Returns:
            True if successful

        Example:
            with open("data.bin", "rb") as f:
                await client.upload_fileobj(f, "uploads/data.bin")
        """
        async with self.get_client() as s3:
            await s3.upload_fileobj(
                fileobj,
                self.config.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
        return True

    async def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download file from S3.

        Args:
            s3_key: S3 object key
            local_path: Local file path to save

        Returns:
            True if successful

        Example:
            await client.download_file("data/file.txt", "local-file.txt")
        """
        async with self.get_client() as s3:
            await s3.download_file(
                self.config.bucket_name,
                s3_key,
                local_path
            )
        return True

    async def list_objects(
        self,
        prefix: str = "",
        delimiter: str = "",
        max_keys: int = 1000
    ) -> List[str]:
        """
        List objects in S3 bucket.

        Args:
            prefix: Object key prefix to filter
            delimiter: Delimiter for grouping keys (e.g., "/" for folders)
            max_keys: Maximum number of keys to return

        Returns:
            List of object keys

        Example:
            # List all objects in "data/" prefix
            keys = await client.list_objects(prefix="data/")

            # List "folders" in root
            folders = await client.list_objects(delimiter="/")
        """
        async with self.get_client() as s3:
            response = await s3.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix,
                Delimiter=delimiter,
                MaxKeys=max_keys
            )

            keys = []
            if "Contents" in response:
                keys = [obj["Key"] for obj in response["Contents"]]

            return keys

    async def get_object(self, s3_key: str) -> Dict[str, Any]:
        """
        Get object from S3.

        Args:
            s3_key: S3 object key

        Returns:
            S3 GetObject response dictionary

        Example:
            response = await client.get_object("data.json")
            body = await response["Body"].read()
        """
        async with self.get_client() as s3:
            response = await s3.get_object(
                Bucket=self.config.bucket_name,
                Key=s3_key
            )
            return response

    async def get_object_body(self, s3_key: str) -> bytes:
        """
        Get object body as bytes.

        Args:
            s3_key: S3 object key

        Returns:
            Object body as bytes

        Example:
            content = await client.get_object_body("file.bin")
        """
        response = await self.get_object(s3_key)
        async with response["Body"] as stream:
            return await stream.read()

    async def delete_object(self, s3_key: str) -> Dict[str, Any]:
        """
        Delete object from S3.

        Args:
            s3_key: S3 object key

        Returns:
            S3 DeleteObject response

        Example:
            await client.delete_object("old-file.txt")
        """
        async with self.get_client() as s3:
            response = await s3.delete_object(
                Bucket=self.config.bucket_name,
                Key=s3_key
            )
            return response

    async def delete_objects(self, s3_keys: List[str]) -> Dict[str, Any]:
        """
        Delete multiple objects from S3.

        Args:
            s3_keys: List of S3 object keys

        Returns:
            S3 DeleteObjects response

        Example:
            await client.delete_objects(["file1.txt", "file2.txt", "file3.txt"])
        """
        async with self.get_client() as s3:
            response = await s3.delete_objects(
                Bucket=self.config.bucket_name,
                Delete={
                    "Objects": [{"Key": key} for key in s3_keys]
                }
            )
            return response

    async def get_presigned_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
        http_method: str = "GET"
    ) -> str:
        """
        Generate presigned URL for S3 object.

        Args:
            s3_key: S3 object key
            expires_in: URL expiration time in seconds
            http_method: HTTP method (GET, PUT, etc.)

        Returns:
            Presigned URL string

        Example:
            # Generate download URL (valid for 1 hour)
            url = await client.get_presigned_url("file.txt")

            # Generate upload URL (valid for 5 minutes)
            upload_url = await client.get_presigned_url(
                "upload.txt",
                expires_in=300,
                http_method="PUT"
            )
        """
        async with self.get_client() as s3:
            method_map = {
                "GET": "get_object",
                "PUT": "put_object",
                "DELETE": "delete_object"
            }
            client_method = method_map.get(http_method.upper(), "get_object")

            url = await s3.generate_presigned_url(
                client_method,
                Params={
                    "Bucket": self.config.bucket_name,
                    "Key": s3_key
                },
                ExpiresIn=expires_in
            )
            return url

    async def copy_object(
        self,
        source_key: str,
        target_key: str,
        source_bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        metadata_directive: str = "COPY"
    ) -> Dict[str, Any]:
        """
        Copy object within S3.

        Args:
            source_key: Source object key
            target_key: Target object key
            source_bucket: Source bucket (defaults to same bucket)
            metadata: New metadata for target object
            metadata_directive: "COPY" or "REPLACE"

        Returns:
            S3 CopyObject response

        Example:
            # Copy within same bucket
            await client.copy_object("old.txt", "new.txt")

            # Copy from another bucket
            await client.copy_object(
                "file.txt",
                "backup/file.txt",
                source_bucket="other-bucket"
            )
        """
        source_bucket = source_bucket or self.config.bucket_name
        copy_source = {"Bucket": source_bucket, "Key": source_key}

        async with self.get_client() as s3:
            kwargs = {
                "CopySource": copy_source,
                "Bucket": self.config.bucket_name,
                "Key": target_key,
                "MetadataDirective": metadata_directive
            }
            if metadata:
                kwargs["Metadata"] = metadata

            response = await s3.copy_object(**kwargs)
            return response

    async def put_object(
        self,
        s3_key: str,
        body: Union[bytes, str, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Put object to S3.

        Args:
            s3_key: S3 object key
            body: Object body (bytes, string, or file-like object)
            content_type: Content type (e.g., "application/json")
            metadata: Object metadata

        Returns:
            S3 PutObject response

        Example:
            # Put bytes
            await client.put_object("data.bin", b"binary data")

            # Put string
            await client.put_object(
                "data.txt",
                "text content",
                content_type="text/plain"
            )

            # Put with metadata
            await client.put_object(
                "file.txt",
                "content",
                metadata={"author": "john"}
            )
        """
        async with self.get_client() as s3:
            kwargs = {
                "Bucket": self.config.bucket_name,
                "Key": s3_key,
                "Body": body
            }
            if content_type:
                kwargs["ContentType"] = content_type
            if metadata:
                kwargs["Metadata"] = metadata

            response = await s3.put_object(**kwargs)
            return response

    async def get_object_as_bytes(self, s3_key: str) -> bytes:
        """
        Get object as bytes.

        Args:
            s3_key: S3 object key

        Returns:
            Object content as bytes

        Example:
            content = await client.get_object_as_bytes("file.bin")
        """
        return await self.get_object_body(s3_key)

    async def get_object_as_string(
        self,
        s3_key: str,
        encoding: str = 'utf-8'
    ) -> str:
        """
        Get object as string.

        Args:
            s3_key: S3 object key
            encoding: String encoding

        Returns:
            Object content as string

        Example:
            text = await client.get_object_as_string("file.txt")
        """
        content = await self.get_object_body(s3_key)
        return content.decode(encoding)

    async def get_object_as_json(self, s3_key: str) -> Dict[str, Any]:
        """
        Get object as JSON.

        Args:
            s3_key: S3 object key

        Returns:
            Parsed JSON object

        Example:
            data = await client.get_object_as_json("config.json")
            print(data["setting"])
        """
        content = await self.get_object_as_string(s3_key)
        return json.loads(content)

    async def get_object_as_model(
        self,
        s3_key: str,
        model_class: Type[T]
    ) -> T:
        """
        Get object as Pydantic model.

        Args:
            s3_key: S3 object key
            model_class: Pydantic model class

        Returns:
            Pydantic model instance

        Example:
            from pydantic import BaseModel

            class Config(BaseModel):
                name: str
                value: int

            config = await client.get_object_as_model("config.json", Config)
            print(config.name)
        """
        data = await self.get_object_as_json(s3_key)
        return model_class.model_validate(data)
