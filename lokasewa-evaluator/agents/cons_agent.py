"""
Cons Agent - Constructive Critic that identifies gaps and areas for improvement
"""

import json
import logging
import time
from utils.api_client import call_cons_agent_model, get_openrouter_generation_cost, extract_generation_id
from schemas import ConsAgentOutput, AgentStatus, Severity
from config import Config

logger = logging.getLogger(__name__)


class ConsAgent:
    """
    Cons Agent acts as a constructive critic, identifying gaps and areas for improvement
    in the student's answer compared to the ideal answer
    """
    
    def __init__(self):
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for cons agent"""
        return """You are a STRICT examiner identifying ALL GAPS and WEAKNESSES in the student's answer.

Your role: Be CRITICAL and THOROUGH—find every flaw, omission, and weakness.

Critical Analysis Areas:
1. **Missing Content**: What key points from ideal answer are absent?
2. **Incorrect Information**: Any factual errors, misconceptions, wrong data?
3. **Vagueness**: Where is the answer too general/superficial without specifics?
4. **Irrelevance**: Content that doesn't address the question?
5. **Structure Issues**: Poor organization, lack of flow, missing sections?
6. **Insufficient Depth**: Shallow treatment where depth is required?

Severity Assessment (BE HONEST):
★ "critical": Answer is fundamentally flawed, mostly incorrect/irrelevant, fails to address question
★ "significant": Major gaps, missing core concepts, vague/superficial, needs substantial work
★ "moderate": Several important points missing, some errors, needs improvement
★ "minor": Mostly complete, few small gaps, nearly meets standard

Rules for Strict Evaluation:
• Vague answers (e.g., "I like fruits") to serious questions = CRITICAL/SIGNIFICANT severity
• Missing 50%+ of key points = SIGNIFICANT severity minimum
• Irrelevant content wastes space = major weakness
• Generic statements without specifics = inadequate depth
• Don't be lenient—every gap matters for exam success

For Weak Answers, You MUST note:
- "Extremely vague—no specific information provided"
- "Does not address the question asked"
- "Missing all key concepts from ideal answer"
- "Lacks any substantive content"
- "Answer is too brief/incomplete for the question complexity"

Return JSON format:
{
    "gaps_identified": ["specific gap 1", "specific gap 2", "..."],
    "areas_for_improvement": ["improvement 1", "improvement 2", "..."],
    "constructive_feedback": "Direct feedback on what needs fixing",
    "severity": "critical|significant|moderate|minor",
    "missing_key_concepts": ["concept1", "concept2", "..."]
}

Be RUTHLESSLY HONEST—students need to know exactly where they fall short."""
    
    async def analyze_weaknesses(self, question: str, student_answer: str, ideal_answer: str) -> ConsAgentOutput:
        """
        Analyze student answer to identify gaps and areas for improvement
        
        Args:
            question: Original exam question
            student_answer: Student's response
            ideal_answer: Model answer for comparison
            
        Returns:
            ConsAgentOutput with constructive criticism and cost tracking
        """
        start_time = time.time()
        generation_id = None
        cost_usd = 0.0
        cost_npr = 0.0
        
        try:
            logger.info(f"Cons Agent: Analyzing answer gaps and weaknesses")
            
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

Please analyze the student's answer and provide constructive criticism focusing on gaps and areas for improvement:"""
            
            logger.info(f"Cons Agent: Calling AI model for analysis...")
            
            # Call AI model
            response = await call_cons_agent_model(analysis_prompt)
            
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
            if not analysis_data.get("gaps_identified"):
                # Even good answers should have some minor suggestions
                analysis_data["gaps_identified"] = ["Consider adding more specific examples"]
            
            # Ensure severity is valid
            severity = analysis_data.get("severity", "moderate")
            if severity not in ["minor", "moderate", "significant"]:
                severity = "moderate"
            
            # Get cost from OpenRouter if we have generation_id
            if generation_id:
                cost_data = await get_openrouter_generation_cost(generation_id)
                if cost_data.get("success"):
                    cost_usd = cost_data.get("cost_usd", 0.0)
                    cost_npr = cost_data.get("cost_npr", 0.0)
            
            time_taken = time.time() - start_time
            
            logger.info(f"Cons Agent: Success! {len(analysis_data['gaps_identified'])} gaps, severity: {severity}, ${cost_usd:.6f} USD (रू {cost_npr:.4f} NPR), {time_taken:.2f}s")
            
            return ConsAgentOutput(
                gaps_identified=analysis_data["gaps_identified"],
                areas_for_improvement=analysis_data.get("areas_for_improvement", []),
                constructive_feedback=analysis_data.get("constructive_feedback", "Focus on addressing the identified gaps"),
                severity=Severity(severity),
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
            logger.error(f"Cons Agent: Error - {error_msg} (after {time_taken:.2f}s)")
            
            return ConsAgentOutput(
                gaps_identified=[],
                areas_for_improvement=[],
                constructive_feedback="",
                severity=Severity.MODERATE,
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
                    # Fallback: extract basic criticism from text
                    return self._extract_basic_criticism(response_text)
            
            # Parse JSON
            result = json.loads(json_str)
            
            # Validate and set defaults
            result.setdefault("gaps_identified", ["Could be more comprehensive"])
            result.setdefault("areas_for_improvement", ["Add more depth and examples"])
            result.setdefault("constructive_feedback", "Consider strengthening your analysis with more details")
            result.setdefault("severity", "moderate")
            result.setdefault("missing_key_concepts", [])
            
            # Ensure lists are actually lists
            for field in ["gaps_identified", "areas_for_improvement", "missing_key_concepts"]:
                if not isinstance(result[field], list):
                    result[field] = [str(result[field])] if result[field] else []
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Cons Agent: JSON parse error - {e}, extracting basic criticism")
            return self._extract_basic_criticism(response_text)
        except Exception as e:
            logger.error(f"Cons Agent: Response parsing error - {e}")
            raise Exception(f"Failed to parse Cons Agent response: {str(e)}")
    
    def _extract_basic_criticism(self, response_text: str) -> dict:
        """
        Extract basic criticism from unstructured response text
        
        Args:
            response_text: Unstructured response
            
        Returns:
            Basic criticism dictionary
        """
        try:
            # Look for critical keywords and phrases
            critical_indicators = [
                "missing", "lacks", "incomplete", "insufficient", "could", "should",
                "needs", "requires", "absent", "overlooks", "fails", "weak"
            ]
            
            sentences = response_text.replace('\n', ' ').split('.')
            gaps = []
            improvements = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if any(indicator in sentence.lower() for indicator in critical_indicators):
                    if len(sentence) > 15:  # Only meaningful sentences
                        if "missing" in sentence.lower() or "lacks" in sentence.lower():
                            gaps.append(sentence[:150])
                        else:
                            improvements.append(sentence[:150])
            
            if not gaps:
                gaps = ["Could benefit from more detailed analysis"]
            if not improvements:
                improvements = ["Add more specific examples and evidence"]
            
            # Determine severity based on content
            severity = "moderate"
            if any(word in response_text.lower() for word in ["excellent", "good", "strong"]):
                severity = "minor"
            elif any(word in response_text.lower() for word in ["poor", "inadequate", "seriously"]):
                severity = "significant"
            
            return {
                "gaps_identified": gaps[:6],  # Max 6 gaps
                "areas_for_improvement": improvements[:6],  # Max 6 improvements
                "constructive_feedback": "Focus on addressing the identified areas for a stronger response",
                "severity": severity,
                "missing_key_concepts": []
            }
            
        except Exception:
            return {
                "gaps_identified": ["Analysis could be more comprehensive"],
                "areas_for_improvement": ["Include more specific examples and details"],
                "constructive_feedback": "Work on providing more depth in your analysis",
                "severity": "moderate",
                "missing_key_concepts": []
            }


# Global cons agent instance
cons_agent = ConsAgent()


# Main agent function for workflow integration
async def run_cons_agent(question: str, student_answer: str, ideal_answer: str) -> ConsAgentOutput:
    """
    Main function to run cons agent analysis
    
    Args:
        question: Original exam question
        student_answer: Student's response
        ideal_answer: Model answer for comparison
        
    Returns:
        ConsAgentOutput with constructive criticism
    """
    return await cons_agent.analyze_weaknesses(question, student_answer, ideal_answer)