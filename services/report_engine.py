# services/report_engine.py
import json
from services.openai_client import get_openai_client

def build_final_report(
    profile: dict,
    config: dict,
    questions: list[dict],
    responses: list[dict],
    scores: list[dict],
    api_key: str | None = None,
) -> dict | None:
    if not scores:
        return None

    avg_score = round(sum(s["overall"] for s in scores) / len(scores), 2)
    all_flags = [flag for s in scores for flag in s.get("risk_flags", [])]

    report = {
        "student": profile.get("full_name", "Unknown Student"),
        "interview_type": config.get("interview_type", "Unknown"),
        "overall_score": avg_score,
        "risk_flags": list(dict.fromkeys(all_flags)),
        "response_count": len(responses),
    }

    summary_input = {
        "student": report["student"],
        "interview_type": report["interview_type"],
        "overall_score": report["overall_score"],
        "scores": scores,
        "risk_flags": report["risk_flags"],
    }

    try:
        client = get_openai_client(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an interview coach for international students. "
                        "Write a short, constructive summary and three bullet-point recommendations."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(summary_input),
                },
            ],
            temperature=0.4,
        )
        report["coach_summary"] = resp.choices[0].message.content
    except Exception:
        report["coach_summary"] = "Summary generation failed. Use numeric scores and flags."

    return report