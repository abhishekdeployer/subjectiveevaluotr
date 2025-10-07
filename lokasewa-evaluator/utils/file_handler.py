"""
File handling utilities for processing images and PDFs
"""

import io
import logging
from pathlib import Path
from typing import Tuple, Union
from PIL import Image
import pdf2image
from schemas import FileType

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles file processing for images and PDFs"""
    
    def __init__(self, max_file_size_mb: int = 10, max_pdf_pages: int = 3, image_dpi: int = 300):
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_pdf_pages = max_pdf_pages
        self.image_dpi = image_dpi
    
    def detect_file_type(self, file_data: bytes) -> str:
        """
        Detect if file is PDF or image based on magic numbers
        
        Args:
            file_data: File content as bytes
            
        Returns:
            "pdf" or "image"
            
        Raises:
            ValueError: If file type is not supported
        """
        if not file_data:
            raise ValueError("Empty file data")
        
        # Check PDF magic number
        if file_data[:4] == b'%PDF':
            return FileType.PDF
        
        # Check common image formats
        image_signatures = {
            b'\xff\xd8\xff': 'jpeg',
            b'\x89PNG\r\n\x1a\n': 'png',
            b'GIF87a': 'gif',
            b'GIF89a': 'gif',
            b'BM': 'bmp'
        }
        
        for signature in image_signatures:
            if file_data.startswith(signature):
                return FileType.IMAGE
        
        raise ValueError("Unsupported file format. Please upload JPEG, PNG, GIF, BMP, or PDF.")
    
    def validate_file_size(self, file_data: bytes) -> bool:
        """
        Validate file size is within limits
        
        Args:
            file_data: File content as bytes
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If file is too large
        """
        file_size = len(file_data)
        
        if file_size > self.max_file_size_bytes:
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            current_mb = file_size / (1024 * 1024)
            raise ValueError(f"File too large ({current_mb:.1f}MB). Maximum allowed: {max_mb}MB")
        
        return True
    
    def process_image(self, image_data: bytes) -> Tuple[str, int]:
        """
        Process image data for OCR
        
        Args:
            image_data: Image content as bytes
            
        Returns:
            Tuple of (base64_encoded_image, confidence_modifier)
        """
        try:
            # Validate
            self.validate_file_size(image_data)
            
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (for API efficiency)
            max_dimension = 2048
            if max(image.size) > max_dimension:
                ratio = max_dimension / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized image to {new_size}")
            
            # Convert back to bytes
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=85, optimize=True)
            processed_data = output_buffer.getvalue()
            
            # Base64 encode for API
            import base64
            encoded_image = base64.b64encode(processed_data).decode('utf-8')
            
            # Confidence modifier based on image quality
            confidence_modifier = self._assess_image_quality(image)
            
            logger.info(f"Processed image: {len(processed_data)} bytes, quality modifier: {confidence_modifier}")
            
            return encoded_image, confidence_modifier
            
        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            raise ValueError(f"Failed to process image: {str(e)}")
    
    def process_pdf(self, pdf_data: bytes) -> Tuple[str, int]:
        """
        Process PDF by converting pages to images
        
        Args:
            pdf_data: PDF content as bytes
            
        Returns:
            Tuple of (combined_base64_images, pages_processed)
        """
        try:
            # Validate
            self.validate_file_size(pdf_data)
            
            # Convert PDF pages to images
            images = pdf2image.convert_from_bytes(
                pdf_data, 
                dpi=self.image_dpi, 
                fmt='jpeg',
                first_page=1,
                last_page=self.max_pdf_pages
            )
            
            total_pages = len(images)
            pages_processed = min(total_pages, self.max_pdf_pages)
            
            if total_pages > self.max_pdf_pages:
                logger.warning(f"PDF has {total_pages} pages, processing first {pages_processed}")
            
            # Process each page and combine
            combined_images = []
            
            for i, image in enumerate(images[:pages_processed]):
                logger.debug(f"Processing PDF page {i+1}/{pages_processed}")
                
                # Convert PIL image to bytes
                img_buffer = io.BytesIO()
                image.save(img_buffer, format='JPEG', quality=85)
                img_bytes = img_buffer.getvalue()
                
                # Process as image
                encoded_image, _ = self.process_image(img_bytes)
                combined_images.append(f"=== Page {i+1} ===\n{encoded_image}")
            
            # Combine all pages
            combined_data = "\n\n".join(combined_images)
            
            logger.info(f"Processed PDF: {pages_processed} pages, {len(combined_data)} total bytes")
            
            return combined_data, pages_processed
            
        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            raise ValueError(f"Failed to process PDF: {str(e)}")
    
    def _assess_image_quality(self, image: Image.Image) -> float:
        """
        Assess image quality for OCR confidence adjustment
        
        Args:
            image: PIL Image object
            
        Returns:
            Quality modifier (0.7 to 1.0)
        """
        try:
            width, height = image.size
            total_pixels = width * height
            
            # Size-based quality
            if total_pixels < 100000:  # Very small
                size_factor = 0.7
            elif total_pixels < 500000:  # Small
                size_factor = 0.8
            elif total_pixels < 2000000:  # Medium
                size_factor = 0.9
            else:  # Large
                size_factor = 1.0
            
            # Aspect ratio check (very wide/tall images might have issues)
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > 5:
                aspect_factor = 0.8
            elif aspect_ratio > 3:
                aspect_factor = 0.9
            else:
                aspect_factor = 1.0
            
            # Combine factors
            quality_modifier = min(size_factor * aspect_factor, 1.0)
            
            return max(quality_modifier, 0.7)  # Minimum 0.7
            
        except Exception:
            return 0.8  # Default moderate confidence
    
    def get_file_info(self, file_data: bytes) -> dict:
        """
        Get file information for logging/debugging
        
        Args:
            file_data: File content as bytes
            
        Returns:
            Dictionary with file info
        """
        file_type = self.detect_file_type(file_data)
        file_size_kb = len(file_data) / 1024
        
        info = {
            "file_type": file_type,
            "file_size_kb": round(file_size_kb, 2),
            "file_size_mb": round(file_size_kb / 1024, 2)
        }
        
        if file_type == FileType.IMAGE:
            try:
                image = Image.open(io.BytesIO(file_data))
                info.update({
                    "dimensions": f"{image.size[0]}x{image.size[1]}",
                    "mode": image.mode,
                    "format": image.format
                })
            except Exception:
                pass
        
        return info


# Global file handler instance
file_handler = FileHandler()