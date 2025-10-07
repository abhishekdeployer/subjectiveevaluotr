"""
LangGraph Workflow - Properly orchestrates all agents using LangGraph state management
"""

import logging
from typing import Dict, Any, TypedDict, Annotated
from datetime import datetime
from operator import add
from langgraph.graph import StateGraph, START, END
from schemas import (
    AgentStatus, FileType,
    create_evaluation_state
)
from agents.ocr_agent import run_ocr_agent
from agents.ideal_answer_agent import run_ideal_answer_agent
from agents.pro_agent import run_pro_agent
from agents.cons_agent import run_cons_agent
from agents.synthesizer_agent import run_synthesizer_agent

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """
    LangGraph state with proper type annotations and reducers
    """
    # Core evaluation data
    session_id: str
    question: str
    student_answer: str
    ideal_answer: str
    
    # Agent outputs (dicts for JSON serialization)
    ocr_output: Dict[str, Any]
    ideal_output: Dict[str, Any]
    pro_output: Dict[str, Any]
    cons_output: Dict[str, Any]
    synthesizer_output: Dict[str, Any]
    
    # Progress tracking
    stage_1_complete: bool
    stage_2_complete: bool
    workflow_complete: bool
    
    # File data
    file_data: bytes
    file_type: str
    
    # Error handling - use reducer to combine errors from parallel nodes
    errors: Annotated[list, add]
    failed_agents: Annotated[list, add]

class EvaluationWorkflow:
    """
    Main workflow orchestrator using LangGraph properly with ainvoke
    """
    
    def __init__(self):
        self.graph = self._build_workflow_graph()
    
    def _build_workflow_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow with proper parallel execution and state management
        
        Returns:
            Compiled StateGraph ready for execution
        """
        # Create state graph with proper typing
        workflow = StateGraph(WorkflowState)
        
        # Add all node functions
        workflow.add_node("ocr", self._ocr_node)
        workflow.add_node("ideal_answer", self._ideal_answer_node)
        workflow.add_node("pro_agent", self._pro_agent_node)
        workflow.add_node("cons_agent", self._cons_agent_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        
        # Entry point - START fans out to both OCR and ideal answer (parallel)
        workflow.add_edge(START, "ocr")
        workflow.add_edge(START, "ideal_answer")
        
        # After OCR and ideal complete, fan out to pro and cons (parallel)
        workflow.add_edge("ocr", "pro_agent")
        workflow.add_edge("ocr", "cons_agent")
        workflow.add_edge("ideal_answer", "pro_agent")
        workflow.add_edge("ideal_answer", "cons_agent")
        
        # After pro and cons complete, go to synthesizer
        workflow.add_edge("pro_agent", "synthesizer")
        workflow.add_edge("cons_agent", "synthesizer")
        
        # End workflow
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()
    
    async def _ocr_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        OCR Agent Node - Extract text from images/PDFs
        Returns partial state update
        """
        try:
            logger.info(f"Session {state['session_id']}: OCR Agent starting...")
            
            # Run OCR agent
            ocr_result = await run_ocr_agent(state["file_data"], state["file_type"])
            
            # Return state updates (LangGraph merges this with existing state)
            updates = {
                "ocr_output": {
                    "student_answer": ocr_result.student_answer,
                    "confidence_score": ocr_result.confidence_score,
                    "status": ocr_result.status.value,
                    "api_source": ocr_result.api_source,
                    "pages_processed": ocr_result.pages_processed,
                    "error": ocr_result.error
                },
                "errors": [],
                "failed_agents": []
            }
            
            if ocr_result.status == AgentStatus.SUCCESS:
                updates["student_answer"] = ocr_result.student_answer
                logger.info(f"Session {state['session_id']}: OCR Agent completed successfully")
            else:
                updates["errors"] = [f"OCR failed: {ocr_result.error}"]
                updates["failed_agents"] = ["ocr"]
                logger.error(f"Session {state['session_id']}: OCR Agent failed - {ocr_result.error}")
            
            return updates
            
        except Exception as e:
            error_msg = f"OCR node error: {str(e)}"
            logger.error(f"Session {state['session_id']}: {error_msg}")
            return {
                "errors": [error_msg],
                "failed_agents": ["ocr"],
                "ocr_output": {"status": "error", "error": error_msg}
            }
    
    async def _ideal_answer_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Ideal Answer Generator Node
        Returns partial state update
        """
        try:
            logger.info(f"Session {state['session_id']}: Ideal Answer Agent starting...")
            
            # Run ideal answer agent
            ideal_result = await run_ideal_answer_agent(state["question"])
            
            # Return state updates
            updates = {
                "ideal_output": {
                    "ideal_answer": ideal_result.ideal_answer,
                    "key_points": ideal_result.key_points,
                    "word_count": ideal_result.word_count,
                    "status": ideal_result.status.value,
                    "error": ideal_result.error,
                    "cost_usd": ideal_result.cost_usd,
                    "cost_npr": ideal_result.cost_npr,
                    "time_taken_seconds": ideal_result.time_taken_seconds
                },
                "errors": [],
                "failed_agents": []
            }
            
            if ideal_result.status == AgentStatus.SUCCESS:
                updates["ideal_answer"] = ideal_result.ideal_answer
                # Track costs
                updates["total_cost_usd"] = state.get("total_cost_usd", 0.0) + ideal_result.cost_usd
                updates["total_cost_npr"] = state.get("total_cost_npr", 0.0) + ideal_result.cost_npr
                updates["ideal_answer_time_seconds"] = ideal_result.time_taken_seconds
                updates["total_time_seconds"] = state.get("total_time_seconds", 0.0) + ideal_result.time_taken_seconds
                logger.info(f"Session {state['session_id']}: Ideal Answer Agent completed successfully")
            else:
                updates["errors"] = [f"Ideal Answer failed: {ideal_result.error}"]
                updates["failed_agents"] = ["ideal_answer"]
                logger.error(f"Session {state['session_id']}: Ideal Answer Agent failed - {ideal_result.error}")
            
            return updates
            
        except Exception as e:
            error_msg = f"Ideal Answer node error: {str(e)}"
            logger.error(f"Session {state['session_id']}: {error_msg}")
            return {
                "errors": [error_msg],
                "failed_agents": ["ideal_answer"],
                "ideal_output": {"status": "error", "error": error_msg}
            }
    
    async def _pro_agent_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Pro Agent Node - Find strengths
        Returns partial state update
        """
        try:
            logger.info(f"Session {state['session_id']}: Pro Agent starting...")
            
            # Check prerequisites
            student_answer = state.get("student_answer", "").strip()
            ideal_answer = state.get("ideal_answer", "").strip()
            
            if not student_answer or not ideal_answer:
                raise Exception(f"Missing prerequisites - student_answer: {len(student_answer)} chars, ideal_answer: {len(ideal_answer)} chars")
            
            # Run pro agent
            pro_result = await run_pro_agent(
                state["question"], 
                state["student_answer"], 
                state["ideal_answer"]
            )
            
            # Return state updates
            updates = {
                "pro_output": {
                    "strengths": pro_result.strengths,
                    "positive_comparison": pro_result.positive_comparison,
                    "encouragement": pro_result.encouragement,
                    "coverage_percentage": pro_result.coverage_percentage,
                    "status": pro_result.status.value,
                    "error": pro_result.error,
                    "cost_usd": pro_result.cost_usd,
                    "cost_npr": pro_result.cost_npr,
                    "time_taken_seconds": pro_result.time_taken_seconds
                },
                "errors": [],
                "failed_agents": []
            }
            
            if pro_result.status == AgentStatus.SUCCESS:
                # Track costs
                updates["total_cost_usd"] = state.get("total_cost_usd", 0.0) + pro_result.cost_usd
                updates["total_cost_npr"] = state.get("total_cost_npr", 0.0) + pro_result.cost_npr
                updates["pro_agent_time_seconds"] = pro_result.time_taken_seconds
                updates["total_time_seconds"] = state.get("total_time_seconds", 0.0) + pro_result.time_taken_seconds
                logger.info(f"Session {state['session_id']}: Pro Agent completed successfully")
            else:
                updates["errors"] = [f"Pro Agent failed: {pro_result.error}"]
                updates["failed_agents"] = ["pro_agent"]
                logger.error(f"Session {state['session_id']}: Pro Agent failed - {pro_result.error}")
            
            return updates
            
        except Exception as e:
            error_msg = f"Pro Agent node error: {str(e)}"
            logger.error(f"Session {state['session_id']}: {error_msg}")
            return {
                "errors": [error_msg],
                "failed_agents": ["pro_agent"],
                "pro_output": {"status": "error", "error": error_msg}
            }
    
    async def _cons_agent_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Cons Agent Node - Find gaps and improvements
        Returns partial state update
        """
        try:
            logger.info(f"Session {state['session_id']}: Cons Agent starting...")
            
            # Check prerequisites
            student_answer = state.get("student_answer", "").strip()
            ideal_answer = state.get("ideal_answer", "").strip()
            
            if not student_answer or not ideal_answer:
                raise Exception(f"Missing prerequisites - student_answer: {len(student_answer)} chars, ideal_answer: {len(ideal_answer)} chars")
            
            # Run cons agent
            cons_result = await run_cons_agent(
                state["question"], 
                state["student_answer"], 
                state["ideal_answer"]
            )
            
            # Return state updates
            updates = {
                "cons_output": {
                    "gaps_identified": cons_result.gaps_identified,
                    "areas_for_improvement": cons_result.areas_for_improvement,
                    "constructive_feedback": cons_result.constructive_feedback,
                    "severity": cons_result.severity.value,
                    "status": cons_result.status.value,
                    "error": cons_result.error,
                    "cost_usd": cons_result.cost_usd,
                    "cost_npr": cons_result.cost_npr,
                    "time_taken_seconds": cons_result.time_taken_seconds
                },
                "errors": [],
                "failed_agents": []
            }
            
            if cons_result.status == AgentStatus.SUCCESS:
                # Track costs
                updates["total_cost_usd"] = state.get("total_cost_usd", 0.0) + cons_result.cost_usd
                updates["total_cost_npr"] = state.get("total_cost_npr", 0.0) + cons_result.cost_npr
                updates["cons_agent_time_seconds"] = cons_result.time_taken_seconds
                updates["total_time_seconds"] = state.get("total_time_seconds", 0.0) + cons_result.time_taken_seconds
                logger.info(f"Session {state['session_id']}: Cons Agent completed successfully")
            else:
                updates["errors"] = [f"Cons Agent failed: {cons_result.error}"]
                updates["failed_agents"] = ["cons_agent"]
                logger.error(f"Session {state['session_id']}: Cons Agent failed - {cons_result.error}")
            
            return updates
            
        except Exception as e:
            error_msg = f"Cons Agent node error: {str(e)}"
            logger.error(f"Session {state['session_id']}: {error_msg}")
            return {
                "errors": [error_msg],
                "failed_agents": ["cons_agent"],
                "cons_output": {"status": "error", "error": error_msg}
            }
    
    async def _synthesizer_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Synthesizer Node - Final evaluation
        Returns partial state update
        """
        try:
            logger.info(f"Session {state['session_id']}: Synthesizer Agent starting...")
            
            # Check prerequisites
            student_answer = state.get("student_answer", "").strip()
            ideal_answer = state.get("ideal_answer", "").strip()
            pro_success = state.get("pro_output", {}).get("status") == "success"
            cons_success = state.get("cons_output", {}).get("status") == "success"
            
            if not all([student_answer, ideal_answer, pro_success, cons_success]):
                missing = []
                if not student_answer:
                    missing.append("student_answer")
                if not ideal_answer:
                    missing.append("ideal_answer")
                if not pro_success:
                    missing.append("pro_agent")
                if not cons_success:
                    missing.append("cons_agent")
                raise Exception(f"Missing prerequisites: {', '.join(missing)}")
            
            # Convert outputs back to proper objects
            from schemas import ProAgentOutput, ConsAgentOutput, Severity
            
            pro_analysis = ProAgentOutput(
                strengths=state["pro_output"]["strengths"],
                positive_comparison=state["pro_output"]["positive_comparison"],
                encouragement=state["pro_output"]["encouragement"],
                coverage_percentage=state["pro_output"]["coverage_percentage"],
                status=AgentStatus.SUCCESS
            )
            
            cons_analysis = ConsAgentOutput(
                gaps_identified=state["cons_output"]["gaps_identified"],
                areas_for_improvement=state["cons_output"]["areas_for_improvement"],
                constructive_feedback=state["cons_output"]["constructive_feedback"],
                severity=Severity(state["cons_output"]["severity"]),
                status=AgentStatus.SUCCESS
            )
            
            # Run synthesizer agent
            synth_result = await run_synthesizer_agent(
                state["question"],
                state["student_answer"], 
                state["ideal_answer"],
                pro_analysis,
                cons_analysis
            )
            
            # Return state updates
            updates = {
                "synthesizer_output": {
                    "final_marks": synth_result.final_marks,
                    "evaluation_parameters": [
                        {
                            "parameter": param.parameter,
                            "score": param.score,
                            "max_score": param.max_score,
                            "comment": param.comment
                        } for param in synth_result.evaluation_parameters
                    ],
                    "personalized_feedback": synth_result.personalized_feedback,
                    "strengths_summary": synth_result.strengths_summary,
                    "improvement_areas": synth_result.improvement_areas,
                    "recommendations": synth_result.recommendations,
                    "status": synth_result.status.value,
                    "error": synth_result.error,
                    "cost_usd": synth_result.cost_usd,
                    "cost_npr": synth_result.cost_npr,
                    "time_taken_seconds": synth_result.time_taken_seconds
                },
                "workflow_complete": synth_result.status == AgentStatus.SUCCESS,
                "errors": [],
                "failed_agents": []
            }
            
            if synth_result.status == AgentStatus.SUCCESS:
                # Track costs
                updates["total_cost_usd"] = state.get("total_cost_usd", 0.0) + synth_result.cost_usd
                updates["total_cost_npr"] = state.get("total_cost_npr", 0.0) + synth_result.cost_npr
                updates["synthesizer_time_seconds"] = synth_result.time_taken_seconds
                updates["total_time_seconds"] = state.get("total_time_seconds", 0.0) + synth_result.time_taken_seconds
                logger.info(f"Session {state['session_id']}: Synthesizer completed - Final marks: {synth_result.final_marks}/100")
            else:
                updates["errors"] = [f"Synthesizer failed: {synth_result.error}"]
                updates["failed_agents"] = ["synthesizer"]
                logger.error(f"Session {state['session_id']}: Synthesizer failed - {synth_result.error}")
            
            return updates
            
        except Exception as e:
            error_msg = f"Synthesizer node error: {str(e)}"
            logger.error(f"Session {state['session_id']}: {error_msg}")
            return {
                "errors": [error_msg],
                "failed_agents": ["synthesizer"],
                "synthesizer_output": {"status": "error", "error": error_msg, "final_marks": 0},
                "workflow_complete": False
            }
    
    async def execute_evaluation(
        self, 
        session_id: str, 
        question: str, 
        file_data: bytes, 
        file_type: str
    ) -> Dict[str, Any]:
        """
        Execute complete evaluation workflow using LangGraph's ainvoke
        
        Args:
            session_id: Unique session identifier
            question: Exam question
            file_data: Answer file content
            file_type: "image" or "pdf"
            
        Returns:
            Complete evaluation results
        """
        try:
            logger.info(f"Session {session_id}: Starting LangGraph evaluation workflow")
            
            # Initialize workflow state
            initial_state = {
                "session_id": session_id,
                "question": question,
                "file_data": file_data,
                "file_type": file_type,
                "student_answer": "",
                "ideal_answer": "",
                "ocr_output": {},
                "ideal_output": {},
                "pro_output": {},
                "cons_output": {},
                "synthesizer_output": {},
                "stage_1_complete": False,
                "stage_2_complete": False,
                "workflow_complete": False,
                "errors": [],
                "failed_agents": []
            }
            
            # Execute workflow using LangGraph's ainvoke - this handles all parallelization!
            logger.info(f"Session {session_id}: Invoking LangGraph workflow...")
            final_state = await self.graph.ainvoke(initial_state)
            
            logger.info(f"Session {session_id}: Workflow complete!")
            
            return final_state
            
        except Exception as e:
            error_msg = f"Workflow execution error: {str(e)}"
            logger.error(f"Session {session_id}: {error_msg}")
            
            return {
                "session_id": session_id,
                "workflow_complete": False,
                "errors": [error_msg],
                "failed_agents": ["workflow"],
                "synthesizer_output": {
                    "status": "error",
                    "error": error_msg,
                    "final_marks": 0
                }
            }


# Global workflow instance
evaluation_workflow = EvaluationWorkflow()


# Main workflow execution function
async def run_evaluation_workflow(
    session_id: str, 
    question: str, 
    file_data: bytes, 
    file_type: str
) -> Dict[str, Any]:
    """
    Main function to execute the evaluation workflow
    
    Args:
        session_id: Unique session identifier
        question: Exam question
        file_data: Answer file content as bytes
        file_type: "image" or "pdf"
        
    Returns:
        Complete evaluation results dictionary
    """
    return await evaluation_workflow.execute_evaluation(session_id, question, file_data, file_type)
