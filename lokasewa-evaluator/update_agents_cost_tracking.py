"""
Script to update all remaining agents (Pro, Cons, Synthesizer) with cost and time tracking
Run this to add cost tracking to all agents
"""

import re

# Files to update
FILES_TO_UPDATE = [
    "agents/pro_agent.py",
    "agents/cons_agent.py",
    "agents/synthesizer_agent.py"
]

# Import additions for each file
IMPORT_ADDITIONS = """import time
from utils.api_client import get_openrouter_generation_cost, extract_generation_id
from config import Config"""

def update_file(filepath):
    """Add cost tracking to agent file"""
    print(f"\n📝 Updating {filepath}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add imports if not already present
        if "get_openrouter_generation_cost" not in content:
            # Find the import section
            import_pattern = r'(from utils\.api_client import [^\n]+)'
            if re.search(import_pattern, content):
                content = re.sub(
                    import_pattern,
                    lambda m: m.group(1) + ', get_openrouter_generation_cost, extract_generation_id',
                    content,
                    count=1
                )
            
            # Add time and Config imports
            if "import time" not in content:
                content = re.sub(
                    r'(import logging)',
                    r'\1\nimport time',
                    content,
                    count=1
                )
            
            if "from config import Config" not in content:
                content = re.sub(
                    r'(from schemas import )',
                    r'from config import Config\n\1',
                    content,
                    count=1
                )
        
        # Add timing and cost tracking variables at the start of main method
        # Pattern: try:\n            logger.info
        timing_init = """        start_time = time.time()
        generation_id = None
        cost_usd = 0.0
        cost_npr = 0.0
        
        try:"""
        
        content = re.sub(
            r'        try:\n            logger\.info',
            timing_init + '\n            logger.info',
            content,
            count=1
        )
        
        # Add cost tracking after API response (look for response.data.get)
        cost_tracking_code = """
            # Extract generation ID for cost tracking
            raw_response = response.data.get("raw_response")
            if raw_response:
                generation_id = extract_generation_id(raw_response)
            """
        
        # Insert after "response = await call_" line
        content = re.sub(
            r'(response = await call_\w+_model\([^)]+\)\s+if not response\.success:)',
            r'\1\n' + cost_tracking_code,
            content,
            count=1
        )
        
        # Add cost fetching before final logger.info("Success!")
        cost_fetch_code = """
            # Get cost from OpenRouter if we have generation_id
            if generation_id:
                cost_data = await get_openrouter_generation_cost(generation_id)
                if cost_data.get("success"):
                    cost_usd = cost_data.get("cost_usd", 0.0)
                    cost_npr = cost_data.get("cost_npr", 0.0)
            
            time_taken = time.time() - start_time
            """
        
        # Insert before logger.info success message
        content = re.sub(
            r'(\s+)(logger\.info\(f["\'][^"\']*Success![^"\']*["\'])',
            r'\1' + cost_fetch_code + r'\n\1\2',
            content,
            count=1
        )
        
        # Update success logger to include cost/time
        content = re.sub(
            r'logger\.info\(f"([^:]+): Success!([^"]+)"\)',
            r'logger.info(f"\1: Success!\2, ${cost_usd:.6f} USD (रू {cost_npr:.4f} NPR), {time_taken:.2f}s")',
            content,
            count=1
        )
        
        # Add cost fields to success return statement
        content = re.sub(
            r'(status=AgentStatus\.SUCCESS,\s+error=None)',
            r'\1,\n                generation_id=generation_id,\n                cost_usd=cost_usd,\n                cost_npr=cost_npr,\n                time_taken_seconds=time_taken',
            content,
            count=1
        )
        
        # Update error except block to include time
        content = re.sub(
            r'(except Exception as e:)\s+(error_msg = str\(e\))',
            r'\1\n            time_taken = time.time() - start_time\n            \2',
            content,
            count=1
        )
        
        # Update error logger
        content = re.sub(
            r'logger\.error\(f"([^:]+): Error - {error_msg}"\)',
            r'logger.error(f"\1: Error - {error_msg} (after {time_taken:.2f}s)")',
            content,
            count=1
        )
        
        # Add cost fields to error return
        content = re.sub(
            r'(status=AgentStatus\.ERROR,\s+error=error_msg)(\s+\))',
            r'\1,\n                generation_id=generation_id,\n                cost_usd=cost_usd,\n                cost_npr=cost_npr,\n                time_taken_seconds=time_taken\2',
            content,
            count=1
        )
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Updated {filepath}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating {filepath}: {e}")
        return False


if __name__ == "__main__":
    print("🔧 Adding cost and time tracking to agents...")
    print("=" * 60)
    
    success_count = 0
    for filepath in FILES_TO_UPDATE:
        if update_file(filepath):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"✨ Updated {success_count}/{len(FILES_TO_UPDATE)} files successfully!")
    print("\n💡 Next: Run the app and see cost tracking in action!")
