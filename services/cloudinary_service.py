import cloudinary
import cloudinary.uploader
from config.config_variables import settings
from fastapi import UploadFile

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

def upload_receipt(file: UploadFile) -> str:
    if not file:
        return None
    
    try:
        # Imprimimos para ver si las credenciales se cargan
        print(f"Subiendo a Cloudinary: {settings.CLOUDINARY_CLOUD_NAME}")
        
        result = cloudinary.uploader.upload(
            file.file,
            folder="pluxee_expenses",
            resource_type="auto",
            type="upload"
        )
        print("Subida exitosa:", result.get("secure_url"))
        return result.get("secure_url")
    except Exception as e:
        # Si falla, veremos el error exacto en la terminal
        print(f"❌ ERROR SUBIENDO A CLOUDINARY: {str(e)}")
        return None