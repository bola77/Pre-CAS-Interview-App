# services/state_manager.py (core, UI-agnostic)

DEFAULTS = {
    "student_profile": {},
    "interview_config": {},
    "questions": [],
    "current_q_index": 0,
    "responses": [],
    "scores": [],
    "risk_flags": [],
    "final_report": None,
    "session_started": False,
    "session_completed": False,
    "counselor_review": {},
    "analytics_events": [],
}

def new_session_state():
    """
    Returns a fresh, independent session dict.
    Safe to use in Streamlit, Gradio, FastAPI, or tests.
    """
    state = {}
    for key, value in DEFAULTS.items():
        if isinstance(value, dict):
            state[key] = value.copy()
        elif isinstance(value, list):
            state[key] = list(value)
        else:
            state[key] = value
    return state

def reset_interview(state: dict):
    """
    Resets interview-specific keys on a given state dict,
    preserving student_profile.
    """
    keep_profile = state.get("student_profile", {}).copy()
    for key, value in DEFAULTS.items():
        if isinstance(value, dict):
            state[key] = value.copy()
        elif isinstance(value, list):
            state[key] = list(value)
        else:
            state[key] = value
    state["student_profile"] = keep_profile
    return state