"""
Resume Review Agent
--------------------
A beginner-friendly single-agent CrewAI application that compares a
candidate's resume against a target job description and produces a
structured, honest review (no invented skills or experience).

Stack: Streamlit (UI) + CrewAI (agent framework) + Groq (LLM provider)
"""

import os
import io
import re
import time

import streamlit as st

# pypdf is used for local PDF text extraction (no external services)
from pypdf import PdfReader
from pypdf.errors import PdfReadError

# CrewAI imports
from crewai import Agent, Task, Crew, Process, LLM


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Resume Review Agent",
    page_icon="🧾",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Helper: safely read secrets without crashing the app
# ---------------------------------------------------------------------------
def get_groq_api_key():
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return None


def get_groq_model():
    try:
        model = st.secrets.get("GROQ_MODEL")
    except Exception:
        model = None
    return model or "openai/gpt-oss-120b"


# ---------------------------------------------------------------------------
# Helper: extract text from an uploaded PDF
# ---------------------------------------------------------------------------
def extract_text_from_pdf(uploaded_file):
    """
    Returns (text, error_message).
    If extraction succeeds, error_message is None.
    If it fails, text is None and error_message explains why.
    """
    try:
        file_bytes = uploaded_file.read()
        reader = PdfReader(io.BytesIO(file_bytes))

        if len(reader.pages) == 0:
            return None, "The PDF appears to have no pages."

        extracted = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            extracted.append(page_text)

        full_text = "\n".join(extracted).strip()

        if not full_text:
            return None, (
                "We couldn't find any selectable text in this PDF. "
                "It might be a scanned image rather than a text-based PDF. "
                "Try pasting your resume text directly instead."
            )

        return full_text, None

    except PdfReadError:
        return None, "This file could not be read. Please upload a valid, non-corrupted PDF."
    except Exception:
        return None, "Something went wrong while reading the PDF. Please try a different file or paste the text instead."


# ---------------------------------------------------------------------------
# Helper: basic input cleanup / validation
# ---------------------------------------------------------------------------
def clean_text(text, max_chars=15000):
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


# ---------------------------------------------------------------------------
# CrewAI setup: exactly 1 agent, 1 task, 1 crew
# ---------------------------------------------------------------------------
def build_crew(resume_text, job_description_text, api_key, model_name):
    """
    Creates and returns a Crew configured with a single Agent and a
    single Task. Called fresh for each review so there is no shared
    state between requests.
    """

    llm = LLM(
        model=f"groq/{model_name}",
        api_key=api_key,
        temperature=0.2,
    )

    reviewer_agent = Agent(
        role="Resume Reviewer",
        goal=(
            "Objectively compare a candidate's resume against a target job "
            "description and produce an honest, structured, and actionable review."
        ),
        backstory=(
            "You are a meticulous technical recruiter with years of experience "
            "screening resumes. You are extremely careful never to assume or "
            "invent details. You only report what the resume actually states. "
            "When something cannot be confirmed, you clearly label it as "
            "Unknown / Not Demonstrated rather than guessing."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    task_description = f"""
You will compare a candidate's RESUME against a JOB DESCRIPTION.

CRITICAL ACCURACY RULE:
- Never invent or assume experience, skills, qualifications, projects,
  certifications, achievements, employment history, or education.
- Only say something is present if it is explicitly supported by the
  resume text below.
- If you cannot determine whether a requirement is met, classify it as
  "Unknown / Not Demonstrated" rather than guessing.

RESUME:
---
{resume_text}
---

JOB DESCRIPTION:
---
{job_description_text}
---

Produce your review using EXACTLY the following Markdown structure and
headings (use "- " bullet points under each heading, and write
"None identified." if a section has nothing to list):

## Match Summary
A short (3-5 sentence) honest overall assessment of fit.

## Skills Found
- List skills explicitly present in the resume that are relevant to the job.

## Missing Requirements
- List requirements from the job description that the resume does not
  show evidence of.

## Unclear / Not Demonstrated
- List items that might be present but are not clearly stated in the resume.

## Experience Gaps
- Describe any gaps between required experience and what the resume shows.

## Education / Qualification Gaps
- Describe any gaps between required education/qualifications and what
  the resume shows.

## Resume Improvements
- Concrete, specific suggestions to improve the resume's wording, structure,
  or content (without inventing new experience).

## Keywords to Consider
- Relevant keywords/phrases from the job description the candidate could
  naturally incorporate if truthfully applicable.

## Priority Action Plan
1. Most important action first.
2. Next most important action.
3. Continue as needed (3-6 total steps).
"""

    review_task = Task(
        description=task_description,
        expected_output=(
            "A Markdown document following the exact section headings requested, "
            "with honest, evidence-based content and no fabricated details."
        ),
        agent=reviewer_agent,
    )

    crew = Crew(
        agents=[reviewer_agent],
        tasks=[review_task],
        process=Process.sequential,
        verbose=False,
    )

    return crew


# ---------------------------------------------------------------------------
# Helper: run the crew with basic retry logic for transient Groq errors
# ---------------------------------------------------------------------------
def run_review(resume_text, job_description_text, api_key, model_name, max_retries=2):
    """
    Returns (result_text, error_message).
    """
    attempt = 0
    last_error = None

    while attempt <= max_retries:
        try:
            crew = build_crew(resume_text, job_description_text, api_key, model_name)
            result = crew.kickoff()
            return str(result), None

        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            # Rate limit / temporary server errors: wait a bit and retry
            if any(term in error_str for term in ["rate limit", "429", "503", "timeout", "temporarily"]):
                attempt += 1
                if attempt <= max_retries:
                    time.sleep(2 * attempt)
                    continue
                return None, (
                    "The AI service is currently busy or rate-limited. "
                    "Please wait a moment and try again."
                )

            # Auth errors
            if any(term in error_str for term in ["unauthorized", "invalid api key", "401", "authentication"]):
                return None, (
                    "Your Groq API key appears to be missing or invalid. "
                    "Please check your Streamlit secrets configuration."
                )

            # Model errors
            if any(term in error_str for term in ["model", "not found", "decommission"]):
                return None, (
                    "The selected Groq model is unavailable. Please check that "
                    "GROQ_MODEL in your secrets is set to a currently supported model."
                )

            # Anything else: fail without exposing a raw stack trace
            return None, (
                "Something went wrong while generating the review. "
                "Please try again in a moment."
            )

    return None, "The AI service did not respond successfully after multiple attempts. Please try again later."


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("🧾 Resume Review Agent")
st.caption("Beginner-friendly AI resume feedback, powered by CrewAI + Groq")

with st.expander("🔒 Privacy Notice", expanded=False):
    st.write(
        "Your resume and job description are sent to the configured LLM "
        "provider (Groq) only to generate this review. Nothing is stored "
        "permanently by this application, and no data is saved to a "
        "database. Please avoid pasting highly sensitive personal "
        "information beyond what is normally on a resume."
    )

st.divider()

# --- Resume input ---
st.subheader("1. Your Resume")
resume_input_method = st.radio(
    "How would you like to provide your resume?",
    ["Paste text", "Upload PDF"],
    horizontal=True,
)

resume_text = ""

if resume_input_method == "Paste text":
    resume_text = st.text_area(
        "Paste your resume text here",
        height=250,
        placeholder="Paste the full text of your resume...",
    )
else:
    uploaded_pdf = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
    if uploaded_pdf is not None:
        with st.spinner("Reading your PDF..."):
            extracted_text, pdf_error = extract_text_from_pdf(uploaded_pdf)
        if pdf_error:
            st.error(pdf_error)
        else:
            resume_text = extracted_text
            st.success("PDF text extracted successfully.")
            with st.expander("Preview extracted text"):
                st.text(resume_text[:2000] + ("..." if len(resume_text) > 2000 else ""))

# --- Job description input ---
st.subheader("2. Target Job Description")
job_description_text = st.text_area(
    "Paste the job description here",
    height=250,
    placeholder="Paste the full job description text...",
)

st.divider()

# --- Review button ---
review_clicked = st.button("🔍 Review My Resume", type="primary", use_container_width=True)

if review_clicked:
    api_key = get_groq_api_key()
    model_name = get_groq_model()

    resume_clean = clean_text(resume_text)
    jd_clean = clean_text(job_description_text)

    # --- Validation ---
    if not api_key:
        st.error(
            "Missing Groq API key. Please add GROQ_API_KEY to your "
            "Streamlit secrets before using this app."
        )
    elif not resume_clean:
        st.warning("Please paste your resume text or upload a valid PDF before continuing.")
    elif not jd_clean:
        st.warning("Please paste the target job description before continuing.")
    elif len(resume_clean) < 30:
        st.warning("Your resume text looks too short. Please check the input and try again.")
    elif len(jd_clean) < 30:
        st.warning("The job description looks too short. Please check the input and try again.")
    else:
        with st.spinner("Analyzing your resume against the job description... this can take up to a minute."):
            result_text, error_message = run_review(resume_clean, jd_clean, api_key, model_name)

        if error_message:
            st.error(error_message)
        else:
            st.success("Review complete!")
            st.divider()
            st.markdown(result_text)

            st.download_button(
                label="⬇️ Download Review as Markdown",
                data=result_text,
                file_name="resume_review.md",
                mime="text/markdown",
                use_container_width=True,
            )

st.divider()
st.caption("Built with CrewAI, Streamlit, and Groq · For educational purposes.")
