# 🎓 AI Answer Evaluator

**Professional Exam Answer Assessment Powered by Multi-Agent AI**

A sophisticated AI-powered system that evaluates exam answers using a multi-agent architecture. Supports all subjects (law, business, mathematics, science, etc.) and all languages (Nepali, English, Hindi, etc.).

## 🌟 Features

- **Multi-Agent AI System**: 4 specialized agents (Ideal Answer Generator, Pro Agent, Cons Agent, Synthesizer)
- **Context-Aware Evaluation**: Adapts to different subjects automatically
- **Multi-Language Support**: Works with Nepali, English, Hindi, and more
- **Strict Evaluation**: Realistic scoring (no mark inflation)
- **Comprehensive Feedback**: Detailed strengths, gaps, and recommendations
- **Cost Transparency**: Shows API costs for each evaluation
- **Fast Processing**: ~30-60 seconds per evaluation

## 🚀 Try It Online

👉 **[Live Demo on Hugging Face Spaces](https://huggingface.co/spaces/YOUR_USERNAME/lokasewa-evaluator)** *(Update this link after deployment)*

## 📸 Screenshots

*(Add screenshots here after deployment)*

## 🛠️ Technology Stack

- **Frontend**: Gradio
- **AI Models**: 
  - OCR: Google Gemini 2.0 Flash
  - Text Generation: GPT-4, Grok-2 via OpenRouter
- **Backend**: Python 3.11+
- **Orchestration**: LangGraph
- **Deployment**: Hugging Face Spaces

## 🏗️ Architecture

```
┌─────────────┐
│  OCR Agent  │ ← Extracts text from images/PDFs
└──────┬──────┘
       │
       ↓
┌─────────────────────┐
│ Ideal Answer Agent  │ ← Generates model answer
└──────┬──────────────┘
       │
       ├─────────────────┬──────────────────┐
       ↓                 ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Pro Agent   │  │  Cons Agent  │  │              │
│ (Strengths)  │  │  (Gaps)      │  │              │
└──────┬───────┘  └──────┬───────┘  │              │
       │                 │           │              │
       └────────┬────────┘           │              │
                ↓                    ↓              │
         ┌──────────────────┐                      │
         │  Synthesizer     │ ← Combines analyses   │
         │  (Final Marks)   │   & generates marks   │
         └──────────────────┘                      │
```

## 📊 Evaluation Process

1. **OCR Extraction**: Converts handwritten/typed answers to text
2. **Ideal Answer Generation**: Creates benchmark answer for comparison
3. **Parallel Analysis**: 
   - Pro Agent finds strengths
   - Cons Agent identifies gaps
4. **Synthesis**: Combines analyses into final evaluation with marks

## 🔧 Local Installation

### Prerequisites
- Python 3.11 or higher
- OpenRouter API Key
- Google AI Studio API Key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/lokasewa-evaluator.git
cd lokasewa-evaluator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Create .env file (Windows)
echo OPENROUTER_API_KEY=your_openrouter_key > .env
echo GOOGLE_API_KEY=your_google_key >> .env

# Or set in terminal (Windows PowerShell)
$env:OPENROUTER_API_KEY="your_openrouter_key"
$env:GOOGLE_API_KEY="your_google_key"
```

4. Run the app:
```bash
python app.py
```

5. Open browser to `http://localhost:7860`

## 🌍 Deployment

### Hugging Face Spaces (Recommended)

1. Fork/clone this repository
2. Create a new Space on Hugging Face
3. Connect your GitHub repo
4. Add API keys in Space settings (Secrets)
5. Space will auto-deploy!

See `EVALUATION_AND_DEPLOYMENT_GUIDE.md` for detailed deployment instructions.

## 📈 Performance

- **Evaluation Time**: 30-60 seconds
- **Cost per Evaluation**: ~$0.002 USD (रू 0.28 NPR)
- **Supports**: All subjects and languages
- **Accuracy Target**: Within ±8 marks of expert evaluations

## 📚 Documentation

- `EVALUATION_AND_DEPLOYMENT_GUIDE.md` - Comprehensive validation & deployment guide
- `QUICK_REFERENCE.md` - Quick answers to common questions
- `SYSTEM_IMPROVEMENTS.md` - Recent improvements and features

## 🎯 Use Cases

- **Students**: Practice exam answers and get instant feedback
- **Teachers**: Assist in grading and provide consistent feedback
- **Tutors**: Scale tutoring services with AI assistance
- **Exam Preparation**: Comprehensive evaluation for competitive exams

## 🔐 Privacy & Security

- Evaluations are processed in real-time and not stored
- Session data is automatically cleaned after evaluation
- API keys are securely managed via environment variables
- No user data is collected or retained

## 💰 Cost Structure

- **OCR**: Uses Google Gemini (free tier available)
- **AI Evaluation**: ~$0.002 per evaluation via OpenRouter
- **Hosting**: Free on Hugging Face Spaces

## 🤝 Contributing

This is a college project created for educational purposes. Feedback and suggestions are welcome!

## 📄 License

This project is for educational purposes. Please ensure you comply with API provider terms of service (OpenRouter, Google AI Studio).

## 👨‍💻 Author

Created as a college project to democratize exam preparation using AI.

## 🙏 Acknowledgments

- OpenRouter for unified LLM API access
- Google for Gemini AI
- Hugging Face for hosting
- Gradio for the amazing UI framework

## 📞 Contact

For questions or feedback about this project, please open an issue on GitHub.

---

**⭐ Star this repository if you find it helpful!**
