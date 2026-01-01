
import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
import io
from PIL import Image
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageHandler:
    """
    Handles image uploads to Google Drive using OAuth 2.0 (user delegated).
    """
    def __init__(self, credentials_info, folder_id):
        self.folder_id = folder_id
        self.drive_service = self._initialize_drive_service(credentials_info)

    def _initialize_drive_service(self, credentials_info):
        """Initializes the Google Drive service using user-delegated OAuth 2.0 credentials."""
        try:
            # Create credentials using the refresh token flow
            creds = Credentials(
                None,  # No initial access token, it will be refreshed automatically
                refresh_token=credentials_info['refresh_token'],
                token_uri=credentials_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=credentials_info['client_id'],
                client_secret=credentials_info['client_secret'],
                scopes=credentials_info.get('scopes', ['https://www.googleapis.com/auth/drive.file'])
            )
            logger.info("Successfully created Google Drive credentials from refresh token.")
            return build('drive', 'v3', credentials=creds)
        except KeyError as e:
            logger.error(f"Missing key in drive_oauth secrets: {e}")
            st.error(f"Thiếu thông tin {e} trong cấu hình Google Drive OAuth.")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service with OAuth: {e}")
            st.error(f"Lỗi cấu hình Google Drive OAuth: {e}")
            return None

    def _optimize_image(self, image_file, max_width=800, quality=85):
        """
        Resizes and compresses the image before uploading.
        """
        try:
            img = Image.open(image_file)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            if img.width > max_width:
                ratio = max_width / float(img.width)
                height = int(float(img.height) * ratio)
                img = img.resize((max_width, height), Image.LANCZOS)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
            img_byte_arr.seek(0)
            return img_byte_arr
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            st.warning("Không thể tối ưu hóa ảnh. Tải lên ảnh gốc.")
            image_file.seek(0)
            return image_file

    def upload_image(self, image_file, product_sku):
        """
        Optimizes and uploads an image to Google Drive, then makes it public.
        """
        if not self.drive_service:
            st.error("Dịch vụ Google Drive chưa được khởi tạo.")
            return None

        filename = f"{product_sku}.jpg"
        optimized_image_bytes = self._optimize_image(image_file)
        media = MediaIoBaseUpload(optimized_image_bytes, mimetype='image/jpeg', resumable=True)
        file_metadata = {
            'name': filename,
            'parents': [self.folder_id]
        }

        try:
            query = f"name='{filename}' and '{self.folder_id}' in parents and trashed=false"
            response = self.drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
            existing_files = response.get('files', [])

            if existing_files:
                file_id = existing_files[0].get('id')
                request = self.drive_service.files().update(fileId=file_id, media_body=media, fields='id')
            else:
                request = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id')
            
            file = request.execute()
            file_id = file.get('id')

            if file_id:
                self.drive_service.permissions().create(
                    fileId=file_id,
                    body={'type': 'anyone', 'role': 'reader'}
                ).execute()
                
                direct_link = f"https://drive.google.com/uc?id={file_id}"
                st.success(f"Ảnh đã được tải lên thành công!")
                return direct_link

            return None

        except HttpError as error:
            logger.error(f"An HTTP error occurred: {error}")
            st.error(f"Lỗi khi tải ảnh lên: {error}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            st.error(f"Đã có lỗi không mong muốn xảy ra: {e}")
            return None

    def delete_image(self, product_sku):
        """Deletes an image from Google Drive based on product_sku."""
        if not self.drive_service:
            return

        filename = f"{product_sku}.jpg"
        try:
            query = f"name='{filename}' and '{self.folder_id}' in parents and trashed=false"
            response = self.drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
            existing_files = response.get('files', [])

            if existing_files:
                file_id = existing_files[0].get('id')
                self.drive_service.files().delete(fileId=file_id).execute()
                logger.info(f"Successfully deleted image '{filename}' from Google Drive.")
        except Exception as e:
            logger.error(f"Error deleting image '{filename}' from Google Drive: {e}")
