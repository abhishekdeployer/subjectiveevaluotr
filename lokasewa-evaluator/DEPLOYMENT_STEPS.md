# 🚀 DEPLOYMENT GUIDE: Get Your Permanent Link!

## 🎯 Goal
Deploy your AI Answer Evaluator to Hugging Face Spaces and get a **permanent public link** that anyone can use **for FREE**!

---

## 📋 Prerequisites

Before starting, you need:
1. ✅ GitHub account (create at github.com if you don't have)
2. ✅ Hugging Face account (create at huggingface.co - it's FREE)
3. ✅ Your OpenRouter API key
4. ✅ Your Google AI Studio API key

---

## 🔄 PART 1: Upload to GitHub

### Step 1.1: Initialize Git Repository (If not already done)

Open PowerShell in your project folder:

```powershell
cd "c:\Users\abhis\realtime voice ai\lokasewa-evaluator"

# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: AI Answer Evaluator"
```

### Step 1.2: Create GitHub Repository

1. Go to **https://github.com/new**
2. **Repository name**: `lokasewa-evaluator` (or any name you like)
3. **Description**: "AI-powered exam answer evaluator with multi-agent system"
4. **Privacy**: Choose **Public** (required for free Hugging Face Spaces)
5. **DO NOT** initialize with README (you already have one)
6. Click **"Create repository"**

### Step 1.3: Push to GitHub

Copy the commands from GitHub (they'll look like this):

```powershell
# Add GitHub as remote
git remote add origin https://github.com/YOUR_USERNAME/lokasewa-evaluator.git

# Push to GitHub
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

**✅ Done! Your code is now on GitHub!**

---

## 🤗 PART 2: Deploy to Hugging Face Spaces (FREE & PERMANENT)

### Step 2.1: Create Hugging Face Space

1. Go to **https://huggingface.co/spaces**
2. Click **"Create new Space"**
3. Fill in details:
   - **Space name**: `lokasewa-evaluator` (or your choice)
   - **License**: `mit` (or your preference)
   - **Select SDK**: Choose **Gradio** ⚠️ **IMPORTANT!**
   - **Space hardware**: Choose **CPU basic (free)** ✓
   - **Visibility**: **Public** (for free tier)
4. Click **"Create Space"**

### Step 2.2: Configure Space Settings

#### Option A: Link GitHub Repository (Recommended - Auto-updates)

1. In your Space, click **"Settings"** tab
2. Scroll to **"Repository"** section
3. Click **"Link to GitHub"**
4. Authorize Hugging Face to access your GitHub
5. Select your repository: `YOUR_USERNAME/lokasewa-evaluator`
6. Enable **"Automatic sync"** (Space will auto-update when you push to GitHub)
7. Click **"Link"**

#### Option B: Upload Files Directly

1. In your Space, click **"Files"** tab
2. Click **"Add file" → "Upload files"**
3. Upload ALL files from your project folder:
   ```
   ✓ app.py
   ✓ config.py
   ✓ models.py
   ✓ schemas.py
   ✓ workflow.py
   ✓ requirements.txt
   ✓ README.md
   ✓ agents/ folder (all files)
   ✓ utils/ folder (all files)
   ```
4. **DO NOT upload**:
   - `.env` file (has your API keys!)
   - `__pycache__/` folders
   - `.md` documentation files (optional)

### Step 2.3: Add API Keys (CRITICAL!)

⚠️ **NEVER put API keys in your code or commit them to GitHub!**

1. In your Space, click **"Settings"** tab
2. Scroll to **"Repository secrets"** section
3. Click **"New secret"**
4. Add first secret:
   - **Name**: `OPENROUTER_API_KEY`
   - **Value**: Your OpenRouter API key
   - Click "Add"
5. Add second secret:
   - **Name**: `GOOGLE_API_KEY`
   - **Value**: Your Google AI Studio API key
   - Click "Add"

### Step 2.4: Create/Update app.py for Hugging Face

Make sure your `app.py` has this at the bottom:

```python
if __name__ == "__main__":
    ui = LokasewaEvaluatorUI()
    ui.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # Hugging Face provides public URL
    )
```

*(This is already correct in your current app.py)*

### Step 2.5: Wait for Build

1. Go to **"App"** tab in your Space
2. You'll see build logs (installing dependencies)
3. Wait 2-5 minutes for first build
4. Once done, you'll see: **"Running"** with a green indicator

**🎉 DONE! Your app is now live!**

---

## 🔗 Your Permanent Link

Your app will be available at:
```
https://huggingface.co/spaces/YOUR_USERNAME/lokasewa-evaluator
```

**This link is:**
- ✅ **Permanent** (stays online 24/7)
- ✅ **Free** (no credit card needed)
- ✅ **Fast** (Hugging Face infrastructure)
- ✅ **Shareable** (anyone can use it)

---

## 🎨 Customize Your Space

### Add a Nice Cover Image

1. Create a nice banner image (1200x630 px recommended)
2. In Space settings, upload as **"Space thumbnail"**

### Update Space Description

In your Space settings, add:
```markdown
# 🎓 AI Answer Evaluator

Professional exam answer assessment powered by multi-agent AI.

**Features:**
- Supports all subjects (law, business, math, science, etc.)
- Multi-language (Nepali, English, Hindi, etc.)
- Strict evaluation (realistic marks)
- Comprehensive feedback

**How to use:**
1. Enter your exam question
2. Upload answer (image/PDF)
3. Click "Start Evaluation"
4. Get detailed feedback in 30-60 seconds!

**Tech Stack:** Python, Gradio, LangGraph, OpenRouter AI
```

---

## 📊 Monitor Usage

### Check Your Space Stats

1. Go to your Space page
2. You'll see:
   - Number of views
   - Active users
   - API errors (if any)

### Check API Costs

1. Go to OpenRouter dashboard: https://openrouter.ai/activity
2. Monitor your spending
3. Set spending limits if needed

---

## 🔧 Update Your App

### If Using GitHub Sync (Recommended):

```powershell
# Make changes to your code locally
# Then:
git add .
git commit -m "Updated feature X"
git push

# Hugging Face Space will auto-update in 1-2 minutes!
```

### If Uploading Files Manually:

1. Go to your Space → "Files" tab
2. Click on file you want to update
3. Click "Edit" → Make changes → "Commit"

---

## 🐛 Troubleshooting

### App Shows "Building" Forever

**Solution:**
1. Check "Logs" tab in your Space
2. Look for errors (usually missing dependencies)
3. Make sure `requirements.txt` has all packages

### App Shows "Runtime Error"

**Solution:**
1. Check "Logs" tab
2. Common issues:
   - API keys not set (check Repository secrets)
   - Missing dependencies
   - Python version mismatch

### App is Slow

**Solution:**
- Free CPU tier is slower
- Upgrade to GPU ($0.60/hr) if needed:
  - Settings → Change hardware → Select GPU

### "ModuleNotFoundError"

**Solution:**
1. Check `requirements.txt` has the package
2. Make sure package names are correct
3. Rebuild Space (Settings → Factory reboot)

---

## 💡 Tips for Best Performance

### 1. Optimize for Hugging Face Free Tier

```python
# In config.py, use faster/cheaper models:
IDEAL_ANSWER_MODEL = "gpt-4o-mini"  # Cheaper than gpt-4o
PRO_AGENT_MODEL = "gpt-3.5-turbo"
CONS_AGENT_MODEL = "gpt-3.5-turbo"
SYNTHESIZER_MODEL = "gpt-4o-mini"
```

### 2. Add Caching

```python
# Cache common questions to reduce API calls
import functools

@functools.lru_cache(maxsize=100)
def cached_ideal_answer(question):
    # Your ideal answer logic
    pass
```

### 3. Rate Limiting

Add to your Gradio interface:
```python
demo.queue(max_size=50)  # Limit concurrent users
demo.launch(max_threads=40)
```

---

## 📱 Share Your Space

Once live, share your link:

- ✅ On LinkedIn: "Built an AI answer evaluator for my college project!"
- ✅ On Twitter: "Check out my AI-powered exam evaluator"
- ✅ In your resume: Link to live demo
- ✅ With friends: Let them test it

**Example share text:**
```
🎓 I built an AI Answer Evaluator using multi-agent AI!

✅ Evaluates exam answers across all subjects
✅ Supports multiple languages (Nepali, English, etc.)
✅ Provides detailed feedback and marks
✅ Completely free to use!

Try it: https://huggingface.co/spaces/YOUR_USERNAME/lokasewa-evaluator

Tech: Python, Gradio, LangGraph, GPT-4, Gemini
```

---

## 🎯 Summary: Quick Steps

1. **Push to GitHub**:
   ```powershell
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/lokasewa-evaluator.git
   git push -u origin main
   ```

2. **Create Space**:
   - Go to huggingface.co/spaces
   - Create new Space (Gradio SDK)
   - Link to GitHub repo

3. **Add Secrets**:
   - Settings → Repository secrets
   - Add `OPENROUTER_API_KEY`
   - Add `GOOGLE_API_KEY`

4. **Wait for Build**:
   - Check "App" tab
   - Wait 2-5 minutes
   - Done!

**Your permanent link**: `https://huggingface.co/spaces/YOUR_USERNAME/lokasewa-evaluator`

---

## ✅ Checklist Before Going Live

- [ ] Tested app locally (works correctly)
- [ ] Created GitHub account
- [ ] Pushed code to GitHub
- [ ] Created Hugging Face account
- [ ] Created Space on Hugging Face
- [ ] Linked GitHub repo to Space
- [ ] Added API key secrets
- [ ] Checked build logs (no errors)
- [ ] Tested live app (Space URL)
- [ ] Updated README with live link
- [ ] Shared with friends/college!

---

**🎉 Congratulations! Your app is now live and accessible to anyone in the world!**

---

## 🔒 IMPORTANT: API Key Security

### ⚠️ NEVER DO THIS:
```python
# DON'T hardcode keys in code!
API_KEY = "sk-xxxxx"  # ❌ WRONG!
```

### ✅ ALWAYS DO THIS:
```python
# Use environment variables
import os
API_KEY = os.getenv("OPENROUTER_API_KEY")  # ✓ CORRECT!
```

Your `config.py` already does this correctly! ✅

---

## 📞 Need Help?

If you face issues:

1. **Check Hugging Face Docs**: https://huggingface.co/docs/hub/spaces
2. **Hugging Face Discord**: https://discord.gg/huggingface
3. **Check build logs** in your Space
4. **Google the error message**

**Your app is ready to deploy! Follow the steps above and you'll have a permanent link in 15-20 minutes!** 🚀
