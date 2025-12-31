# managers/product/image_handler.py
import logging
from datetime import datetime
from PIL import Image
import io

class ImageHandler:
    def __init__(self, bucket):
        self.bucket = bucket

    def optimize_and_upload_image(self, file_obj, filename, max_width=1024, quality=85):
        """
        Optimizes an image by resizing and compressing it, then uploads to Firebase Storage.

        Args:
            file_obj: The file-like object from Streamlit's uploader.
            filename: The original name of the file.
            max_width: The maximum width for the resized image.
            quality: The compression quality for JPEG images (1-95).

        Returns:
            The public URL of the uploaded image, or None if it fails.
        """
        if not self.bucket:
            logging.warning("Firebase Storage bucket not configured. Image upload skipped.")
            return None

        try:
            # Load image with Pillow
            img = Image.open(file_obj)

            # --- Optimization Step ---
            # Convert RGBA to RGB for JPEG compatibility if needed
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            # Resize the image if it's wider than max_width
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # "Save" the optimized image to an in-memory buffer
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
            img_byte_arr.seek(0) # Rewind the buffer

            # --- Upload Step ---
            unique_filename = f"{int(datetime.now().timestamp())}_{filename.split('.')[0]}.jpg"
            path = f"products/{unique_filename}"
            blob = self.bucket.blob(path)
            
            # Upload from the in-memory buffer
            blob.upload_from_string(img_byte_arr.getvalue(), content_type="image/jpeg")

            # Make the image publicly accessible
            blob.make_public()
            
            logging.info(f"Successfully uploaded optimized image to {blob.public_url}")
            return blob.public_url

        except Exception as e:
            logging.error(f"Image optimization and upload failed: {e}", exc_info=True)
            return None
