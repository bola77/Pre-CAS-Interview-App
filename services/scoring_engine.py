# services/scoring_engine.py
import json
from services.openai_client import get_openai_client

RUBRIC = """
You are an expert in university admissions and UKVI credibility interviews.
Score the student's answer on:
- relevance (1-4)
- structure (1-4)
- clarity (1-4)
- confidence (1-4)
- overall (1-4, average of the above)
- risk_flags (list of short strings, can be empty)
- improved_answer_hint (one short coaching hint)
Return ONLY one JSON object with these keys, no explanation.
"""

def score_response(question_obj: dict, answer: str, api_key: str | None = None) -> dict:
    client = get_openai_client(api_key=api_key)
    question_text = question_obj["question"]
    user_msg = f"""
Question: {question_text}
Student answer: {answer}
Apply the rubric and produce scores.
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
    )
    content = resp.choices[0].message.content

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {
            "relevance": 2,
            "structure": 2,
            "clarity": 2,
            "confidence": 2,
            "overall": 2,
            "risk_flags": ["Scoring fallback used"],
            "improved_answer_hint": "Explain your motivation, background, and goals more clearly.",
        }

    data.update({
        "question_id": question_obj["id"],
        "section": question_obj.get("section", "general"),
    })
    return data