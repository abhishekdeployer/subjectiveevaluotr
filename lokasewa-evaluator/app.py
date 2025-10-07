"""
Main Gradio Application - Lokasewa Aayog Subjective Answer Evaluator
"""

import os
import logging
import asyncio
from datetime import datetime
import gradio as gr
from config import Config
from utils.session_manager import create_user_session, cleanup_user_session
from utils.file_handler import file_handler
from workflow import run_evaluation_workflow

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LokasewaEvaluatorUI:
    """
    Main Gradio UI for the Lokasewa Evaluator system
    """
    
    def __init__(self):
        self.app = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the complete Gradio interface"""
        
        with gr.Blocks(
            theme=gr.themes.Soft(),
            title="Lokasewa Aayog Answer Evaluator",
            css=self._get_custom_css()
        ) as self.app:
            
            # Header
            gr.Markdown(
                """
                # 🎓 AI Answer Evaluator
                ### Professional Exam Answer Assessment Powered by Multi-Agent AI
                *Comprehensive evaluation for competitive examinations • Supports all subjects & languages*
                """
            )
            
            # Main input section
            question_input = gr.Textbox(
                label="📝 Exam Question",
                placeholder="Enter your exam question here (any language: Nepali, English, Hindi, etc.)",
                lines=4
            )
            
            file_input = gr.File(
                label="📄 Upload Answer (Image or PDF)",
                file_types=["image", ".pdf"]
            )
            
            evaluate_btn = gr.Button(
                "🚀 Start Evaluation", 
                variant="primary",
                size="lg"
            )
            
            gr.Markdown("---")
            
            # Progress section
            with gr.Row():
                gr.Markdown("## 📊 Evaluation Progress")
            
            # Stage indicators
            stage_1_status = gr.Markdown("⏳ **Stage 1:** Waiting to start...")
            stage_2_status = gr.Markdown("⏳ **Stage 2:** Waiting...")  
            stage_3_status = gr.Markdown("⏳ **Stage 3:** Waiting...")
            
            # Intermediate results
            with gr.Row(visible=False) as extracted_section:
                with gr.Column():
                    extracted_answer = gr.Textbox(
                        label="📖 Extracted Student Answer",
                        lines=8,
                        interactive=False
                    )
                    ocr_confidence = gr.Textbox(
                        label="🎯 OCR Confidence",
                        interactive=False
                    )
            
            with gr.Row(visible=False) as analysis_section:
                with gr.Column():
                    pro_analysis = gr.JSON(
                        label="👍 Pro Agent Analysis (Strengths)",
                        visible=False
                    )
                with gr.Column():
                    cons_analysis = gr.JSON(
                        label="👎 Cons Agent Analysis (Areas for Improvement)",
                        visible=False
                    )
            
            gr.Markdown("---")
            
            # Final results section
            with gr.Row():
                gr.Markdown("## 🎯 Final Evaluation Results")
            
            final_marks = gr.Markdown("### Final Marks: --/100", visible=False)
            
            # Results tabs
            with gr.Tabs(visible=False) as results_tabs:
                with gr.Tab("📊 Detailed Scores"):
                    evaluation_table = gr.Dataframe(
                        headers=["Parameter", "Score", "Max Score", "Comment"],
                        label="Evaluation Parameters",
                        interactive=False
                    )
                
                with gr.Tab("💬 Personalized Feedback"):
                    personalized_feedback = gr.Textbox(
                        label="Your Personalized Feedback",
                        lines=10,
                        interactive=False
                    )
                    
                    with gr.Row():
                        with gr.Column():
                            strengths_summary = gr.Textbox(
                                label="✅ Key Strengths",
                                lines=4,
                                interactive=False
                            )
                        with gr.Column():
                            improvement_areas = gr.Textbox(
                                label="🔄 Areas for Improvement",
                                lines=4,
                                interactive=False
                            )
                    
                    recommendations = gr.Textbox(
                        label="📚 Study Recommendations",
                        lines=5,
                        interactive=False
                    )
                
                with gr.Tab("🎓 Expert Answer"):
                    ideal_answer_display = gr.Textbox(
                        label="Model Answer (Expert Response)",
                        lines=12,
                        interactive=False
                    )
                
                with gr.Tab("💰 Cost & Time"):
                    gr.Markdown("""
                    ### API Cost Breakdown
                    *Exchange Rate: 1 USD = 142 NPR (as of October 3, 2025)*  
                    *Note: OCR cost not included (uses Google Gemini via AI Studio)*
                    """)
                    cost_table = gr.Dataframe(
                        headers=["Agent", "Cost (USD)", "Cost (NPR)", "Time"],
                        label="Cost & Time per Agent",
                        interactive=False
                    )
            
            # New evaluation button
            new_evaluation_btn = gr.Button(
                "📝 Evaluate Another Question",
                variant="secondary",
                visible=False
            )
            
            # Event handlers
            evaluate_btn.click(
                fn=self._evaluate_answer,
                inputs=[question_input, file_input],
                outputs=[
                    stage_1_status, stage_2_status, stage_3_status,
                    extracted_section, extracted_answer, ocr_confidence,
                    analysis_section, pro_analysis, cons_analysis,
                    final_marks, results_tabs, evaluation_table,
                    personalized_feedback, strengths_summary, improvement_areas,
                    recommendations, ideal_answer_display, cost_table, new_evaluation_btn
                ],
                show_progress=True
            )
            
            new_evaluation_btn.click(
                fn=self._reset_interface,
                outputs=[
                    question_input, file_input,
                    stage_1_status, stage_2_status, stage_3_status,
                    extracted_section, analysis_section, final_marks,
                    results_tabs, new_evaluation_btn
                ]
            )
    
    async def _evaluate_answer(self, question: str, uploaded_file):
        """
        Main evaluation function with progressive UI updates
        
        Args:
            question: User's question input
            uploaded_file: Gradio File object
            
        Yields:
            Progressive UI updates throughout evaluation
        """
        try:
            # Initial validation
            if not question or not question.strip():
                yield self._create_error_output("❌ Please enter a question (minimum 10 characters)")
                return
            
            if len(question.strip()) < 10:
                yield self._create_error_output("❌ Question too short. Please provide at least 10 characters.")
                return
            
            if not uploaded_file:
                yield self._create_error_output("❌ Please upload an answer file (image or PDF)")
                return
            
            # Read file
            try:
                if hasattr(uploaded_file, 'name'):
                    # Gradio file object
                    with open(uploaded_file.name, 'rb') as f:
                        file_data = f.read()
                else:
                    # Direct bytes
                    file_data = uploaded_file
                
                # Detect file type and validate
                file_type = file_handler.detect_file_type(file_data)
                file_handler.validate_file_size(file_data)
                
            except Exception as e:
                yield self._create_error_output(f"❌ File processing error: {str(e)}")
                return
            
            # Create session
            try:
                session_id = await create_user_session(question.strip(), file_data, file_type)
                logger.info(f"Created session {session_id} for evaluation")
            except Exception as e:
                yield self._create_error_output(f"❌ Session creation failed: {str(e)}")
                return
            
            # Stage 1 started
            yield (
                "⏳ **Stage 1:** OCR Processing + Ideal Answer Generation (Running in Parallel)...",
                "⏳ **Stage 2:** Waiting for Stage 1...",
                "⏳ **Stage 3:** Waiting...",
                gr.update(visible=False), gr.update(), gr.update(),  # extracted section
                gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),  # analysis
                gr.update(visible=False), gr.update(visible=False), gr.update(),  # results
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), [], gr.update(visible=False)
            )
            
            # Execute workflow with progress tracking
            workflow_result = await run_evaluation_workflow(
                session_id, question.strip(), file_data, file_type
            )
            
            # Check if workflow failed
            if not workflow_result.get("workflow_complete", False):
                error_msg = "; ".join(workflow_result.get("errors", ["Unknown workflow error"]))
                yield self._create_error_output(f"❌ Evaluation failed: {error_msg}")
                await cleanup_user_session(session_id)
                return
            
            # Stage 1 complete - show extracted text
            ocr_output = workflow_result.get("ocr_output", {})
            ideal_output = workflow_result.get("ideal_output", {})
            
            if ocr_output.get("status") == "success":
                extracted_text = ocr_output.get("student_answer", "")
                confidence = f"Confidence: {ocr_output.get('confidence_score', 0)*100:.1f}%"
                if ocr_output.get("pages_processed", 1) > 1:
                    confidence += f" ({ocr_output['pages_processed']} pages processed)"
            else:
                extracted_text = f"OCR Error: {ocr_output.get('error', 'Unknown error')}"
                confidence = "Confidence: 0%"
            
            yield (
                "✅ **Stage 1:** OCR + Ideal Answer Complete",
                "⏳ **Stage 2:** Pro & Cons Analysis (Running in Parallel)...",
                "⏳ **Stage 3:** Waiting for Stage 2...",
                gr.update(visible=True), extracted_text, confidence,
                gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), [], gr.update(visible=False)
            )
            
            # Wait a moment for visual feedback
            await asyncio.sleep(1)
            
            # Stage 2 complete - show pro/cons analysis
            pro_output = workflow_result.get("pro_output", {})
            cons_output = workflow_result.get("cons_output", {})
            
            yield (
                "✅ **Stage 1:** OCR + Ideal Answer Complete",
                "✅ **Stage 2:** Pro & Cons Analysis Complete",
                "⏳ **Stage 3:** Final Synthesis & Scoring...",
                gr.update(visible=True), extracted_text, confidence,
                gr.update(visible=True), 
                pro_output if pro_output.get("status") == "success" else {"error": pro_output.get("error")},
                cons_output if cons_output.get("status") == "success" else {"error": cons_output.get("error")},
                gr.update(visible=False), gr.update(visible=False), gr.update(),
                gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), [], gr.update(visible=False)
            )
            
            # Wait a moment for visual feedback
            await asyncio.sleep(1)
            
            # Final results
            synth_output = workflow_result.get("synthesizer_output", {})
            
            if synth_output.get("status") != "success":
                yield self._create_error_output(f"❌ Final evaluation failed: {synth_output.get('error', 'Unknown error')}")
                await cleanup_user_session(session_id)
                return
            
            # Format results for display
            final_marks_value = synth_output.get("final_marks", 0)
            eval_params = synth_output.get("evaluation_parameters", [])
            
            # Create evaluation table
            eval_table_data = [
                [param["parameter"], param["score"], param["max_score"], param["comment"]]
                for param in eval_params
            ]
            
            # Get individual agent costs and times
            ideal_cost_usd = ideal_output.get("cost_usd", 0.0)
            pro_cost_usd = pro_output.get("cost_usd", 0.0)
            cons_cost_usd = cons_output.get("cost_usd", 0.0)
            synth_cost_usd = synth_output.get("cost_usd", 0.0)
            
            ideal_time = ideal_output.get("time_taken_seconds", 0.0)
            pro_time = pro_output.get("time_taken_seconds", 0.0)
            cons_time = cons_output.get("time_taken_seconds", 0.0)
            synth_time = synth_output.get("time_taken_seconds", 0.0)
            
            # Calculate totals
            total_cost_usd = ideal_cost_usd + pro_cost_usd + cons_cost_usd + synth_cost_usd
            total_cost_npr = total_cost_usd * 142.0
            total_time = ideal_time + pro_time + cons_time + synth_time
            
            # Create cost breakdown table
            cost_table_data = [
                ["Ideal Answer", f"${ideal_cost_usd:.6f}", f"रू {ideal_cost_usd * 142:.4f}", f"{ideal_time:.2f}s"],
                ["Pro Agent", f"${pro_cost_usd:.6f}", f"रू {pro_cost_usd * 142:.4f}", f"{pro_time:.2f}s"],
                ["Cons Agent", f"${cons_cost_usd:.6f}", f"रू {cons_cost_usd * 142:.4f}", f"{cons_time:.2f}s"],
                ["Synthesizer", f"${synth_cost_usd:.6f}", f"रू {synth_cost_usd * 142:.4f}", f"{synth_time:.2f}s"],
                ["**TOTAL**", f"**${total_cost_usd:.6f}**", f"**रू {total_cost_npr:.4f}**", f"**{total_time:.2f}s**"],
            ]
            
            # Final complete output
            yield (
                "✅ **Stage 1:** OCR + Ideal Answer Complete",
                "✅ **Stage 2:** Pro & Cons Analysis Complete", 
                "✅ **Stage 3:** Final Evaluation Complete!",
                gr.update(visible=True), extracted_text, confidence,
                gr.update(visible=True), pro_output, cons_output,
                gr.update(value=f"### 🎯 Final Marks: {final_marks_value}/100", visible=True),
                gr.update(visible=True),
                eval_table_data,
                synth_output.get("personalized_feedback", ""),
                synth_output.get("strengths_summary", ""),
                synth_output.get("improvement_areas", ""),
                "\n".join([f"• {rec}" for rec in synth_output.get("recommendations", [])]),
                ideal_output.get("ideal_answer", ""),
                cost_table_data,
                gr.update(visible=True)
            )
            
            # Cleanup session
            await cleanup_user_session(session_id)
            logger.info(f"Evaluation completed for session {session_id}")
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"UI Evaluation error: {error_msg}")
            yield self._create_error_output(f"❌ {error_msg}")
    
    def _create_error_output(self, error_message: str):
        """Create standardized error output for UI"""
        return (
            error_message,  # stage_1_status
            "❌ **Stage 2:** Cancelled due to error",  # stage_2_status  
            "❌ **Stage 3:** Cancelled due to error",  # stage_3_status
            gr.update(visible=False), gr.update(), gr.update(),  # extracted section
            gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),  # analysis
            gr.update(visible=False), gr.update(visible=False), gr.update(),  # results
            gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), [], gr.update(visible=False)  # cost_table + new_eval_btn
        )
    
    def _reset_interface(self):
        """Reset interface for new evaluation"""
        return (
            gr.update(value=""),  # question_input
            gr.update(value=None),  # file_input
            "⏳ **Stage 1:** Waiting to start...",  # stage_1_status
            "⏳ **Stage 2:** Waiting...",  # stage_2_status
            "⏳ **Stage 3:** Waiting...",  # stage_3_status
            gr.update(visible=False),  # extracted_section
            gr.update(visible=False),  # analysis_section
            gr.update(visible=False),  # final_marks
            gr.update(visible=False),  # results_tabs
            gr.update(visible=False),  # new_evaluation_btn
        )
    
    def _get_custom_css(self):
        """Custom CSS for better UI styling"""
        return """
        /* Main Container */
        .gradio-container {
            max-width: 1400px !important;
            margin: auto;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        /* Header Styling */
        .gradio-container h1 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 2.5em;
            font-weight: 700;
            text-align: center;
            margin-bottom: 0.5em;
        }
        
        .gradio-container h3 {
            color: #4a5568;
            font-weight: 600;
        }
        
        /* Input Section */
        .gradio-container .input-section {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Buttons */
        .gradio-container button {
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .gradio-container button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        
        /* Progress indicators */
        .progress-bar {
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 10px;
        }
        
        /* Results Cards */
        .gradio-container .markdown-text {
            background: white;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* Tables */
        .gradio-container table {
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .gradio-container table th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            padding: 12px;
        }
        
        .gradio-container table td {
            padding: 10px;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .gradio-container table tr:hover {
            background-color: #f7fafc;
        }
        
        /* Tabs */
        .gradio-container .tabs {
            border-radius: 10px;
            overflow: hidden;
        }
        
        .gradio-container .tab-nav button {
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .gradio-container .tab-nav button.selected {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        /* Status messages */
        .gradio-container .status-message {
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
        }
        
        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .gradio-container .fade-in {
            animation: fadeIn 0.5s ease-out;
        }
        """
    
    def launch(self, **kwargs):
        """Launch the Gradio app"""
        
        # Validate configuration before launch
        try:
            Config.validate()
            logger.info("Configuration validated successfully")
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        
        # Default launch parameters with port auto-detection
        launch_params = {
            "server_name": "0.0.0.0",
            "server_port": None,  # Let Gradio find available port
            "share": False,
            "debug": Config.DEBUG_MODE,
            "show_error": True,
            "quiet": False
        }
        
        # Override with user parameters
        launch_params.update(kwargs)
        
        # If server_port is None, Gradio will find available port starting from 7860
        if launch_params['server_port'] is None:
            logger.info(f"Launching Lokasewa Evaluator UI on {launch_params['server_name']} (auto-detecting port from 7860...)")
        else:
            logger.info(f"Launching Lokasewa Evaluator UI on {launch_params['server_name']}:{launch_params['server_port']}")
        
        return self.app.launch(**launch_params)


def main():
    """Main function to run the application"""
    
    # Setup logging
    logger.info("Starting Lokasewa Aayog Answer Evaluator")
    
    # Create and launch UI
    ui = LokasewaEvaluatorUI()
    
    try:
        ui.launch(
            share=True,  # Create public link
            debug=Config.DEBUG_MODE
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except OSError as e:
        if "Cannot find empty port" in str(e) or "10048" in str(e):
            logger.error("Port already in use. Please close any running instances or use a different port.")
            logger.info("TIP: Set GRADIO_SERVER_PORT environment variable or pass server_port parameter")
            print("\n" + "="*60)
            print("❌ ERROR: Port already in use!")
            print("="*60)
            print("\n💡 SOLUTIONS:")
            print("1. Close any running instances of this app")
            print("2. Kill the process using the port:")
            print("   netstat -ano | findstr :7860")
            print("   taskkill /PID <process_id> /F")
            print("3. Use a different port:")
            print("   set GRADIO_SERVER_PORT=7861 && python app.py")
            print("="*60 + "\n")
        else:
            logger.error(f"Application error: {e}")
            raise
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise


if __name__ == "__main__":
    main()