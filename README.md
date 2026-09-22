# 🧾 Resume Review Agent

A beginner-friendly AI application that compares your resume against a
target job description and gives you honest, structured, actionable
feedback — without inventing skills or experience you don't have.

Built with:
- **CrewAI** — a single AI agent that does the reviewing
- **Streamlit** — the web interface
- **Groq** — the LLM provider (fast, free-tier friendly)

---

## How It Works (Simple Explanation)

1. You paste your resume (or upload it as a PDF) and paste the job
   description into the app.
2. The app hands both texts to a single CrewAI **Agent** with one job:
   act like a careful, honest recruiter.
3. That agent runs one **Task**: compare the resume to the job
   description and write a structured report.
4. The report is shown on screen and can be downloaded as a Markdown
   file.

The agent is instructed to **never make things up**. If it can't tell
whether you have a certain skill or qualification from your resume
text, it will say "Unknown / Not Demonstrated" instead of guessing.

---

## Project File Structure

```
resume-review-agent/
├── app.py                          # Main Streamlit + CrewAI application
├── requirements.txt                # Pinned Python dependencies
├── README.md                       # This file
├── .gitignore                      # Files Git should ignore
└── .streamlit/
    └── secrets.toml.example        # Template for your API key (not a real secret)
```

---

## GitHub Setup Instructions

1. Create a new (empty) repository on GitHub, e.g. `resume-review-agent`.
2. On your computer, download/unzip this project folder.
3. Open a terminal in the project folder and run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Resume Review Agent"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/resume-review-agent.git
   git push -u origin main
   ```
4. Confirm on GitHub.com that `app.py`, `requirements.txt`, `README.md`,
   `.gitignore`, and `.streamlit/secrets.toml.example` all appear in
   the repository. Your real `secrets.toml` should **not** appear —
   that's expected and correct.

---

## Streamlit Community Cloud Deployment Instructions

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in
   with your GitHub account.
2. Click **"New app"**.
3. Select your `resume-review-agent` repository and the `main` branch.
4. Set **Main file path** to `app.py`.
5. Click **"Advanced settings"**:
   - Set **Python version** to **3.11**.
6. Still in Advanced settings (or after deployment, via **App
   settings → Secrets**), paste your secrets in this format:
   ```toml
   GROQ_API_KEY = "your-actual-groq-api-key"
   GROQ_MODEL = "openai/gpt-oss-120b"
   ```
7. Click **Deploy**. The first build can take a couple of minutes.
8. Once deployed, open the app URL and test it with a sample resume
   and job description.

### Getting a Groq API Key
1. Go to [console.groq.com](https://console.groq.com) and sign up/log in.
2. Navigate to **API Keys** and create a new key.
3. Copy it into your Streamlit secrets as shown above. Never share
   this key publicly or commit it to GitHub.

---

## Running Locally (Optional)

```bash
# 1. Create and activate a virtual environment
python3.11 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then edit .streamlit/secrets.toml with your real API key

# 4. Run the app
streamlit run app.py
```

---

## Common Errors and Fixes

| Error / Symptom | Likely Cause | Fix |
|---|---|---|
| "Missing Groq API key" | `GROQ_API_KEY` not set in secrets | Add it under App settings → Secrets on Streamlit Cloud, or in `.streamlit/secrets.toml` locally |
| "Your Groq API key appears to be missing or invalid" | Wrong/expired key | Generate a new key at console.groq.com and update your secrets |
| "The AI service is currently busy or rate-limited" | Too many requests / free-tier limits hit | Wait a minute and try again; consider upgrading your Groq plan |
| "The selected Groq model is unavailable" | Model name outdated or decommissioned | Check [Groq's model list](https://console.groq.com/docs/models) and update `GROQ_MODEL` in secrets |
| "We couldn't find any selectable text in this PDF" | PDF is a scanned image, not real text | Use "Paste text" instead, or run OCR on the PDF first |
| App fails to build on Streamlit Cloud | Python version mismatch or dependency conflict | Confirm Python 3.11 is selected in Advanced settings and that `requirements.txt` versions match this README |
| Blank or very short review output | Resume or job description text too short/generic | Paste more complete text (at least a few sentences) |

---

## Important Notes

- This app does **not** store your resume or job description anywhere
  permanently — it's only used in-memory to generate your review.
- The agent is deliberately restricted to reporting only what's
  explicitly in your resume, to avoid misleading feedback.
- This project intentionally uses a **single agent and single task**
  to stay simple and easy to understand for beginners. It does not use
  multiple agents, a database, RAG, authentication, or Docker.
