"""
OCR Agent - Extracts text from images and PDFs using Gemini vision models
"""

import json
import logging
from typing import Tuple
from utils.file_handler import file_handler
from utils.api_client import call_ocr_model
from schemas import OCROutput, AgentStatus, FileType

logger = logging.getLogger(__name__)


class OCRAgent:
    """
    Agent responsible for extracting text from images and PDFs
    Uses Gemini vision models with automatic fallback
    """
    
    def __init__(self):
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for OCR"""
        return """You are an expert OCR system specializing in Nepali handwriting and mixed Nepali-English text extraction.

CRITICAL: You MUST extract text from the image. Do not say "I cannot" or refuse.

Your task:
1. Extract ALL text from the provided image accurately - this is MANDATORY
2. Preserve formatting, paragraphs, and structure as much as possible
3. Handle both Nepali Devanagari script and English text
4. If text is unclear, make your best attempt but note uncertainty
5. Maintain the natural flow and order of the text
6. ALWAYS return the JSON format below, even if the text is minimal

Important guidelines:
- Extract text exactly as written, including any spelling errors
- Preserve line breaks and paragraph structure  
- If you encounter illegible sections, mark them as [ILLEGIBLE] but continue
- Pay special attention to handwritten answers in exam format
- Include any diagrams descriptions if present
- Even if the image quality is poor, extract what you can see

Return your response as JSON with this exact format (NO OTHER TEXT):
{
    "student_answer": "extracted text here... (THIS FIELD MUST NOT BE EMPTY)",
    "confidence_score": 0.95,
    "notes": "any notes about illegible sections or quality issues"
}

IMPORTANT: The "student_answer" field MUST contain the extracted text. Never leave it empty.
Be thorough and accurate. This is for exam evaluation purposes."""
    
    async def extract_text(self, file_data: bytes, file_type: str) -> OCROutput:
        """
        Extract text from image or PDF file
        
        Args:
            file_data: File content as bytes
            file_type: "image" or "pdf"
            
        Returns:
            OCROutput with extracted text and confidence score
        """
        try:
            logger.info(f"OCR Agent: Starting extraction for {file_type}")
            
            # Get file info for logging
            file_info = file_handler.get_file_info(file_data)
            logger.info(f"OCR Agent: File info - {file_info}")
            
            # Process file based on type
            if file_type == FileType.IMAGE:
                image_data, quality_modifier = file_handler.process_image(file_data)
                pages_processed = 1
                
            elif file_type == FileType.PDF:
                # PDF processing returns combined image data
                image_data, pages_processed = file_handler.process_pdf(file_data)
                quality_modifier = 0.9  # PDFs generally have good quality
                
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            logger.info(f"OCR Agent: File processed, calling AI model...")
            
            # Call OCR model
            response = await call_ocr_model(self.system_prompt, image_data)
            
            if not response.success:
                raise Exception(f"OCR model failed: {response.error}")
            
            # Parse response
            content = response.data["content"]
            api_source = response.api_source
            
            # Extract JSON from response
            ocr_result = self._parse_ocr_response(content)
            
            # Adjust confidence based on file quality
            final_confidence = min(ocr_result["confidence_score"] * quality_modifier, 1.0)
            
            # Validate extracted text
            extracted_text = ocr_result["student_answer"].strip()
            if not extracted_text:
                raise Exception("No text could be extracted from the image")
            
            if len(extracted_text) < 5:
                logger.warning(f"OCR Agent: Very short text extracted: '{extracted_text}'")
                final_confidence *= 0.7
            
            logger.info(f"OCR Agent: Success! Extracted {len(extracted_text)} characters with confidence {final_confidence:.2f}")
            
            return OCROutput(
                student_answer=extracted_text,
                confidence_score=final_confidence,
                pages_processed=pages_processed,
                status=AgentStatus.SUCCESS,
                api_source=api_source,
                error=None
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"OCR Agent: Error - {error_msg}")
            
            return OCROutput(
                student_answer="",
                confidence_score=0.0,
                pages_processed=0,
                status=AgentStatus.ERROR,
                api_source="none",
                error=error_msg
            )
    
    def _parse_ocr_response(self, response_text: str) -> dict:
        """
        Parse the AI model response to extract OCR results
        
        Args:
            response_text: Raw response from AI model
            
        Returns:
            Dictionary with OCR results
        """
        try:
            # Try to find JSON in the response
            response_text = response_text.strip()
            
            # Look for JSON wrapped in code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            elif "```" in response_text and "{" in response_text:
                # Generic code block with JSON
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif response_text.startswith("{") and response_text.endswith("}"):
                # Direct JSON
                json_str = response_text
            else:
                # Try to find JSON within the text
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = response_text[start:end]
                else:
                    # If no JSON found, treat entire response as extracted text
                    return {
                        "student_answer": response_text,
                        "confidence_score": 0.8,
                        "notes": "Response was not in JSON format"
                    }
            
            # Parse JSON
            result = json.loads(json_str)
            
            # Validate required fields
            if "student_answer" not in result:
                raise ValueError("Missing 'student_answer' field")
            
            # Set defaults for optional fields
            result.setdefault("confidence_score", 0.8)
            result.setdefault("notes", "")
            
            # Ensure confidence is in valid range
            confidence = float(result["confidence_score"])
            result["confidence_score"] = max(0.0, min(1.0, confidence))
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"OCR Agent: JSON parse error - {e}, treating as raw text")
            # Fallback: treat entire response as extracted text
            return {
                "student_answer": response_text,
                "confidence_score": 0.7,
                "notes": f"JSON parse error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"OCR Agent: Response parsing error - {e}")
            raise Exception(f"Failed to parse OCR response: {str(e)}")


# Global OCR agent instance
ocr_agent = OCRAgent()


# Main agent function for workflow integration
async def run_ocr_agent(file_data: bytes, file_type: str) -> OCROutput:
    """
    Main function to run OCR agent
    
    Args:
        file_data: File content as bytes
        file_type: "image" or "pdf"
        
    Returns:
        OCROutput with results
    """
    return await ocr_agent.extract_text(file_data, file_type)