import os
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv(override=True) 

# Environment Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Service key to bypass RLS write policies
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = OpenAI(api_key=OPENAI_API_KEY)


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
    
    points: float = Field(description="Marks awarded for correct answer.")
    penalty_points: float = Field(description="Marks deducted for incorrect answer.")
    difficulty_rating: int = Field(description="1 (Easiest) to 10 (Hardest).")
    detailed_solution_latex: str = Field(description="Step-by-step LaTeX solution.")
    kid_friendly_hint: str = Field(description="Hint for junior learners.")

class PracticeSetSchema(BaseModel):
    set_title: str = Field(description="Official title of the practice set.")
    total_questions: int = Field(description="Total count of questions.")
    questions: List[QuestionItem] = Field(description="Array of formatted questions matching the required section variation.")


# --- GENERATOR FUNCTION ---

def generate_complete_practice_set(certification_id: str, level_code: str, set_title: str, year: int = 2026):
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

    print("Requesting full practice set from OpenAI GPT-4o...")
    completion = ai_client.beta.chat.completions.parse(
        model="gpt-5.4-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a full {total_q_count}-question practice test paper for {set_title}."}
        ],
        response_format=PracticeSetSchema,
        temperature=0.7,
    )

    result = completion.choices[0].message.parsed
    print(f"Generated {len(result.questions)} questions successfully.")

    # 3. Create Record in `exam_sets` Table[cite: 1]
    set_payload = {
        "certification_id": certification_id,
        "level_id": level["id"],
        "title": set_title,
        "description": f"Full practice exam set for {cert['full_name']} ({level_code}).",
        "year": year,
        "time_minutes": cert["default_time_minutes"],
        "is_published": True,
        "access_tier": "free"
    }
    set_res = supabase.table("exam_sets").insert(set_payload).execute()
    set_id = set_res.data[0]["id"]

    # 4. Insert Questions into `questions` & Link to `exam_set_questions`
    for q in result.questions:
        # Assign a topic ID round-robin
        assigned_topic = topics[(q.position - 1) % len(topics)]

        q_payload = {
            "certification_id": certification_id,
            "level_id": level["id"],
            "topic_id": assigned_topic["id"],
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
        }

        # Insert question[cite: 1]
        inserted_q = supabase.table("questions").insert(q_payload).execute()
        q_id = inserted_q.data[0]["id"]

        # Map to exam set position[cite: 1]
        supabase.table("exam_set_questions").insert({
            "set_id": set_id,
            "question_id": q_id,
            "position": q.position
        }).execute()

        print(f"  [Q{q.position}/{total_q_count}] Created ({q.question_type}) -> Linked to Set ID {set_id}")

    print(f"=== SUCCESS: Practice Set '{set_title}' (ID: {set_id}) Created & Published! ===")

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
        set_title="SASMO 2026 Full Model Practice Set 1",
        year=2026
    )