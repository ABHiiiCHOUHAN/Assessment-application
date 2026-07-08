import streamlit as st
import json
import os
import uuid
from datetime import datetime
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from PIL import Image
import io
import fitz
from typing import Optional
from streamlit_tags import st_tags

HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(history_data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_data, f, indent=4)

# --- Define Pydantic Models for Structured Output ---
class QuestionFeedback(BaseModel):
    question: str = Field(description="The text of the question")
    student_answer: str = Field(description="The answer provided by the student")
    correctness: bool = Field(description="Whether the student's answer is correct")
    explanation: str = Field(description="A one-line explanation of the correct answer")
    mcq_breakdown: Optional[str] = Field(description="If it's an MCQ, a one-line breakdown explaining why other options are incorrect. If not an MCQ, set to null.", default=None)
    marks_awarded: float = Field(description="Marks awarded for this question")

class SubjectScore(BaseModel):
    subject: str = Field(description="Name of the subject (Mathematics, Science, General Knowledge, Mental Ability)")
    score: float = Field(description="Total score obtained in this subject")
    max_score: float = Field(description="Maximum possible score for this subject")

class ExamEvaluation(BaseModel):
    subject_scores: list[SubjectScore] = Field(description="Scores broken down by subject")
    questions: list[QuestionFeedback] = Field(description="Detailed feedback for each question")
    total_score: float = Field(description="Total score obtained across all subjects")
    total_max_score: float = Field(description="Maximum possible total score")

# --- Page Config ---
st.set_page_config(page_title="AI Exam Scorer", page_icon="📝", layout="wide")

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #a0aec0;
        margin-bottom: 2rem;
    }
    .metadata-card {
        background-color: #1e2532;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
    }
    .metadata-text {
        font-size: 1.1rem;
        color: #e2e8f0;
        margin-bottom: 0.5rem;
    }
    .correct-ans {
        color: #48bb78;
        font-weight: bold;
    }
    .incorrect-ans {
        color: #f56565;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password", help="Enter your Google Gemini API Key")
    if api_key:
        st.success("API Key provided!")
    else:
        st.warning("Please enter your API Key to proceed.")
        
    st.markdown("---")
    app_mode = st.radio("Navigation", ["New Assessment", "History"])
    
    st.markdown("---")
    
    if app_mode == "New Assessment":
        assessment_mode = st.radio("Assessment Mode", ["Direct Assessment", "Assessment with Official Answer Key"])
        st.markdown("---")
    else:
        assessment_mode = None
    st.markdown("### About")
    st.info("This app uses Google's Gemini 2.5 Flash model to analyze and score handwritten or printed exam papers.")

if app_mode == "History":
    st.markdown('<p class="main-header">🕰️ Assessment History</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">View past student evaluations</p>', unsafe_allow_html=True)
    
    history = load_history()
    if not history:
        st.info("No past assessments found.")
    else:
        for record in reversed(history):
            with st.expander(f"{record['date']} - {record['student_name']} ({record['exam_name']}) - Score: {record.get('total_score', 0)}/{record.get('total_max_score', 0)}"):
                # Render metadata
                st.markdown(f"""
                <div class="metadata-card">
                    <p class="metadata-text"><strong>Student Name:</strong> {record['student_name']} | <strong>Roll No:</strong> {record['roll_number']}</p>
                    <p class="metadata-text"><strong>Exam:</strong> {record['exam_name']} | <strong>Type:</strong> {record['exam_type']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                evaluation = record['evaluation']
                
                # Render subject scores
                st.markdown("### Score Overview")
                num_cols = len(evaluation.get('subject_scores', [])) + 1
                cols = st.columns(num_cols)
                with cols[0]:
                    st.metric("Total Score", f"{evaluation.get('total_score', 0)} / {evaluation.get('total_max_score', 0)}")
                for i, subject_score in enumerate(evaluation.get('subject_scores', [])):
                    with cols[i+1]:
                        st.metric(subject_score['subject'], f"{subject_score['score']} / {subject_score['max_score']}")
                        
                # Detailed Question Breakdown
                st.markdown("### Detailed Question Breakdown")
                for i, q in enumerate(evaluation.get('questions', [])):
                    st.markdown(f"**Q{i+1}:** {q['question']}")
                    st.markdown(f"**Student Answer:** {q['student_answer']}")
                    correct_status = "✅ Correct" if q['correctness'] else "❌ Incorrect"
                    css_class = "correct-ans" if q['correctness'] else "incorrect-ans"
                    st.markdown(f"**Status:** <span class='{css_class}'>{correct_status}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Marks:** {q['marks_awarded']}")
                    st.markdown(f"**Explanation:** {q['explanation']}")
                    if q.get('mcq_breakdown'):
                        st.info(f"**MCQ Breakdown:** {q['mcq_breakdown']}")
                    st.markdown("---")
    st.stop()

# --- Main Area ---
st.markdown('<p class="main-header">📝 AI Exam Scorer & Analyzer</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Automated grading and detailed feedback powered by GenAI</p>', unsafe_allow_html=True)

# --- Input Fields ---
with st.container():
    st.markdown("### Student & Exam Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        student_name = st.text_input("Student Name", placeholder="e.g. John Doe")
        roll_number = st.text_input("Roll Number", placeholder="e.g. 101")
    with col2:
        exam_name = st.text_input("Exam Name", placeholder="e.g. Midterm 1")
        exam_type = st.selectbox("Exam Type", ["Mock Test", "Final", "Quiz", "Assignment"])
    with col3:
        total_questions = st.number_input("Total Questions", min_value=1, value=10)
        subjects = st_tags(
            label='Subjects',
            text='Type a subject and press ENTER ⏎',
            value=['Math', 'Science'],
            suggestions=['Math', 'Science', 'GK', 'English', 'History', 'Geography', 'Physics', 'Chemistry', 'Biology'],
            key='subject_tags'
        )
        subjects_str = ", ".join(subjects)

st.markdown("---")

# --- File Uploader ---
if assessment_mode == "Direct Assessment":
    st.markdown("### Upload Exam Paper")
    uploaded_file = st.file_uploader("Upload an Image (PNG/JPG) or PDF of the completed exam", type=["png", "jpg", "jpeg", "pdf"])
else:
    st.markdown("### Upload Assessment Documents")
    
    with st.container(border=True):
        st.markdown("#### 🧑‍🎓 Student Submission")
        col_qp_user, col_ak_user = st.columns(2)
        
        with col_qp_user:
            user_qp = st.file_uploader("User Question Paper", type=["png", "jpg", "jpeg", "pdf"])
            user_qp_marking = st.selectbox(
                "Are answers marked on this paper?", 
                ["No", "Yes (Tick marks)", "Yes (Highlights)", "Yes (Other)"],
                key="user_qp_marking_select"
            )
            
        with col_ak_user:
            if user_qp_marking == "No":
                user_ak = st.file_uploader("User Answer Key (Student's Answers)", type=["png", "jpg", "jpeg", "pdf"])
            else:
                user_ak = None
                st.info("ℹ️ Student answers are included in the Question Paper upload.")
                
    with st.container(border=True):
        st.markdown("#### 🏫 Official Documents")
        col_qp_off, col_ak_off = st.columns(2)
        
        with col_qp_off:
            official_qp = st.file_uploader("Official Question Paper", type=["png", "jpg", "jpeg", "pdf"])
            official_qp_marking = st.selectbox(
                "Are answers marked on this paper?", 
                ["No", "Yes (Tick marks)", "Yes (Highlights)", "Yes (Other)"],
                key="official_qp_marking_select"
            )
            
        with col_ak_off:
            if official_qp_marking == "No":
                official_ak = st.file_uploader("Official Answer Key", type=["png", "jpg", "jpeg", "pdf"])
            else:
                official_ak = None
                st.info("ℹ️ Official answers are included in the Question Paper upload.")

def process_file_to_parts(uploaded_file):
    parts = []
    if uploaded_file.type.startswith("image/"):
        image = Image.open(uploaded_file)
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=image.format or 'PNG')
        img_bytes = img_byte_arr.getvalue()
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type=uploaded_file.type))
    elif uploaded_file.type == "application/pdf":
        # Convert PDF to images using PyMuPDF (fitz)
        uploaded_file.seek(0)
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better resolution
            img_bytes = pix.tobytes("png")
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
    return parts

if st.button("Analyze & Score", type="primary"):
    if not api_key:
        st.error("Please provide a Gemini API Key in the sidebar.")
    elif assessment_mode == "Direct Assessment" and not uploaded_file:
        st.error("Please upload an exam paper.")
    elif assessment_mode == "Assessment with Official Answer Key" and not (user_qp and (user_ak or user_qp_marking != "No") and official_qp and (official_ak or official_qp_marking != "No")):
        st.error("Please upload all required documents for the Official Answer Key mode.")
    elif not student_name or not exam_name or not roll_number or not subjects:
        st.warning("Please fill in all student & exam information fields.")
    else:
        with st.spinner("Analyzing exam paper... This may take a minute."):
            try:
                # Initialize GenAI client
                client = genai.Client(api_key=api_key)
                
                user_parts = []
                official_parts = []
                prompt_text = ""
                
                if assessment_mode == "Direct Assessment":
                    # Process file
                    user_parts = process_file_to_parts(uploaded_file)
                    
                    # Prompt
                    prompt_text = f"""
                    You are an expert exam grader. Analyze the provided exam paper images.
                    The exam contains questions covering the following subjects: {subjects_str}.
                    Read each question, read the student's answer, evaluate its correctness, and award marks.
                    If it's a multiple-choice question (MCQ), briefly explain why the incorrect options are wrong.
                    Provide a one-line explanation for the correct answer.
                    Return the results strictly adhering to the requested JSON schema.
                    """
                else:
                    user_parts.extend(process_file_to_parts(user_qp))
                    if user_ak:
                        user_parts.extend(process_file_to_parts(user_ak))
                        
                    official_parts.extend(process_file_to_parts(official_qp))
                    if official_ak:
                        official_parts.extend(process_file_to_parts(official_ak))
                    
                    user_ak_note = "2. User (Student's) Exam Answer Key (their written answers)" if user_ak else f"Note: User's answers are marked directly on the User Question Paper using {user_qp_marking}."
                    official_ak_note = "4. Official Examination Answer Key" if official_ak else f"Note: Official answers are marked directly on the Official Question Paper using {official_qp_marking}."
                    
                    prompt_text = f"""
                    You are an expert exam grader. You are provided with documents in the following order:
                    1. User (Student's) Question Paper
                    {user_ak_note}
                    3. Official Question Paper (if attached)
                    {official_ak_note}
                    
                    The exam covers the following subjects: {subjects_str}.
                    
                    Your task is to:
                    - Evaluate the student's answers against the official answers.
                    - Determine correctness and award marks based on the official key.
                    - If it's a multiple-choice question (MCQ), briefly explain why the incorrect options are wrong.
                    - Provide a one-line explanation for the correct answer.
                    - Return the results strictly adhering to the requested JSON schema.
                    """
                
                # Chunking Logic (Batch Size of 1 part to avoid token limits for large exams)
                BATCH_SIZE = 1
                batched_user_parts = [user_parts[i:i + BATCH_SIZE] for i in range(0, len(user_parts), BATCH_SIZE)]
                total_batches = len(batched_user_parts)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                merged_evaluation = {
                    "subject_scores": [],
                    "questions": [],
                    "total_score": 0,
                    "total_max_score": 0
                }
                
                for idx, user_batch in enumerate(batched_user_parts):
                    status_text.markdown(f"**Analyzing batch {idx + 1} of {total_batches}...**")
                    
                    batch_prompt = prompt_text + "\\n\\nIMPORTANT: You are analyzing a partial chunk of the student's exam. Only evaluate the questions visible in the attached student pages for this batch."
                    
                    parts = [batch_prompt]
                    parts.extend(user_batch)
                    parts.extend(official_parts)
                    
                    # Call Gemini API with Structured Output
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=parts,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=ExamEvaluation,
                                temperature=0.1,
                                max_output_tokens=8192
                            ),
                        )
                    except Exception as api_err:
                        st.error(f"API Error on batch {idx + 1}: {api_err}")
                        st.stop()
                    
                    # Parse Response
                    try:
                        raw_text = response.text
                        if raw_text.startswith("```json"):
                            raw_text = raw_text.strip("```json").strip("```").strip()
                        elif raw_text.startswith("```"):
                            raw_text = raw_text.strip("```").strip()
                            
                        evaluation = json.loads(raw_text)
                        
                        # Merge Results
                        merged_evaluation["questions"].extend(evaluation.get("questions", []))
                        merged_evaluation["total_score"] += evaluation.get("total_score", 0)
                        merged_evaluation["total_max_score"] += evaluation.get("total_max_score", 0)
                        
                        for subj in evaluation.get("subject_scores", []):
                            existing = next((s for s in merged_evaluation["subject_scores"] if s["subject"] == subj["subject"]), None)
                            if existing:
                                existing["score"] += subj["score"]
                                existing["max_score"] += subj["max_score"]
                            else:
                                merged_evaluation["subject_scores"].append(subj)
                                
                    except Exception as e:
                        print(f"RAW FAILED AI RESPONSE (Batch {idx+1}):\\n{response.text}\\n")
                        st.error(f"Failed to parse batch {idx + 1}. The AI might have been cut off or returned an invalid structure.\\n\\n**Raw Error:** {e}")
                        with st.expander(f"View Raw AI Response for Batch {idx + 1}"):
                            try:
                                st.code(response.text, language="json")
                            except:
                                st.write("Could not retrieve response text. It might be blocked or empty.")
                        st.stop()
                        
                    progress_bar.progress((idx + 1) / total_batches)
                
                status_text.markdown("**Analysis Complete! Formatting results...**")
                evaluation = merged_evaluation
                
                # Save to History
                history = load_history()
                new_record = {
                    "id": str(uuid.uuid4()),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "student_name": student_name,
                    "roll_number": roll_number,
                    "exam_name": exam_name,
                    "exam_type": exam_type,
                    "total_score": evaluation.get("total_score", 0),
                    "total_max_score": evaluation.get("total_max_score", 0),
                    "evaluation": evaluation
                }
                history.append(new_record)
                save_history(history)
                
                st.success("Analysis Complete & Saved to History!")
                
                # --- Results Dashboard ---
                st.markdown("---")
                st.markdown("## 📊 Results Dashboard")
                
                # Metadata Card
                st.markdown(f"""
                <div class="metadata-card">
                    <p class="metadata-text"><strong>Student Name:</strong> {student_name} | <strong>Roll No:</strong> {roll_number}</p>
                    <p class="metadata-text"><strong>Exam:</strong> {exam_name} | <strong>Type:</strong> {exam_type}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Score Overview
                st.markdown("### Score Overview")
                
                num_cols = len(evaluation.get('subject_scores', [])) + 1
                cols = st.columns(num_cols)
                
                with cols[0]:
                    st.metric("Total Score", f"{evaluation.get('total_score', 0)} / {evaluation.get('total_max_score', 0)}")
                
                for i, subject_score in enumerate(evaluation.get('subject_scores', [])):
                    with cols[i+1]:
                        st.metric(subject_score['subject'], f"{subject_score['score']} / {subject_score['max_score']}")
                        
                # Detailed Question Breakdown
                st.markdown("### Detailed Question Breakdown")
                
                for i, q in enumerate(evaluation.get('questions', [])):
                    with st.expander(f"Question {i+1}: {q['question'][:50]}..."):
                        st.markdown(f"**Question:** {q['question']}")
                        st.markdown(f"**Student Answer:** {q['student_answer']}")
                        
                        correct_status = "✅ Correct" if q['correctness'] else "❌ Incorrect"
                        css_class = "correct-ans" if q['correctness'] else "incorrect-ans"
                        
                        st.markdown(f"**Status:** <span class='{css_class}'>{correct_status}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Marks Awarded:** {q['marks_awarded']}")
                        st.markdown(f"**Explanation:** {q['explanation']}")
                        
                        if q.get('mcq_breakdown'):
                            st.info(f"**MCQ Breakdown:** {q['mcq_breakdown']}")

            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")
