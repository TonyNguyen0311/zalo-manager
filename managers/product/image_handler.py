# managers/product/image_handler.py
import logging
from datetime import datetime
from PIL import Image
import io
from googleapiclient.http import MediaIoUploader

class ImageHandler:
    """Handles image optimization and uploading to Google Drive."""

    def __init__(self, drive_service, folder_id):
        """
        Initializes the handler with a pre-configured Google Drive service object.

        Args:
            drive_service: The authenticated Google Drive v3 service object.
            folder_id: The ID of the target Google Drive folder.
        """
        self.service = drive_service
        self.folder_id = folder_id

    def optimize_and_upload_image(self, file_obj, filename, max_width=1024, quality=85):
        """
        Optimizes an image, uploads it to Google Drive, and makes it public.

        Args:
            file_obj: File-like object from Streamlit's uploader.
            filename: The original name of the file.
            max_width: Maximum width for resizing.
            quality: JPEG compression quality.

        Returns:
            A direct-view URL for the uploaded image, or None on failure.
        """
        if not self.service or not self.folder_id:
            logging.warning("Google Drive service or Folder ID not configured. Upload skipped.")
            return None

        try:
            # 1. Optimize Image using Pillow (in-memory)
            img = Image.open(file_obj)
            if img.mode in ("RGBA", "P"): # Convert formats with transparency to RGB
                img = img.convert("RGB")

            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
            img_byte_arr.seek(0)

            # 2. Upload to Google Drive
            unique_filename = f"product_{int(datetime.now().timestamp())}.jpg"
            file_metadata = {
                'name': unique_filename,
                'parents': [self.folder_id]
            }
            media = MediaIoUploader(img_byte_arr, mimetype='image/jpeg', resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            if not file_id:
                raise Exception("Failed to get file ID after upload.")

            logging.info(f"File uploaded to Drive with ID: {file_id}")

            # 3. Make File Publicly Readable
            permission = {'type': 'anyone', 'role': 'reader'}
            self.service.permissions().create(fileId=file_id, body=permission).execute()
            
            # 4. Construct and return the viewable URL
            public_url = f"https://drive.google.com/uc?id={file_id}"
            logging.info(f"Successfully created public URL: {public_url}")
            
            return public_url

        except Exception as e:
            logging.error(f"Google Drive image upload failed: {e}", exc_info=True)
            return None
