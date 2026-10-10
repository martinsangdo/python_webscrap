import os
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv(override=True) 

# Environment Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Service key to bypass RLS write policies
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.8-flash"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = genai.Client(api_key=GEMINI_API_KEY)


# --- PYDANTIC SCHEMAS FOR MULTI-TYPE GENERATION ---

class QuestionItem(BaseModel):
    position: int = Field(description="1-based question index in the exam paper.")
    section_name: str = Field(description="Name of the exam section.")
    question_type: str = Field(description="'MCQ_5_OPTION', 'MCQ_4_OPTION', 'INTEGER_FILL', or 'PROOF'.")
    stem_text: str = Field(description="The problem text.")
    latex_content: Optional[str] = Field(description="Standalone equation or formula in LaTeX.")
    
    # Visual / Chart variations
    has_image_or_chart: bool = Field(description="True if this problem requires a diagram or chart.")
    chart_type: Optional[str] = Field(description="'BAR', 'LINE', 'PIE', 'GEOMETRY_SVG', or null.")
    chart_data: Optional[Dict[str, Any]] = Field(description="Structured JSON for charts (categories, values) or null.")
    
    # Options & Answers
    options_json: Optional[Dict[str, str]] = Field(description="{'A': '...', 'B': '...'} for MCQs, null for INTEGER_FILL.")
    correct_answer: str = Field(description="Choice letter ('A', 'B') or integer string ('142').")
    
    points: int = Field(description="Whole-number marks awarded for correct answer.")
    penalty_points: float = Field(description="Marks deducted for incorrect answer.")
    difficulty_rating: int = Field(description="1 (Easiest) to 10 (Hardest).")
    detailed_solution_latex: str = Field(description="Step-by-step LaTeX solution.")
    kid_friendly_hint: str = Field(description="Hint for junior learners.")

class PracticeSetSchema(BaseModel):
    set_title: str = Field(description="Official title of the practice set.")
    total_questions: int = Field(description="Total count of questions.")
    questions: List[QuestionItem] = Field(description="Array of formatted questions matching the required section variation.")


# --- GENERATOR FUNCTION ---

def generate_complete_practice_set(certification_id: str, level_code: str, set_title: str):
    print(f"=== Generating Complete Practice Test: '{set_title}' ===")

    # 1. Fetch Metadata from DB
    cert = supabase.table("certifications").select("*").eq("id", certification_id).single().execute().data
    level = supabase.table("exam_levels").select("*").eq("certification_id", certification_id).eq("level_code", level_code).single().execute().data
    rules = supabase.table("exam_structure_rules").select("*").eq("level_id", level["id"]).execute().data
    topics = supabase.table("topics").select("*").execute().data

    # Build human-readable breakdown string from database rules
    rules_breakdown = []
    total_q_count = 0
    for r in rules:
        total_q_count += r["questions_count"]
        rules_breakdown.append(
            f"- Section: '{r['section_name']}' | Count: {r['questions_count']} | Type: {r['question_type']} | Points: +{r['points_per_correct']} (Penalty: -{r['penalty_points']})"
        )
    rules_text = "\n".join(rules_breakdown)

    # 2. System Prompt configured with Exam Rules
    system_prompt = f"""
    You are an official Master Problem Setter for {cert['full_name']} ({certification_id}).
    
    EXAM METADATA:
    - Target Grade Band: Grade {level['target_grade_min']} to Grade {level['target_grade_max']}
    - Total Questions Required: {total_q_count}
    - Style Philosophy: {cert['prompt_philosophy']}

    REQUIRED SECTION BREAKDOWN & QUESTION TYPES:
    {rules_text}

    VARIATION RULES:
    1. STRICTLY adhere to the question types specified for each section.
    2. For 'MCQ_5_OPTION', supply options A, B, C, D, E.
    3. For 'MCQ_4_OPTION', supply options A, B, C, D.
    4. For 'INTEGER_FILL', options_json MUST be null, and correct_answer MUST be an integer string.
    5. Include 1 to 3 chart/graph questions (BAR, PIE, LINE) with structured `chart_data` (categories and values).
    6. Ensure questions progress in difficulty and cover diverse topics (Logic, Arithmetic, Geometry, Number Theory, Combinatorics).
    7. All mathematical formulas must be formatted in valid LaTeX ($...$).
    """

    print(f"Requesting full practice set from Gemini ({GEMINI_MODEL})...")
    response = ai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"Generate a full {total_q_count}-question practice test paper for {set_title}.",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_json_schema=PracticeSetSchema.model_json_schema(),
            temperature=0.7,
        ),
    )

    result = PracticeSetSchema.model_validate_json(response.text)
    print(f"Generated {len(result.questions)} questions successfully.")

    # 3. Validate the AI output BEFORE touching the database
    positions = sorted(q.position for q in result.questions)
    if positions != list(range(1, total_q_count + 1)):
        raise ValueError(f"Expected positions 1..{total_q_count}, got {positions}")
    allowed_types = {r["question_type"] for r in rules}
    bad_types = {q.question_type for q in result.questions} - allowed_types
    if bad_types:
        raise ValueError(f"Unexpected question types from AI: {bad_types}")

    # 4. Write everything: questions -> hidden set -> links -> publish.
    # The set stays unpublished until every row is in, and partial rows are removed on failure.
    q_payloads = [{
        "certification_id": certification_id,
        "level_id": level["id"],
        # Assign a topic ID round-robin
        "topic_id": topics[(q.position - 1) % len(topics)]["id"],
        "question_type": q.question_type,
        "stem_text": q.stem_text,
        "latex_content": q.latex_content,
        "chart_type": q.chart_type,
        "chart_data": q.chart_data,
        "options_json": q.options_json,
        "correct_answer": q.correct_answer,
        "points": q.points,
        "penalty_points": q.penalty_points,
        "difficulty_rating": q.difficulty_rating,
        "detailed_solution_latex": q.detailed_solution_latex,
        "kid_friendly_hint": q.kid_friendly_hint,
        "is_ai_generated": True
    } for q in result.questions]

    question_ids: List[int] = []
    set_id = None
    try:
        question_ids = [row["id"] for row in supabase.table("questions").insert(q_payloads).execute().data]

        set_payload = {
            "certification_id": certification_id,
            "level_id": level["id"],
            "title": set_title,
            "description": f"Full practice exam set for {cert['full_name']} ({level_code}).",
            "time_minutes": cert["default_time_minutes"],
            "is_published": False,
            "access_tier": "free"
        }
        set_id = supabase.table("exam_sets").insert(set_payload).execute().data[0]["id"]

        links = [
            {"set_id": set_id, "question_id": qid, "position": q.position}
            for qid, q in zip(question_ids, result.questions)
        ]
        supabase.table("exam_set_questions").insert(links).execute()

        supabase.table("exam_sets").update({"is_published": True}).eq("id", set_id).execute()
    except Exception:
        print("Database write failed, rolling back partial rows...")
        if set_id:
            supabase.table("exam_set_questions").delete().eq("set_id", set_id).execute()
            supabase.table("exam_sets").delete().eq("id", set_id).execute()
        if question_ids:
            supabase.table("questions").delete().in_("id", question_ids).execute()
        raise

    print(f"=== SUCCESS: Practice Set '{set_title}' (ID: {set_id}) with {len(question_ids)} questions Created & Published! ===")

#find out what levels of a certification
def get_available_level_codes(certification_id: str) -> list[str]:
    response = supabase.table("exam_levels") \
        .select("level_code, target_grade_min, target_grade_max") \
        .eq("certification_id", certification_id) \
        .order("target_grade_min") \
        .execute()
    
    levels = response.data
    level_codes = [item["level_code"] for item in levels]
    
    print(f"Available level codes for {certification_id}: {level_codes}")
    return level_codes

# Example usage:
codes = get_available_level_codes("IKMC")
# Output: ['PRE_ECOLIER', 'ECOLIER', 'BENJAMIN', 'CADET', 'JUNIOR', 'STUDENT']

generate_complete_practice_set(
        certification_id="SASMO",
        level_code="PRIMARY_4",
        set_title="SASMO 2026 Full Model Practice Set 1"
    )