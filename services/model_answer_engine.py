# services/model_answer_engine.py
import json
from services.openai_client import get_openai_client

SYSTEM_PROMPT = """
You are an expert international admissions and UKVI interview trainer.
For each question, write a concise, high-quality model answer.
Requirements:
- 3–6 sentences.
- Clear structure (motivation, background, course fit, future plans where relevant).
- Honest tone suitable for a genuine student.
- No invented personal details (use only what is provided in the profile).
- Avoid sounding robotic or memorized.
"""

def generate_model_answer(
    profile: dict,
    question_obj: dict,
    student_answer: str | None = None,
    api_key: str | None = None,
) -> str:
    client = get_openai_client(api_key=api_key)

    context = {
        "student_profile": {
            "full_name": profile.get("full_name"),
            "home_country": profile.get("home_country"),
            "target_university": profile.get("target_university"),
            "target_course": profile.get("target_course"),
            "academic_background": profile.get("academic_background"),
            "english_level": profile.get("english_level"),
        },
        "question": question_obj.get("question"),
        "section": question_obj.get("section"),
        "student_answer": student_answer,
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Use the following JSON context to write ONE model answer.\n"
                "Respond with plain text only, no JSON or bullet list.\n\n"
                + json.dumps(context)
            ),
        },
    ]

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.5,
    )
    return resp.choices[0].message.content