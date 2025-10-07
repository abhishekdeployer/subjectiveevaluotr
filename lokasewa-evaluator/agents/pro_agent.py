"""
Pro Agent - Student Advocate that finds strengths and positive aspects
"""

import json
import logging
import time
from utils.api_client import call_pro_agent_model, get_openrouter_generation_cost, extract_generation_id
from schemas import ProAgentOutput, AgentStatus
from config import Config

logger = logging.getLogger(__name__)


class ProAgent:
    """
    Pro Agent acts as the student's advocate, finding strengths and positive aspects
    in their answer compared to the ideal answer
    """
    
    def __init__(self):
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for pro agent"""
        return """You are a fair examiner finding GENUINE STRENGTHS in the student's answer.

Your role: Identify what the student did WELL—but be honest and proportionate.

Analysis Focus:
1. **Correct Content**: Which concepts/facts are accurate?
2. **Relevant Points**: What actually addresses the question?
3. **Structure & Clarity**: Is the answer organized logically?
4. **Examples & Evidence**: Are there appropriate supporting details?
5. **Coverage**: What % of key points from ideal answer are present?

Critical Rules:
• Be FAIR not generous—don't invent strengths that aren't there
• Vague, irrelevant answers have minimal strengths
• Match your assessment to answer quality
• For weak answers: acknowledge any correct elements (even if few)
• For strong answers: highlight comprehensive coverage and depth

Assessment Guidelines by Answer Quality:
★ Excellent (80-100% coverage): "Comprehensive understanding, well-structured, accurate examples"
★ Good (60-79% coverage): "Solid grasp of main concepts, some depth, mostly relevant"
★ Average (40-59% coverage): "Basic understanding present, lacks depth/completeness"
★ Weak (20-39% coverage): "Shows minimal understanding, mostly vague/off-topic"
★ Very Weak (0-19% coverage): "Little to no relevant content, incorrect concepts"

Return JSON format:
{
    "strengths": ["specific strength 1", "specific strength 2", "..."],
    "positive_comparison": "Brief comparison with ideal answer",
    "encouragement": "Proportionate, realistic encouragement",
    "coverage_percentage": 45.0,
    "effort_recognition": "Fair assessment of effort shown"
}

Be supportive BUT realistic—false praise helps no one."""
    
    async def analyze_strengths(self, question: str, student_answer: str, ideal_answer: str) -> ProAgentOutput:
        """
        Analyze student answer to find strengths and positive aspects
        
        Args:
            question: Original exam question
            student_answer: Student's response
            ideal_answer: Model answer for comparison
            
        Returns:
            ProAgentOutput with positive analysis and cost tracking
        """
        start_time = time.time()
        generation_id = None
        cost_usd = 0.0
        cost_npr = 0.0
        
        try:
            logger.info(f"Pro Agent: Analyzing student answer strengths")
            
            # Validate inputs
            if not all([question.strip(), student_answer.strip(), ideal_answer.strip()]):
                raise ValueError("Missing required inputs (question, student answer, or ideal answer)")
            
            # Build analysis prompt
            analysis_prompt = f"""{self.system_prompt}

QUESTION:
{question}

STUDENT'S ANSWER:
{student_answer}

IDEAL ANSWER (for comparison):
{ideal_answer}

Please analyze the student's answer and provide your supportive evaluation focusing on strengths and positive aspects:"""
            
            logger.info(f"Pro Agent: Calling AI model for analysis...")
            
            # Call AI model
            response = await call_pro_agent_model(analysis_prompt)
            
            if not response.success:
                raise Exception(f"AI model failed: {response.error}")
            
            # Extract generation ID for cost tracking
            raw_response = response.data.get("raw_response")
            if raw_response:
                generation_id = extract_generation_id(raw_response)
            
            # Parse response
            content = response.data["content"]
            
            # Extract structured analysis
            analysis_data = self._parse_analysis_response(content)
            
            # Validate analysis
            if not analysis_data.get("strengths"):
                logger.warning("Pro Agent: No strengths identified, adding default")
                analysis_data["strengths"] = ["Student attempted to answer the question"]
            
            # Ensure coverage percentage is valid
            coverage = analysis_data.get("coverage_percentage", 50.0)
            coverage = max(0.0, min(100.0, float(coverage)))
            
            # Get cost from OpenRouter if we have generation_id
            if generation_id:
                cost_data = await get_openrouter_generation_cost(generation_id)
                if cost_data.get("success"):
                    cost_usd = cost_data.get("cost_usd", 0.0)
                    cost_npr = cost_data.get("cost_npr", 0.0)
            
            time_taken = time.time() - start_time
            
            logger.info(f"Pro Agent: Success! {len(analysis_data['strengths'])} strengths, {coverage}% coverage, ${cost_usd:.6f} USD (रू {cost_npr:.4f} NPR), {time_taken:.2f}s")
            
            return ProAgentOutput(
                strengths=analysis_data["strengths"],
                positive_comparison=analysis_data.get("positive_comparison", "Student shows understanding of the topic"),
                encouragement=analysis_data.get("encouragement", "Keep practicing to improve further"),
                coverage_percentage=coverage,
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
            logger.error(f"Pro Agent: Error - {error_msg} (after {time_taken:.2f}s)")
            
            return ProAgentOutput(
                strengths=[],
                positive_comparison="",
                encouragement="",
                coverage_percentage=0.0,
                status=AgentStatus.ERROR,
                error=error_msg,
                generation_id=generation_id,
                cost_usd=cost_usd,
                cost_npr=cost_npr,
                time_taken_seconds=time_taken
            )
    
    def _parse_analysis_response(self, response_text: str) -> dict:
        """
        Parse the AI model response to extract analysis data
        
        Args:
            response_text: Raw response from AI model
            
        Returns:
            Dictionary with analysis components
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
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif response_text.startswith("{") and response_text.endswith("}"):
                json_str = response_text
            else:
                # Try to find JSON within the text
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = response_text[start:end]
                else:
                    # Fallback: extract basic positive analysis from text
                    return self._extract_basic_analysis(response_text)
            
            # Parse JSON
            result = json.loads(json_str)
            
            # Validate and set defaults
            result.setdefault("strengths", ["Student attempted the answer"])
            result.setdefault("positive_comparison", "Shows basic understanding")
            result.setdefault("encouragement", "Continue practicing to improve")
            result.setdefault("coverage_percentage", 50.0)
            result.setdefault("effort_recognition", "Clear effort demonstrated")
            
            # Ensure strengths is a list
            if not isinstance(result["strengths"], list):
                result["strengths"] = [str(result["strengths"])]
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Pro Agent: JSON parse error - {e}, extracting basic analysis")
            return self._extract_basic_analysis(response_text)
        except Exception as e:
            logger.error(f"Pro Agent: Response parsing error - {e}")
            raise Exception(f"Failed to parse Pro Agent response: {str(e)}")
    
    def _extract_basic_analysis(self, response_text: str) -> dict:
        """
        Extract basic analysis from unstructured response text
        
        Args:
            response_text: Unstructured response
            
        Returns:
            Basic analysis dictionary
        """
        try:
            # Look for positive keywords and phrases
            positive_indicators = [
                "good", "well", "correct", "accurate", "clear", "demonstrates",
                "shows", "understands", "relevant", "appropriate", "solid"
            ]
            
            sentences = response_text.replace('\n', ' ').split('.')
            strengths = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if any(indicator in sentence.lower() for indicator in positive_indicators):
                    if len(sentence) > 20:  # Only meaningful sentences
                        strengths.append(sentence[:150])  # Limit length
            
            if not strengths:
                strengths = ["Student provided a response to the question"]
            
            # Extract percentage if mentioned
            coverage = 50.0
            import re
            percentage_match = re.search(r'(\d+)%', response_text)
            if percentage_match:
                coverage = float(percentage_match.group(1))
            
            return {
                "strengths": strengths[:6],  # Max 6 strengths
                "positive_comparison": "Analysis shows some positive aspects",
                "encouragement": "Continue working to improve your responses",
                "coverage_percentage": coverage,
                "effort_recognition": "Effort demonstrated in attempting the question"
            }
            
        except Exception:
            return {
                "strengths": ["Student attempted to answer the question"],
                "positive_comparison": "Basic attempt at addressing the topic",
                "encouragement": "Keep practicing and studying to improve",
                "coverage_percentage": 40.0,
                "effort_recognition": "Shows willingness to engage with the material"
            }


# Global pro agent instance
pro_agent = ProAgent()


# Main agent function for workflow integration
async def run_pro_agent(question: str, student_answer: str, ideal_answer: str) -> ProAgentOutput:
    """
    Main function to run pro agent analysis
    
    Args:
        question: Original exam question
        student_answer: Student's response
        ideal_answer: Model answer for comparison
        
    Returns:
        ProAgentOutput with positive analysis
    """
    return await pro_agent.analyze_strengths(question, student_answer, ideal_answer)