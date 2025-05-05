import boto3
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os

# Функция для загрузки файла в S3
def upload_to_s3(file, file_name):
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )

    try:
        # Используем правильное имя бакета
        s3_client.upload_fileobj(
            file,
            os.getenv('AWS_BUCKET_NAME'),  # Исправление тут
            file_name,
            ExtraArgs={'ACL': 'public-read'}
        )
        # Получаем URL файла
        file_url = f"https://{os.getenv('AWS_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{file_name}"
        return file_url
    except Exception as e:
        raise e
