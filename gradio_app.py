import time
import json
import gradio as gr
import pandas as pd

from services.question_engine import generate_questions
from services.scoring_engine import score_response
from services.report_engine import build_final_report
from services.model_answer_engine import generate_model_answer
from services.storage import save_session


def build_app():
    with gr.Blocks() as demo:
        gr.Markdown("# PrimeCrown Interview Prep (Gradio)")

        # Shared session state across tabs (per user session)[web:78]
        student_profile_state = gr.State({})
        interview_config_state = gr.State({})
        questions_state = gr.State([])
        current_q_index_state = gr.State(0)
        responses_state = gr.State([])
        scores_state = gr.State([])
        risk_flags_state = gr.State([])
        final_report_state = gr.State(None)
        counselor_review_state = gr.State({})

        with gr.Tabs():
            # ----------------- 1. Student Intake -----------------
            with gr.Tab("Student Intake"):
                gr.Markdown("### Student Intake")

                full_name = gr.Textbox(label="Full name")
                home_country = gr.Textbox(label="Home country", value="Nigeria")
                target_university = gr.Textbox(label="Target university")
                target_course = gr.Textbox(label="Target course")
                academic_background = gr.Textbox(
                    label="Academic background", lines=4
                )
                english_level = gr.Dropdown(
                    ["High", "Medium", "Needs support"],
                    label="English confidence",
                    value="High",
                )
                previous_issues = gr.Textbox(
                    label="Previous interview or visa issues",
                    lines=3,
                )

                save_profile_btn = gr.Button("Save profile")
                profile_status = gr.Textbox(
                    label="Status",
                    interactive=False,
                )
                profile_json = gr.JSON(label="Current profile", value={})

                def save_profile(
                    full_name,
                    home_country,
                    target_university,
                    target_course,
                    academic_background,
                    english_level,
                    previous_issues,
                    current_profile,
                ):
                    profile = {
                        "full_name": full_name,
                        "home_country": home_country,
                        "target_university": target_university,
                        "target_course": target_course,
                        "academic_background": academic_background,
                        "english_level": english_level,
                        "previous_issues": previous_issues,
                    }
                    status = "Student profile saved."
                    return status, profile, profile

                save_profile_btn.click(
                    fn=save_profile,
                    inputs=[
                        full_name,
                        home_country,
                        target_university,
                        target_course,
                        academic_background,
                        english_level,
                        previous_issues,
                        student_profile_state,
                    ],
                    outputs=[profile_status, student_profile_state, profile_json],
                )

            # ----------------- 2. Interview Setup -----------------
            with gr.Tab("Interview Setup"):
                gr.Markdown("### Interview Setup")

                profile_preview = gr.JSON(label="Loaded profile")

                def preview_profile(profile):
                    return profile

                student_profile_state.change(
                    fn=preview_profile,
                    inputs=student_profile_state,
                    outputs=profile_preview,
                )

                interview_type = gr.Dropdown(
                    ["Admissions", "UKVI / Credibility", "Scholarship"],
                    label="Interview type",
                    value="UKVI / Credibility",
                )
                difficulty = gr.Dropdown(
                    ["Easy", "Standard", "Strict"],
                    label="Difficulty",
                    value="Standard",
                )
                session_length = gr.Dropdown(
                    ["15 min", "30 min", "50 min"],
                    label="Session length",
                    value="30 min",
                )
                followups = gr.Checkbox(
                    label="Enable follow-up probing",
                    value=True,
                )

                generate_btn = gr.Button("Generate interview")
                setup_status = gr.Textbox(
                    label="Status",
                    interactive=False,
                )
                questions_markdown = gr.Markdown("No questions yet.")

                def generate_interview(
                    profile,
                    interview_type,
                    difficulty,
                    session_length,
                    followups,
                ):
                    if not profile or not profile.get("full_name"):
                        return (
                            "Complete Student Intake first.",
                            {},
                            [],
                            0,
                            [],
                            [],
                            [],
                            "No questions.",
                        )

                    config = {
                        "interview_type": interview_type,
                        "difficulty": difficulty,
                        "session_length": session_length,
                        "followups": followups,
                    }
                    questions = generate_questions(profile, config)
                    status = f"Generated {len(questions)} questions."
                    md = "\n\n".join(
                        [f"{q['id']}. {q['question']}" for q in questions]
                    )

                    # reset interview-related state
                    return (
                        status,
                        config,
                        questions,
                        0,   # current_q_index
                        [],  # responses
                        [],  # scores
                        [],  # risk_flags
                        md,
                    )

                generate_btn.click(
                    fn=generate_interview,
                    inputs=[
                        student_profile_state,
                        interview_type,
                        difficulty,
                        session_length,
                        followups,
                    ],
                    outputs=[
                        setup_status,
                        interview_config_state,
                        questions_state,
                        current_q_index_state,
                        responses_state,
                        scores_state,
                        risk_flags_state,
                        questions_markdown,
                    ],
                )

            # ----------------- 3. Live Interview -----------------
            with gr.Tab("Live Interview"):
                gr.Markdown("### Live Interview")

                current_q_box = gr.Markdown(
                    "No question yet. Generate interview first."
                )
                progress_box = gr.Textbox(
                    label="Progress",
                    interactive=False,
                )

                def show_current_question(questions, idx):
                    if not questions:
                        return "No questions. Please generate interview.", "0 / 0"
                    if idx >= len(questions):
                        return (
                            "Interview completed.",
                            f"{len(questions)} / {len(questions)}",
                        )
                    q = questions[idx]
                    return (
                        f"Question {idx + 1} of {len(questions)}:\n\n{q['question']}",
                        f"{idx} / {len(questions)}",
                    )

                questions_state.change(
                    fn=show_current_question,
                    inputs=[questions_state, current_q_index_state],
                    outputs=[current_q_box, progress_box],
                )
                current_q_index_state.change(
                    fn=show_current_question,
                    inputs=[questions_state, current_q_index_state],
                    outputs=[current_q_box, progress_box],
                )

                with gr.Row():
                    timer_input = gr.Number(
                        value=60,
                        label="Answer time (seconds)",
                        precision=0,
                    )
                    timer_text = gr.Textbox(
                        label="Timer",
                        interactive=False,
                    )
                    start_timer_btn = gr.Button("Start Timer")

                def countdown(seconds):
                    seconds = int(seconds)
                    for remaining in range(seconds, -1, -1):
                        if remaining == 0:
                            yield "Time is up!"
                        else:
                            yield f"{remaining} sec left"
                        time.sleep(1)

                start_timer_btn.click(
                    fn=countdown,
                    inputs=timer_input,
                    outputs=timer_text,
                )

                audio_comp = gr.Audio(
                    source="microphone",
                    type="filepath",
                    label="Record your answer",
                )
                text_answer = gr.Textbox(
                    label="Or type your answer",
                    lines=6,
                )
                submit_btn = gr.Button("Submit answer")
                skip_btn = gr.Button("Skip question")
                live_status = gr.Textbox(
                    label="Status",
                    interactive=False,
                )

                def submit_answer(
                    audio_path,
                    text_answer,
                    questions,
                    idx,
                    responses,
                    scores,
                    risk_flags,
                ):
                    if not questions:
                        return (
                            "No questions available.",
                            questions,
                            idx,
                            responses,
                            scores,
                            risk_flags,
                        )
                    if idx >= len(questions):
                        return (
                            "Interview already completed.",
                            questions,
                            idx,
                            responses,
                            scores,
                            risk_flags,
                        )

                    q = questions[idx]
                    answer = text_answer or ""
                    score = score_response(q, answer)

                    responses.append({
                        "question_id": q["id"],
                        "question": q["question"],
                        "answer": answer,
                        "audio_path": audio_path,
                    })
                    scores.append(score)
                    risk_flags.extend(score.get("risk_flags", []))

                    idx += 1
                    if idx >= len(questions):
                        status = (
                            f"Recorded answer and score for Q{q['id']}. "
                            "Interview completed."
                        )
                    else:
                        status = f"Recorded answer and score for Q{q['id']}."

                    return (
                        status,
                        questions,
                        idx,
                        responses,
                        scores,
                        risk_flags,
                    )

                submit_btn.click(
                    fn=submit_answer,
                    inputs=[
                        audio_comp,
                        text_answer,
                        questions_state,
                        current_q_index_state,
                        responses_state,
                        scores_state,
                        risk_flags_state,
                    ],
                    outputs=[
                        live_status,
                        questions_state,
                        current_q_index_state,
                        responses_state,
                        scores_state,
                        risk_flags_state,
                    ],
                )

                def skip_question(
                    questions,
                    idx,
                    responses,
                    scores,
                    risk_flags,
                ):
                    if not questions:
                        return (
                            "No questions available.",
                            questions,
                            idx,
                            responses,
                            scores,
                            risk_flags,
                        )
                    if idx >= len(questions):
                        return (
                            "Interview already completed.",
                            questions,
                            idx,
                            responses,
                            scores,
                            risk_flags,
                        )

                    q = questions[idx]
                    responses.append({
                        "question_id": q["id"],
                        "question": q["question"],
                        "answer": "",
                        "audio_path": None,
                    })
                    scores.append(score_response(q, ""))

                    idx += 1
                    if idx >= len(questions):
                        status = f"Skipped Q{q['id']}. Interview completed."
                    else:
                        status = f"Skipped Q{q['id']}."

                    return (
                        status,
                        questions,
                        idx,
                        responses,
                        scores,
                        risk_flags,
                    )

                skip_btn.click(
                    fn=skip_question,
                    inputs=[
                        questions_state,
                        current_q_index_state,
                        responses_state,
                        scores_state,
                        risk_flags_state,
                    ],
                    outputs=[
                        live_status,
                        questions_state,
                        current_q_index_state,
                        responses_state,
                        scores_state,
                        risk_flags_state,
                    ],
                )

            # ----------------- 4. Feedback Report -----------------
            with gr.Tab("Feedback Report"):
                gr.Markdown("### Feedback Report")

                overall_metric = gr.Textbox(
                    label="Overall score",
                    interactive=False,
                )
                basic_info = gr.Markdown("")
                coach_summary_box = gr.Markdown("")
                risk_flags_box = gr.Markdown("")
                scores_df = gr.Dataframe(
                    interactive=False,
                )
                bar_plot = gr.BarPlot(
                    label="Scores by question",
                    x="question_id",
                    y="overall",
                )

                build_btn = gr.Button("Refresh report")
                save_export_btn = gr.Button("Save session export")
                export_status = gr.Textbox(label="Export status", interactive=False)

                def build_feedback(
                    profile,
                    config,
                    questions,
                    responses,
                    scores,
                ):
                    if not responses or not scores:
                        return (
                            "",
                            "No completed responses yet.",
                            "No summary.",
                            "No flags.",
                            pd.DataFrame([]),
                            pd.DataFrame({"question_id": [], "overall": []}),
                            None,
                        )

                    report = build_final_report(
                        profile, config, questions, responses, scores
                    )
                    df = pd.DataFrame(scores)

                    if "overall" in df.columns and "question_id" in df.columns:
                        bar_data = df[["question_id", "overall"]]
                    else:
                        bar_data = pd.DataFrame({"question_id": [], "overall": []})

                    flags_md = "\n".join(
                        [
                            f"- {f}"
                            for f in (
                                report.get("risk_flags")
                                or ["No major flags detected."]
                            )
                        ]
                    )
                    info_md = (
                        f"**Student:** {report['student']}  \n"
                        f"**Interview type:** {report['interview_type']}"
                    )

                    return (
                        str(report["overall_score"]),
                        info_md,
                        report.get("coach_summary", "No summary."),
                        flags_md,
                        df,
                        bar_data,
                        report,
                    )

                build_btn.click(
                    fn=build_feedback,
                    inputs=[
                        student_profile_state,
                        interview_config_state,
                        questions_state,
                        responses_state,
                        scores_state,
                    ],
                    outputs=[
                        overall_metric,
                        basic_info,
                        coach_summary_box,
                        risk_flags_box,
                        scores_df,
                        bar_plot,
                        final_report_state,
                    ],
                )

                def export_session(
                    profile,
                    config,
                    responses,
                    scores,
                    report,
                ):
                    if not report:
                        return "No report to export yet."
                    payload = {
                        "profile": profile,
                        "config": config,
                        "responses": responses,
                        "scores": scores,
                        "report": report,
                    }
                    save_session(payload)
                    return "Session exported to data/session_exports.json"

                save_export_btn.click(
                    fn=export_session,
                    inputs=[
                        student_profile_state,
                        interview_config_state,
                        responses_state,
                        scores_state,
                        final_report_state,
                    ],
                    outputs=export_status,
                )

            # ----------------- 5. Counselor Review -----------------
            with gr.Tab("Counselor Review"):
                gr.Markdown("### Counselor Review")

                readiness = gr.Dropdown(
                    ["Ready", "Needs another practice"],
                    label="Readiness decision",
                )
                credibility_risk = gr.Dropdown(
                    ["Low", "Medium", "High"],
                    label="Credibility risk",
                )
                language_support = gr.Dropdown(
                    ["Low", "Medium", "High"],
                    label="Language support need",
                )
                notes = gr.Textbox(
                    label="Counselor notes",
                    lines=4,
                )

                save_review_btn = gr.Button("Save review")
                review_status = gr.Textbox(
                    label="Status",
                    interactive=False,
                )
                review_json = gr.JSON(label="Current review")

                def save_review(
                    readiness,
                    credibility_risk,
                    language_support,
                    notes,
                ):
                    review = {
                        "readiness": readiness,
                        "credibility_risk": credibility_risk,
                        "language_support": language_support,
                        "notes": notes,
                    }
                    return "Counselor review saved.", review, review

                save_review_btn.click(
                    fn=save_review,
                    inputs=[readiness, credibility_risk, language_support, notes],
                    outputs=[review_status, counselor_review_state, review_json],
                )

                gr.Markdown("#### Model answers for counselor reference")

                question_selector = gr.Dropdown(
                    label="Select question",
                    choices=[],
                )
                model_answer_box = gr.Markdown("")
                generate_model_btn = gr.Button("Generate model answer")

                def update_question_choices(questions):
                    if not questions:
                        return []
                    return [
                        f"Q{q['id']} – {q['question'][:60]}..."
                        for q in questions
                    ]

                questions_state.change(
                    fn=update_question_choices,
                    inputs=questions_state,
                    outputs=question_selector,
                )

                def gen_model_answer(
                    selected_label,
                    questions,
                    responses,
                    profile,
                ):
                    if not selected_label or not questions:
                        return "No question selected."
                    label_map = {
                        f"Q{q['id']} – {q['question'][:60]}...": q
                        for q in questions
                    }
                    q = label_map[selected_label]
                    answer_dict = next(
                        (r for r in responses if r["question_id"] == q["id"]),
                        None,
                    )
                    student_answer = (
                        answer_dict["answer"] if answer_dict else ""
                    )
                    text = generate_model_answer(
                        profile, q, student_answer=student_answer
                    )
                    return f"**AI model answer example:**\n\n{text}"

                generate_model_btn.click(
                    fn=gen_model_answer,
                    inputs=[
                        question_selector,
                        questions_state,
                        responses_state,
                        student_profile_state,
                    ],
                    outputs=model_answer_box,
                )

            # ----------------- 6. Admin Analytics -----------------
            with gr.Tab("Admin Analytics"):
                gr.Markdown("### Admin Analytics")

                responses_metric = gr.Textbox(
                    label="Responses", interactive=False
                )
                scores_metric = gr.Textbox(
                    label="Scores logged", interactive=False
                )
                readiness_metric = gr.Textbox(
                    label="Readiness", interactive=False
                )
                scores_by_section_df = gr.Dataframe(interactive=False)
                overall_line = gr.LinePlot(
                    label="Overall score trend",
                    x="index",
                    y="overall",
                )

                refresh_analytics_btn = gr.Button("Refresh analytics")

                def analytics(
                    scores,
                    responses,
                    review,
                ):
                    resp_count = len(responses or [])
                    score_count = len(scores or [])
                    readiness = review.get("readiness", "N/A") if review else "N/A"

                    if scores:
                        df = pd.DataFrame(scores)
                        if "section" in df.columns:
                            cols = [
                                c
                                for c in [
                                    "relevance",
                                    "structure",
                                    "clarity",
                                    "confidence",
                                    "overall",
                                ]
                                if c in df.columns
                            ]
                            grouped = df.groupby("section")[cols].mean()
                        else:
                            grouped = pd.DataFrame([])
                        if "overall" in df.columns:
                            line_data = pd.DataFrame(
                                {
                                    "index": range(len(df)),
                                    "overall": df["overall"],
                                }
                            )
                        else:
                            line_data = pd.DataFrame(
                                {"index": [], "overall": []}
                            )
                    else:
                        grouped = pd.DataFrame([])
                        line_data = pd.DataFrame(
                            {"index": [], "overall": []}
                        )

                    return (
                        str(resp_count),
                        str(score_count),
                        readiness,
                        grouped,
                        line_data,
                    )

                refresh_analytics_btn.click(
                    fn=analytics,
                    inputs=[
                        scores_state,
                        responses_state,
                        counselor_review_state,
                    ],
                    outputs=[
                        responses_metric,
                        scores_metric,
                        readiness_metric,
                        scores_by_section_df,
                        overall_line,
                    ],
                )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.queue().launch()