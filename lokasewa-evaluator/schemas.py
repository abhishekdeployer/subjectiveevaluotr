"""
Data schemas and models for the Lokasewa Evaluator system
All structured data models using Pydantic for validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    """Supported file types"""
    IMAGE = "image"
    PDF = "pdf"


class AgentStatus(str, Enum):
    """Agent execution status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    ERROR = "error"


class Severity(str, Enum):
    """Issue severity levels"""
    MINOR = "minor"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"


# Agent Output Models

class OCROutput(BaseModel):
    """OCR Agent output structure"""
    student_answer: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    pages_processed: int = 1
    status: AgentStatus
    api_source: str  # "google_ai_studio" or "openrouter"
    error: Optional[str] = None


class IdealAnswerOutput(BaseModel):
    """Ideal Answer Generator output structure"""
    ideal_answer: str
    key_points: List[str]
    word_count: int
    status: AgentStatus
    error: Optional[str] = None
    generation_id: Optional[str] = None  # OpenRouter generation ID
    cost_usd: float = 0.0  # Cost in USD
    cost_npr: float = 0.0  # Cost in NPR
    time_taken_seconds: float = 0.0  # Time taken for this agent


class ProAgentOutput(BaseModel):
    """Pro Agent (Student Advocate) output structure"""
    strengths: List[str]
    positive_comparison: str
    encouragement: str
    coverage_percentage: float = Field(ge=0.0, le=100.0)
    status: AgentStatus
    error: Optional[str] = None
    generation_id: Optional[str] = None  # OpenRouter generation ID
    cost_usd: float = 0.0  # Cost in USD
    cost_npr: float = 0.0  # Cost in NPR
    time_taken_seconds: float = 0.0  # Time taken for this agent


class ConsAgentOutput(BaseModel):
    """Cons Agent (Constructive Critic) output structure"""
    gaps_identified: List[str]
    areas_for_improvement: List[str]
    constructive_feedback: str
    severity: Severity
    status: AgentStatus
    error: Optional[str] = None
    generation_id: Optional[str] = None  # OpenRouter generation ID
    cost_usd: float = 0.0  # Cost in USD
    cost_npr: float = 0.0  # Cost in NPR
    time_taken_seconds: float = 0.0  # Time taken for this agent


class EvaluationParameter(BaseModel):
    """Individual evaluation parameter"""
    parameter: str
    score: int = Field(ge=0, le=10)
    max_score: int = 10
    comment: str


class SynthesizerOutput(BaseModel):
    """Synthesizer Agent (Final Evaluator) output structure"""
    final_marks: int = Field(ge=0, le=100)
    evaluation_parameters: List[EvaluationParameter]
    personalized_feedback: str
    strengths_summary: str
    improvement_areas: str
    recommendations: List[str]
    status: AgentStatus
    error: Optional[str] = None
    generation_id: Optional[str] = None  # OpenRouter generation ID
    cost_usd: float = 0.0  # Cost in USD
    cost_npr: float = 0.0  # Cost in NPR
    time_taken_seconds: float = 0.0  # Time taken for this agent


# Main State Model

class EvaluationState(BaseModel):
    """
    Main state object that flows through the LangGraph workflow
    Contains all data from input through final output
    """
    
    # Input data
    session_id: str
    timestamp: datetime
    question: str
    answer_file: Union[str, bytes]
    file_type: FileType
    
    # OCR Stage
    ocr_output: Optional[OCROutput] = None
    student_answer: str = ""
    ocr_confidence: float = 0.0
    ocr_status: AgentStatus = AgentStatus.NOT_STARTED
    
    # Ideal Answer Stage
    ideal_answer_output: Optional[IdealAnswerOutput] = None
    ideal_answer: str = ""
    ideal_answer_status: AgentStatus = AgentStatus.NOT_STARTED
    
    # Pro Agent Stage
    pro_output: Optional[ProAgentOutput] = None
    pro_status: AgentStatus = AgentStatus.NOT_STARTED
    
    # Cons Agent Stage
    cons_output: Optional[ConsAgentOutput] = None
    cons_status: AgentStatus = AgentStatus.NOT_STARTED
    
    # Synthesizer Stage
    synthesizer_output: Optional[SynthesizerOutput] = None
    final_marks: int = 0
    synthesizer_status: AgentStatus = AgentStatus.NOT_STARTED
    
    # Error tracking
    errors: List[str] = []
    
    # Progress tracking
    current_stage: str = "not_started"
    
    # Cost tracking (OpenRouter only, excludes Google AI Studio OCR)
    total_cost_usd: float = 0.0  # Total cost in USD
    total_cost_npr: float = 0.0  # Total cost in NPR (USD * 142)
    total_time_seconds: float = 0.0  # Total time for all agents
    
    # Individual agent times
    ocr_time_seconds: float = 0.0
    ideal_answer_time_seconds: float = 0.0
    pro_agent_time_seconds: float = 0.0
    cons_agent_time_seconds: float = 0.0
    synthesizer_time_seconds: float = 0.0
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            bytes: lambda v: "<bytes_data>"
        }


# Session Management Models

class SessionInfo(BaseModel):
    """Session information for concurrent user handling"""
    session_id: str
    created_at: datetime
    question: str
    file_size_kb: float  # Changed from int to float to handle decimal file sizes
    file_type: FileType
    status: str = "active"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# API Response Models

class APIResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    api_source: Optional[str] = None


# UI Update Models

class UIProgressUpdate(BaseModel):
    """Progress update for Gradio UI"""
    stage: str
    status: AgentStatus
    message: str
    data: Optional[Dict[str, Any]] = None


class UIFinalResults(BaseModel):
    """Final results for UI display"""
    final_marks: int
    evaluation_table: List[List[str]]  # For Gradio DataFrame
    personalized_feedback: str
    ideal_answer: str
    strengths_summary: str
    improvement_areas: str
    recommendations: List[str]
    # Cost tracking
    total_cost_usd: float = 0.0
    total_cost_npr: float = 0.0
    total_time_seconds: float = 0.0
    cost_breakdown: List[List[str]] = []  # For cost table display


# Validation Models

class QuestionValidation(BaseModel):
    """Question input validation"""
    question: str = Field(min_length=10, max_length=5000)
    
    @classmethod
    def validate_question(cls, question: str) -> bool:
        """Validate question input"""
        try:
            cls(question=question)
            return True
        except:
            return False


class FileValidation(BaseModel):
    """File input validation"""
    file_size_bytes: int = Field(gt=0, le=10*1024*1024)  # Max 10MB
    file_type: FileType
    
    @classmethod
    def validate_file(cls, file_size: int, file_type: str) -> bool:
        """Validate file input"""
        try:
            cls(file_size_bytes=file_size, file_type=FileType(file_type))
            return True
        except:
            return False


# Helper functions

def create_evaluation_state(session_id: str, question: str, file_data: Union[str, bytes], file_type: str) -> EvaluationState:
    """Create a new evaluation state object"""
    return EvaluationState(
        session_id=session_id,
        timestamp=datetime.now(),
        question=question,
        answer_file=file_data,
        file_type=FileType(file_type)
    )


def format_for_ui(state: EvaluationState) -> UIFinalResults:
    """Format evaluation state for UI display"""
    if not state.synthesizer_output:
        raise ValueError("Evaluation not complete")
    
    synth = state.synthesizer_output
    
    # Format evaluation parameters for Gradio table
    eval_table = [
        [param.parameter, str(param.score), str(param.max_score), param.comment]
        for param in synth.evaluation_parameters
    ]
    
    # Build cost breakdown table
    cost_breakdown = []
    if state.ideal_answer_output:
        cost_breakdown.append([
            "Ideal Answer",
            f"${state.ideal_answer_output.cost_usd:.6f}",
            f"रू {state.ideal_answer_output.cost_npr:.4f}",
            f"{state.ideal_answer_time_seconds:.2f}s"
        ])
    
    if state.pro_output:
        cost_breakdown.append([
            "Pro Agent",
            f"${state.pro_output.cost_usd:.6f}",
            f"रू {state.pro_output.cost_npr:.4f}",
            f"{state.pro_agent_time_seconds:.2f}s"
        ])
    
    if state.cons_output:
        cost_breakdown.append([
            "Cons Agent",
            f"${state.cons_output.cost_usd:.6f}",
            f"रू {state.cons_output.cost_npr:.4f}",
            f"{state.cons_agent_time_seconds:.2f}s"
        ])
    
    if synth:
        cost_breakdown.append([
            "Synthesizer",
            f"${synth.cost_usd:.6f}",
            f"रू {synth.cost_npr:.4f}",
            f"{state.synthesizer_time_seconds:.2f}s"
        ])
    
    # Add total row
    cost_breakdown.append([
        "**TOTAL**",
        f"**${state.total_cost_usd:.6f}**",
        f"**रू {state.total_cost_npr:.4f}**",
        f"**{state.total_time_seconds:.2f}s**"
    ])
    
    return UIFinalResults(
        final_marks=synth.final_marks,
        evaluation_table=eval_table,
        personalized_feedback=synth.personalized_feedback,
        ideal_answer=state.ideal_answer,
        strengths_summary=synth.strengths_summary,
        improvement_areas=synth.improvement_areas,
        recommendations=synth.recommendations,
        total_cost_usd=state.total_cost_usd,
        total_cost_npr=state.total_cost_npr,
        total_time_seconds=state.total_time_seconds,
        cost_breakdown=cost_breakdown
    )