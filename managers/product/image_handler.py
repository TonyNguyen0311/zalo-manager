import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from PIL import Image
import io
from googleapiclient.http import MediaIoBaseUpload

class ImageHandler:
    """Handles image optimization and uploading to Google Drive."""

    def __init__(self, gdrive_service_account_info, folder_id):
        if not gdrive_service_account_info:
            raise ValueError("Google Drive service account information is not provided.")
        if not folder_id:
            raise ValueError("Google Drive folder ID is not provided.")

        creds = Credentials.from_service_account_info(
            gdrive_service_account_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        self.service = build('drive', 'v3', credentials=creds)
        self.folder_id = folder_id

    def optimize_image(self, uploaded_file, max_size=(1024, 1024), quality=85):
        """Resizes and compresses the image."""
        try:
            img = Image.open(uploaded_file)
            img.thumbnail(max_size)
            
            # Convert to RGB if it's RGBA to avoid issues with saving as JPEG
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality)
            buffer.seek(0)
            return buffer
        except Exception as e:
            st.error(f"Lỗi tối ưu hóa hình ảnh: {e}")
            return None

    def upload_image(self, image_buffer, product_name):
        """Uploads the image buffer to Google Drive and returns the web view link."""
        if image_buffer is None:
            return None
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{product_name.replace(' ', '_')}_{timestamp}.jpg"

            file_metadata = {
                'name': file_name,
                'parents': [self.folder_id]
            }
            
            media = MediaIoBaseUpload(image_buffer, mimetype='image/jpeg', resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            # Make the file publicly readable
            file_id = file.get('id')
            self.service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
            
            # It's better to return the direct webViewLink
            return file.get('webViewLink')

        except Exception as e:
            st.error(f"Lỗi tải ảnh lên Google Drive: {e}")
            return None