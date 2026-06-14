import boto3
from botocore.config import Config as BotoConfig
from app.config import Config

def get_r2_client():
    """Create and return a boto3 client configured for Cloudflare R2."""
    boto_config = BotoConfig(
        signature_version='s3v4',
        retries={'max_attempts': 3}
    )
    return boto3.client(
        's3',
        endpoint_url=Config.R2_ENDPOINT_URL,
        aws_access_key_id=Config.R2_ACCESS_KEY_ID,
        aws_secret_access_key=Config.R2_SECRET_ACCESS_KEY,
        config=boto_config,
        region_name='auto'
    )

def upload_photo_bytes(bytes_data, key):
    """Upload photo bytes to Cloudflare R2 bucket."""
    client = get_r2_client()
    client.put_object(
        Bucket=Config.R2_BUCKET_NAME,
        Key=key,
        Body=bytes_data,
        ContentType='image/webp'
    )

def delete_photo_by_key(key):
    """Delete a photo from Cloudflare R2 bucket by its key."""
    client = get_r2_client()
    client.delete_object(
        Bucket=Config.R2_BUCKET_NAME,
        Key=key
    )
