"""
Ideal Answer Generator Agent - Creates comprehensive model answers for questions
"""

import json
import logging
import time
from utils.api_client import call_ideal_answer_model, get_openrouter_generation_cost, extract_generation_id
from schemas import IdealAnswerOutput, AgentStatus
from config import Config

logger = logging.getLogger(__name__)


class IdealAnswerAgent:
    """
    Agent responsible for generating ideal/model answers for questions
    Uses GPT OSS models to create comprehensive, exam-appropriate responses
    """
    
    def __init__(self):
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for ideal answer generation"""
        return """You are an expert evaluator for competitive examinations across ALL academic and professional domains.

CRITICAL: First analyze the question to determine its SUBJECT AREA, then respond accordingly.

Subject areas you handle:
• Law & Constitution (legal procedures, articles, case law)
• Public Administration (governance, policies, bureaucracy)
• Banking & Finance (financial systems, regulations, economics)
• Business & Marketing (management, strategy, operations)
• Science & Technology (concepts, principles, applications)
• Mathematics (calculations, proofs, problem-solving)
• History & Politics (events, systems, movements)
• Social Sciences (sociology, psychology, development)
• Current Affairs (recent events, policies, reforms)
• General Knowledge (geography, culture, environment)

Your task: Generate the IDEAL ANSWER that would earn FULL MARKS.

Core Requirements:
1. **Context Awareness**: Adapt tone, terminology, and depth to the subject
2. **Completeness**: Address ALL parts of the question
3. **Accuracy**: Only include factually correct, verifiable information
4. **Structure**: Clear introduction → detailed body → concise conclusion
5. **Appropriate Length**: 200-450 words (match question complexity)
6. **Language Flexibility**: Handle questions in ANY language (Nepali, English, Hindi, etc.)

Subject-Specific Guidelines:
• Legal: Article numbers, precedents, procedures (ONLY if question is law-related)
• Technical: Formulas, diagrams descriptions, step-by-step solutions
• Business: Frameworks, real-world examples, strategic analysis
• Descriptive: Clear explanations with relevant examples
• Analytical: Compare, contrast, evaluate with balanced perspective

Avoid:
- Adding irrelevant legal/constitutional references to non-legal questions
- Generic filler content without substance
- Overly verbose language; be precise and direct
- Assumptions about question context

Return JSON format:
{
    "ideal_answer": "your complete model answer here",
    "key_points": ["main point 1", "main point 2", "..."],
    "word_count": 350,
    "subject_area": "identified subject (e.g., business, law, mathematics)"
}

Write precisely what's needed to score full marks—nothing more, nothing less."""
    
    async def generate_ideal_answer(self, question: str) -> IdealAnswerOutput:
        """
        Generate ideal answer for the given question
        
        Args:
            question: The exam question
            
        Returns:
            IdealAnswerOutput with comprehensive model answer and cost tracking
        """
        start_time = time.time()
        generation_id = None
        cost_usd = 0.0
        cost_npr = 0.0
        
        try:
            logger.info(f"Ideal Answer Agent: Generating answer for question (length: {len(question)} chars)")
            
            # Validate question
            question = question.strip()
            if not question:
                raise ValueError("Empty question provided")
            
            if len(question) < 10:
                raise ValueError("Question too short (minimum 10 characters)")
            
            # Build full prompt
            full_prompt = f"{self.system_prompt}\n\nQuestion: {question}\n\nGenerate the ideal answer:"
            
            logger.info(f"Ideal Answer Agent: Calling AI model...")
            
            # Call AI model
            response = await call_ideal_answer_model(full_prompt)
            
            if not response.success:
                raise Exception(f"AI model failed: {response.error}")
            
            # Extract generation ID for cost tracking
            raw_response = response.data.get("raw_response")
            if raw_response:
                generation_id = extract_generation_id(raw_response)
            
            # Parse response
            content = response.data["content"]
            
            # Extract structured data from response
            answer_data = self._parse_answer_response(content)
            
            # Validate generated answer
            ideal_answer = answer_data["ideal_answer"].strip()
            if not ideal_answer:
                raise Exception("No answer content generated")
            
            if len(ideal_answer.split()) < 50:
                logger.warning(f"Ideal Answer Agent: Short answer generated ({len(ideal_answer.split())} words)")
            
            # Calculate actual word count
            actual_word_count = len(ideal_answer.split())
            
            # Get cost from OpenRouter if we have generation_id
            if generation_id:
                cost_data = await get_openrouter_generation_cost(generation_id)
                if cost_data.get("success"):
                    cost_usd = cost_data.get("cost_usd", 0.0)
                    cost_npr = cost_data.get("cost_npr", 0.0)
            
            time_taken = time.time() - start_time
            
            logger.info(f"Ideal Answer Agent: Success! {actual_word_count} words, ${cost_usd:.6f} USD (रू {cost_npr:.4f} NPR), {time_taken:.2f}s")
            
            return IdealAnswerOutput(
                ideal_answer=ideal_answer,
                key_points=answer_data.get("key_points", []),
                word_count=actual_word_count,
                status=AgentStatus.SUCCESS,
                error=None,
                generation_id=generation_id,
                cost_usd=cost_usd,
                cost_npr=cost_npr,
                time_taken_seconds=time_taken
            )
            
        except Exception as e:
            time_taken = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Ideal Answer Agent: Error - {error_msg} (after {time_taken:.2f}s)")
            
            return IdealAnswerOutput(
                ideal_answer="",
                key_points=[],
                word_count=0,
                status=AgentStatus.ERROR,
                error=error_msg,
                generation_id=generation_id,
                cost_usd=cost_usd,
                cost_npr=cost_npr,
                time_taken_seconds=time_taken
            )
    
    def _parse_answer_response(self, response_text: str) -> dict:
        """
        Parse the AI model response to extract structured answer data
        
        Args:
            response_text: Raw response from AI model
            
        Returns:
            Dictionary with answer components
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
                    # If no JSON found, treat entire response as ideal answer
                    return {
                        "ideal_answer": response_text,
                        "key_points": self._extract_key_points(response_text),
                        "word_count": len(response_text.split()),
                        "subject_area": "General"
                    }
            
            # Parse JSON
            result = json.loads(json_str)
            
            # Validate required fields
            if "ideal_answer" not in result:
                raise ValueError("Missing 'ideal_answer' field")
            
            # Set defaults for optional fields
            result.setdefault("key_points", self._extract_key_points(result["ideal_answer"]))
            result.setdefault("word_count", len(result["ideal_answer"].split()))
            result.setdefault("subject_area", "General")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Ideal Answer Agent: JSON parse error - {e}, treating as raw answer")
            # Fallback: treat entire response as ideal answer
            return {
                "ideal_answer": response_text,
                "key_points": self._extract_key_points(response_text),
                "word_count": len(response_text.split()),
                "subject_area": "General"
            }
        except Exception as e:
            logger.error(f"Ideal Answer Agent: Response parsing error - {e}")
            raise Exception(f"Failed to parse ideal answer response: {str(e)}")
    
    def _extract_key_points(self, answer_text: str) -> list:
        """
        Extract key points from answer text as fallback
        
        Args:
            answer_text: The answer content
            
        Returns:
            List of key points
        """
        try:
            # Simple heuristic: look for numbered points, bullet points, or sentences
            lines = answer_text.split('\n')
            key_points = []
            
            for line in lines:
                line = line.strip()
                # Look for numbered points (1., 2., etc.)
                if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                    # Clean up the point
                    point = line.lstrip('0123456789.-• ').strip()
                    if len(point) > 10:  # Only meaningful points
                        key_points.append(point[:100])  # Limit length
            
            # If no structured points found, extract first few sentences
            if not key_points:
                sentences = answer_text.replace('\n', ' ').split('.')
                for sentence in sentences[:5]:  # Max 5 points
                    sentence = sentence.strip()
                    if len(sentence) > 20:  # Only substantial sentences
                        key_points.append(sentence[:100])
            
            return key_points[:8]  # Maximum 8 key points
            
        except Exception:
            return ["Main concepts covered in the answer"]


# Global ideal answer agent instance
ideal_answer_agent = IdealAnswerAgent()


# Main agent function for workflow integration
async def run_ideal_answer_agent(question: str) -> IdealAnswerOutput:
    """
    Main function to run ideal answer agent
    
    Args:
        question: The exam question
        
    Returns:
        IdealAnswerOutput with results
    """
    return await ideal_answer_agent.generate_ideal_answer(question)