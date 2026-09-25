import re
import os
import uuid
from pydantic import BaseModel, Field
from openai import OpenAI
from supabase import create_client, Client

def optimize_svg(svg_code: str) -> str:
    """
    Minifies raw SVG string by stripping comments, extra whitespace, 
    XML declarations, and rounding float precision.
    """
    # 1. Remove XML declarations and doctype header
    svg = re.sub(r"<\?xml.*?\?>", "", svg_code)
    svg = re.sub(r"<!DOCTYPE.*?>", "", svg, flags=re.DOTALL)

    # 2. Remove HTML/XML comments
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.DOTALL)

    # 3. Round long floating-point numbers to 2 decimal places (e.g. 102.39482 -> 102.39)
    svg = re.sub(r"(\d+\.\d{2})\d+", r"\1", svg)

    # 4. Collapse multiple spaces, newlines, and tabs
    svg = re.sub(r"\s+", " ", svg)

    # 5. Remove space between tags
    svg = re.sub(r">\s+<", "><", svg)

    return svg.strip()
import os
import json
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from openai import OpenAI
from supabase import create_client, Client

# Environment Credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Use Service Role Key to bypass RLS write policies
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY]):
    raise ValueError("Missing required environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = OpenAI(api_key=OPENAI_API_KEY)


# Pydantic Schema for Strict Output Validation
class SingleQuestion(BaseModel):
    stem_text: str = Field(description="Problem text/story.")
    latex_content: Optional[str] = Field(description="Standalone equation string or math formula in LaTeX.")
    options_json: Optional[Dict[str, str]] = Field(description="Map of options {'A': '...', 'B': '...'}, or null for integer answers.")
    correct_answer: str = Field(description="Correct option key ('A', 'B') or numeric integer string.")
    difficulty_rating: int = Field(description="Rating from 1 to 10.")
    detailed_solution_latex: str = Field(description="Comprehensive solution steps with LaTeX.")
    kid_friendly_hint: str = Field(description="Hint guiding the student.")


def generate_exam_set(
    certification_id: str,
    level_code: str,
    set_title: str,
    year: Optional[int] = 2026,
    access_tier: str = 'free'
):
    print(f"--- Creating Exam Set: '{set_title}' for {certification_id} ({level_code}) ---")

    # 1. Fetch Certification, Level, and Structure Rules
    cert = supabase.table("certifications").select("*").eq("id", certification_id).single().execute().data
    level = supabase.table("exam_levels").select("*").eq("certification_id", certification_id).eq("level_code", level_code).single().execute().data
    rules = supabase.table("exam_structure_rules").select("*").eq("level_id", level["id"]).execute().data
    topics = supabase.table("topics").select("*").execute().data

    if not rules:
        raise ValueError(f"No exam_structure_rules found for level_id: {level['id']}")

    # 2. Insert Practice Set Metadata into `exam_sets`
    set_payload = {
        "certification_id": certification_id,
        "level_id": level["id"],
        "title": set_title,
        "description": f"Complete practice set for {cert['full_name']} ({level_code}).",
        "year": year,
        "time_minutes": cert["default_time_minutes"],
        "is_published": True, # Publish immediately[cite: 1]
        "access_tier": access_tier
    }
    
    set_res = supabase.table("exam_sets").insert(set_payload).execute() #[cite: 1]
    set_id = set_res.data[0]["id"] #[cite: 1]
    print(f"Created Practice Set ID: {set_id} | Title: {set_title}") #[cite: 1]

    # 3. Generate Questions for Each Section & Map to `exam_set_questions`[cite: 1]
    global_position = 1

    for rule in rules:
        questions_to_generate = rule["questions_count"]
        print(f"Generating {questions_to_generate} questions for section: '{rule['section_name']}'...")

        for i in range(questions_to_generate):
            # Pick a topic round-robin style
            topic = topics[i % len(topics)]

            system_prompt = f"""
            You are an expert Math Olympiad Problem Designer for {cert['full_name']}.
            Generate 1 unique {rule['question_type']} question for Grade {level['target_grade_min']}-{level['target_grade_max']}.
            Topic: {topic['title']} ({topic['domain_code']})
            Section: {rule['section_name']}
            Philosophy: {cert['prompt_philosophy']}
            Ensure all mathematical formulas are valid LaTeX.
            """

            try:
                completion = ai_client.beta.chat.completions.parse(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Generate question #{global_position} for this set."}
                    ],
                    response_format=SingleQuestion,
                    temperature=0.7,
                )

                q_data = completion.choices[0].message.parsed

                # Insert into `questions` table[cite: 1]
                q_payload = {
                    "certification_id": certification_id,
                    "level_id": level["id"],
                    "topic_id": topic["id"],
                    "question_type": rule["question_type"],
                    "stem_text": q_data.stem_text,
                    "latex_content": q_data.latex_content,
                    "options_json": q_data.options_json,
                    "correct_answer": q_data.correct_answer,
                    "points": rule["points_per_correct"],
                    "penalty_points": rule["penalty_points"],
                    "difficulty_rating": q_data.difficulty_rating,
                    "detailed_solution_latex": q_data.detailed_solution_latex,
                    "kid_friendly_hint": q_data.kid_friendly_hint,
                    "is_ai_generated": True
                }

                q_res = supabase.table("questions").insert(q_payload).execute() #[cite: 1]
                question_id = q_res.data[0]["id"] #[cite: 1]

                # Map Question to Practice Set in `exam_set_questions`[cite: 1]
                mapping_payload = {
                    "set_id": set_id,
                    "question_id": question_id,
                    "position": global_position
                }
                supabase.table("exam_set_questions").insert(mapping_payload).execute() #[cite: 1]

                print(f"  -> Added Question #{global_position} (ID: {question_id}) to Set ID: {set_id}") #[cite: 1]
                global_position += 1

            except Exception as e:
                print(f"Error generating question #{global_position}: {e}")

    print(f"SUCCESS: Generated complete practice set '{set_title}' with {global_position - 1} questions.")


if __name__ == "__main__":
    # Example: Generate a 2026 Mock Paper for Math Kangaroo Ecolier
    generate_exam_set(
        certification_id="IKMC",
        level_code="ECOLIER",
        set_title="2026 Official Mock Set 1",
        year=2026,
        access_tier="free"
    )