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

# Environment Variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Service key required for storage uploads
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = OpenAI(api_key=OPENAI_API_KEY)

BUCKET_NAME = "question-diagrams"

# Pydantic Schema for Question + SVG Output
class GeometryQuestionSchema(BaseModel):
    stem_text: str = Field(description="The problem statement.")
    svg_code: str = Field(description="Valid SVG string with viewBox '0 0 400 400', containing clean geometrical shapes and labels.")
    correct_answer: str = Field(description="The numeric or MCQ choice answer.")
    solution_latex: str = Field(description="LaTeX solution steps.")

def generate_and_upload_geometry_question(cert_id: str, topic_id: int):
    system_prompt = """
    You are a Math Olympiad geometry illustrator. 
    Generate a geometry problem along with valid XML SVG code.
    SVG RULES:
    - Include viewBox="0 0 400 400".
    - Use clean black lines (stroke="#000000", stroke-width="2"), white background.
    - Include <text> tags for vertex labels (A, B, C, D) and side length dimensions.
    """

    print("Generating geometry problem and SVG diagram with GPT-4o...")
    completion = ai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate a right-angled triangle problem with an inscribed circle, labeled vertices, and dimensions."}
        ],
        response_format=GeometryQuestionSchema,
        temperature=0.7,
    )

    result = completion.choices[0].message.parsed
    svg_bytes = result.svg_code.encode("utf-8")

    # 1. Upload SVG directly to Supabase Storage
    filename = f"geometry_{uuid.uuid4().hex[:8]}.svg"
    storage_path = f"svgs/{filename}"

    print(f"Uploading SVG to bucket '{BUCKET_NAME}' at '{storage_path}'...")
    supabase.storage.from_(BUCKET_NAME).upload(
        file=svg_bytes,
        path=storage_path,
        file_options={"content-type": "image/svg+xml"}
    )

    # 2. Get Public URL for the uploaded diagram
    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
    print(f"Generated Public Image URL: {public_url}")

    # 3. Insert record into Supabase 'questions' table
    payload = {
        "certification_id": cert_id,
        "topic_id": topic_id,
        "question_type": "INTEGER_FILL",
        "stem_text": result.stem_text,
        "image_url": public_url,  # Public SVG URL saved here
        "correct_answer": result.correct_answer,
        "detailed_solution_latex": result.solution_latex,
        "is_ai_generated": True
    }

    inserted = supabase.table("questions").insert(payload).execute()
    print(f"Successfully saved question with SVG diagram! Question ID: {inserted.data[0]['id']}")

if __name__ == "__main__":
    generate_and_upload_geometry_question(cert_id="AMC8", topic_id=1)