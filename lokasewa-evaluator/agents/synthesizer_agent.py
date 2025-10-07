"""
Synthesizer Agent - Final evaluator that combines all analyses into comprehensive evaluation
"""

import json
import logging
import time
from typing import List, Dict
from utils.api_client import call_synthesizer_model, get_openrouter_generation_cost, extract_generation_id
from schemas import SynthesizerOutput, EvaluationParameter, AgentStatus, ProAgentOutput, ConsAgentOutput
from config import Config

logger = logging.getLogger(__name__)


class SynthesizerAgent:
    """
    Synthesizer Agent combines all previous analyses into a final comprehensive evaluation
    Generates dynamic parameters, calculates final marks, and provides personalized feedback
    """
    
    def __init__(self):
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for synthesizer agent"""
        return """You are the CHIEF EXAMINER delivering the FINAL EVALUATION. Combine all analyses into a fair, comprehensive assessment.

Available Inputs:
1. Original Question
2. Student's Answer
3. Ideal Answer (benchmark)
4. Pro Analysis (strengths found)
5. Cons Analysis (gaps/weaknesses found)

Your Task (4 Steps):

**STEP 1: DYNAMIC PARAMETER GENERATION**
Create 10 evaluation parameters SPECIFIC to the question's subject and requirements.

Parameter Examples by Domain:
• Law: Legal accuracy, article knowledge, precedent awareness, interpretation, application
• Business: Conceptual clarity, frameworks used, real-world application, strategic thinking
• Science/Math: Technical accuracy, formula application, problem-solving approach, calculations
• Administrative: Policy understanding, governance concepts, stakeholder analysis, feasibility
• Descriptive: Argument quality, logical flow, evidence quality, critical thinking, originality

Mix domain-specific + universal parameters (e.g., clarity, structure, completeness).

**STEP 2: STRICT SCORING** (Out of 10 each)
Use this rubric for EACH parameter:
• 9-10: Exceptional—matches/exceeds ideal answer quality
• 7-8: Good—solid understanding, minor gaps only
• 5-6: Average—basic grasp but lacks depth/completeness
• 3-4: Weak—significant gaps, vague/superficial
• 1-2: Very weak—mostly incorrect/irrelevant
• 0: Completely missing or wrong

Critical Scoring Rules:
- Vague answers without specifics = MAX 4-5 points/parameter
- Missing 50%+ of key points = MAX 40-50/100 total
- Irrelevant answers = corresponding parameters get 0-2 points
- Be STRICT—don't inflate scores out of sympathy

**STEP 3: PERSONALIZED FEEDBACK** (250-350 words)
Structure: Overall assessment → Strengths → Weaknesses → Recommendations → Encouragement
- Be HONEST about quality level
- Don't sugarcoat weak performance
- Provide actionable, specific improvement steps
- Balance criticism with constructive guidance

**STEP 4: FINAL MARKS**
Sum all parameter scores = Final Marks (out of 100)

Typical Distribution:
• 80-100: Excellent (comprehensive, accurate, well-structured)
• 60-79: Good (solid understanding, minor gaps)
• 40-59: Average (basic grasp, needs improvement)
• 20-39: Weak (major gaps, vague/incomplete)
• 0-19: Very weak (mostly incorrect/irrelevant)

Return JSON format:
{
    "final_marks": 45,
    "evaluation_parameters": [
        {"parameter": "X", "score": 4, "max_score": 10, "comment": "specific reason"},
        ... // 10 total parameters
    ],
    "personalized_feedback": "Complete assessment...",
    "strengths_summary": "What they did well",
    "improvement_areas": "What needs work",
    "recommendations": ["specific action 1", "specific action 2", "..."],
    "overall_assessment": "One-line summary"
}

BE FAIR BUT STRICT—accurate assessment helps students improve."""
    
    async def synthesize_evaluation(
        self, 
        question: str, 
        student_answer: str, 
        ideal_answer: str,
        pro_analysis: ProAgentOutput, 
        cons_analysis: ConsAgentOutput
    ) -> SynthesizerOutput:
        """
        Synthesize all analyses into final comprehensive evaluation
        
        Args:
            question: Original exam question
            student_answer: Student's response
            ideal_answer: Model answer
            pro_analysis: Pro agent's positive analysis
            cons_analysis: Cons agent's gap analysis
            
        Returns:
            SynthesizerOutput with final evaluation and cost tracking
        """
        start_time = time.time()
        generation_id = None
        cost_usd = 0.0
        cost_npr = 0.0
        
        try:
            logger.info(f"Synthesizer Agent: Starting final evaluation synthesis")
            
            # Validate inputs
            if not all([question.strip(), student_answer.strip(), ideal_answer.strip()]):
                raise ValueError("Missing required inputs")
            
            if pro_analysis.status != AgentStatus.SUCCESS:
                raise ValueError("Pro agent analysis failed")
            
            if cons_analysis.status != AgentStatus.SUCCESS:
                raise ValueError("Cons agent analysis failed")
            
            # Build comprehensive synthesis prompt
            synthesis_prompt = f"""{self.system_prompt}

QUESTION:
{question}

STUDENT'S ANSWER:
{student_answer}

IDEAL ANSWER:
{ideal_answer}

PRO AGENT ANALYSIS (Strengths):
- Strengths: {', '.join(pro_analysis.strengths)}
- Positive Comparison: {pro_analysis.positive_comparison}
- Coverage: {pro_analysis.coverage_percentage}%
- Encouragement: {pro_analysis.encouragement}

CONS AGENT ANALYSIS (Gaps):
- Gaps Identified: {', '.join(cons_analysis.gaps_identified)}
- Areas for Improvement: {', '.join(cons_analysis.areas_for_improvement)}
- Constructive Feedback: {cons_analysis.constructive_feedback}
- Severity: {cons_analysis.severity}

Now provide your final comprehensive evaluation:"""
            
            logger.info(f"Synthesizer Agent: Calling AI model for synthesis...")
            
            # Call AI model
            response = await call_synthesizer_model(synthesis_prompt)
            
            if not response.success:
                raise Exception(f"AI model failed: {response.error}")
            
            # Extract generation ID for cost tracking
            raw_response = response.data.get("raw_response")
            if raw_response:
                generation_id = extract_generation_id(raw_response)
            
            # Parse response
            content = response.data["content"]
            
            # Extract structured evaluation
            evaluation_data = self._parse_evaluation_response(content)
            
            # Validate evaluation
            if not evaluation_data.get("evaluation_parameters"):
                raise Exception("No evaluation parameters generated")
            
            # Ensure we have exactly 10 parameters
            params = evaluation_data["evaluation_parameters"][:10]  # Take first 10
            while len(params) < 10:
                # Add default parameters if needed
                params.append({
                    "parameter": f"Additional Criterion {len(params) + 1}",
                    "score": 5,
                    "max_score": 10,
                    "comment": "Standard evaluation criterion"
                })
            
            # Calculate final marks
            total_score = sum(param["score"] for param in params)
            final_marks = min(100, max(0, total_score))  # Ensure 0-100 range
            
            # Build evaluation parameters list
            eval_params = []
            for param in params:
                eval_params.append(EvaluationParameter(
                    parameter=param["parameter"],
                    score=max(0, min(10, param["score"])),  # Ensure 0-10 range
                    max_score=10,
                    comment=param.get("comment", "Standard evaluation")
                ))
            
            # Get cost from OpenRouter if we have generation_id
            if generation_id:
                cost_data = await get_openrouter_generation_cost(generation_id)
                if cost_data.get("success"):
                    cost_usd = cost_data.get("cost_usd", 0.0)
                    cost_npr = cost_data.get("cost_npr", 0.0)
            
            time_taken = time.time() - start_time
            
            logger.info(f"Synthesizer Agent: Success! Final marks: {final_marks}/100, ${cost_usd:.6f} USD (रू {cost_npr:.4f} NPR), {time_taken:.2f}s")
            
            return SynthesizerOutput(
                final_marks=final_marks,
                evaluation_parameters=eval_params,
                personalized_feedback=evaluation_data.get("personalized_feedback", "Evaluation completed"),
                strengths_summary=evaluation_data.get("strengths_summary", "Various strengths identified"),
                improvement_areas=evaluation_data.get("improvement_areas", "Areas for growth identified"),
                recommendations=evaluation_data.get("recommendations", ["Continue studying and practicing"]),
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
            logger.error(f"Synthesizer Agent: Error - {error_msg} (after {time_taken:.2f}s)")
            
            return SynthesizerOutput(
                final_marks=0,
                evaluation_parameters=[],
                personalized_feedback="",
                strengths_summary="",
                improvement_areas="",
                recommendations=[],
                status=AgentStatus.ERROR,
                error=error_msg,
                generation_id=generation_id,
                cost_usd=cost_usd,
                cost_npr=cost_npr,
                time_taken_seconds=time_taken
            )
    
    def _parse_evaluation_response(self, response_text: str) -> dict:
        """
        Parse the AI model response to extract evaluation data
        
        Args:
            response_text: Raw response from AI model
            
        Returns:
            Dictionary with evaluation components
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
                    # Fallback: create basic evaluation from text
                    return self._create_fallback_evaluation(response_text)
            
            # Parse JSON
            result = json.loads(json_str)
            
            # Validate and set defaults
            result.setdefault("final_marks", 50)
            result.setdefault("evaluation_parameters", self._create_default_parameters())
            result.setdefault("personalized_feedback", "Evaluation completed successfully")
            result.setdefault("strengths_summary", "Various strengths identified")
            result.setdefault("improvement_areas", "Areas for improvement noted")
            result.setdefault("recommendations", ["Continue studying and practicing"])
            
            # Ensure evaluation_parameters is properly formatted
            if not isinstance(result["evaluation_parameters"], list):
                result["evaluation_parameters"] = self._create_default_parameters()
            
            # Validate each parameter
            validated_params = []
            for param in result["evaluation_parameters"]:
                if isinstance(param, dict) and "parameter" in param and "score" in param:
                    validated_params.append({
                        "parameter": str(param["parameter"]),
                        "score": max(0, min(10, int(param.get("score", 5)))),
                        "max_score": 10,
                        "comment": str(param.get("comment", "Standard evaluation"))
                    })
            
            if validated_params:
                result["evaluation_parameters"] = validated_params[:10]  # Max 10 parameters
            else:
                result["evaluation_parameters"] = self._create_default_parameters()
            
            # Ensure recommendations is a list
            if not isinstance(result["recommendations"], list):
                result["recommendations"] = [str(result["recommendations"])] if result["recommendations"] else ["Continue practicing"]
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Synthesizer Agent: JSON parse error - {e}, creating fallback evaluation")
            return self._create_fallback_evaluation(response_text)
        except Exception as e:
            logger.error(f"Synthesizer Agent: Response parsing error - {e}")
            raise Exception(f"Failed to parse Synthesizer response: {str(e)}")
    
    def _create_default_parameters(self) -> List[Dict]:
        """Create default evaluation parameters"""
        return [
            {"parameter": "Content Accuracy", "score": 6, "max_score": 10, "comment": "Basic accuracy demonstrated"},
            {"parameter": "Completeness", "score": 5, "max_score": 10, "comment": "Partially complete response"},
            {"parameter": "Structure & Organization", "score": 6, "max_score": 10, "comment": "Adequate organization"},
            {"parameter": "Depth of Analysis", "score": 5, "max_score": 10, "comment": "Surface-level analysis"},
            {"parameter": "Examples & Evidence", "score": 4, "max_score": 10, "comment": "Limited examples provided"},
            {"parameter": "Relevance", "score": 7, "max_score": 10, "comment": "Generally relevant to question"},
            {"parameter": "Clarity of Expression", "score": 6, "max_score": 10, "comment": "Clear but could be improved"},
            {"parameter": "Understanding of Concepts", "score": 6, "max_score": 10, "comment": "Basic understanding shown"},
            {"parameter": "Critical Thinking", "score": 4, "max_score": 10, "comment": "Limited critical analysis"},
            {"parameter": "Overall Quality", "score": 5, "max_score": 10, "comment": "Average quality response"}
        ]
    
    def _create_fallback_evaluation(self, response_text: str) -> dict:
        """
        Create fallback evaluation from unstructured response
        
        Args:
            response_text: Unstructured response text
            
        Returns:
            Basic evaluation dictionary
        """
        # Estimate score based on response content
        score_indicators = {
            "excellent": 8, "good": 7, "adequate": 6, "fair": 5, 
            "poor": 3, "weak": 3, "strong": 7, "solid": 6
        }
        
        estimated_score = 5  # Default
        for indicator, score in score_indicators.items():
            if indicator in response_text.lower():
                estimated_score = score
                break
        
        # Create parameters with estimated scores
        params = self._create_default_parameters()
        for param in params:
            param["score"] = max(1, min(10, estimated_score + (-1 if "Limited" in param["comment"] else 0)))
        
        return {
            "final_marks": sum(p["score"] for p in params),
            "evaluation_parameters": params,
            "personalized_feedback": "Your response has been evaluated. Focus on improving depth and providing more specific examples.",
            "strengths_summary": "Basic understanding demonstrated",
            "improvement_areas": "Depth of analysis, specific examples, comprehensive coverage",
            "recommendations": [
                "Study the topic in more detail",
                "Practice writing comprehensive answers",
                "Include more specific examples and evidence"
            ]
        }


# Global synthesizer agent instance
synthesizer_agent = SynthesizerAgent()


# Main agent function for workflow integration
async def run_synthesizer_agent(
    question: str, 
    student_answer: str, 
    ideal_answer: str,
    pro_analysis: ProAgentOutput, 
    cons_analysis: ConsAgentOutput
) -> SynthesizerOutput:
    """
    Main function to run synthesizer agent
    
    Args:
        question: Original exam question
        student_answer: Student's response
        ideal_answer: Model answer
        pro_analysis: Pro agent's analysis
        cons_analysis: Cons agent's analysis
        
    Returns:
        SynthesizerOutput with final evaluation
    """
    return await synthesizer_agent.synthesize_evaluation(
        question, student_answer, ideal_answer, pro_analysis, cons_analysis
    )