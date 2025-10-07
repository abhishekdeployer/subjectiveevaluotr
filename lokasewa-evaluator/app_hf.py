import os
from app import LokasewaEvaluatorUI

# Hugging Face Spaces entry point
if __name__ == "__main__":
    ui = LokasewaEvaluatorUI()
    
    # Launch with Hugging Face-friendly settings
    ui.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,  # Hugging Face provides the public URL
        show_error=True,
        debug=False
    )
