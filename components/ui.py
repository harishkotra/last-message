import streamlit as st


def _short_lines(text: str, max_lines: int = 3) -> list[str]:
    if not text:
        return ["Unknown"]
    cleaned = " ".join(str(text).replace("\n", " ").split())
    parts = [p.strip() for p in cleaned.replace(";", ".").split(".") if p.strip()]
    if not parts:
        return [cleaned[:90]]
    lines = []
    for p in parts:
        words = p.split()
        lines.append(" ".join(words[:10]))
        if len(lines) >= max_lines:
            break
    return lines


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

        :root {
            --bg: #0b0d10;
            --panel: #12161c;
            --soft: #1a2028;
            --text: #f5f7fa;
            --muted: #98a2b3;
            --alert: #ff4d4d;
            --warm: #ff8a3d;
            --ok: #34d399;
        }

        .stApp {
            background: radial-gradient(circle at 20% 10%, rgba(255,77,77,0.20), transparent 25%),
                        radial-gradient(circle at 80% 30%, rgba(255,138,61,0.20), transparent 30%),
                        linear-gradient(180deg, #080a0d 0%, #10141a 100%);
            color: var(--text);
            font-family: 'Space Grotesk', sans-serif;
        }

        .app-title {font-size: 3rem; font-weight: 700; letter-spacing: 0.03em; margin-bottom: 0.2rem;}
        .tagline {color: var(--muted); font-size: 1.1rem; margin-bottom: 1rem;}
        .status-row {display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1rem;}
        .status-pill {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 999px;
            padding: 0.35rem 0.8rem;
            font-size: 0.82rem;
            color: #e5e7eb;
        }
        .status-pill.ok {border-color: rgba(52,211,153,0.5); color: #9ff3d2;}
        .status-pill.alert {border-color: rgba(255,77,77,0.65); color: #ffc4c4;}

        .emergency-pulse {
            width: 14px;
            height: 14px;
            border-radius: 999px;
            background: var(--alert);
            display: inline-block;
            margin-right: 8px;
            box-shadow: 0 0 0 rgba(255,77,77,0.4);
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% {box-shadow: 0 0 0 0 rgba(255,77,77,0.55);}
            70% {box-shadow: 0 0 0 14px rgba(255,77,77,0);}
            100% {box-shadow: 0 0 0 0 rgba(255,77,77,0);}
        }

        .panel-card {
            background: linear-gradient(180deg, rgba(22,27,35,0.95), rgba(17,21,27,0.92));
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 16px;
            padding: 1rem;
            margin-bottom: 0.8rem;
            box-shadow: 0 6px 30px rgba(0,0,0,0.32);
            animation: fadeInUp 0.5s ease both;
        }

        .card-title {font-weight: 800; font-size: 1.02rem; color: #ffd8bf; margin-bottom: 0.45rem; text-transform: uppercase; letter-spacing: 0.04em;}
        .card-body {font-size: 1.04rem; line-height: 1.75; color: #f7f7f7;}

        .mono {font-family: 'IBM Plex Mono', monospace; color: #c9d3e0; font-size: 0.9rem;}

        .stTextArea textarea, .stTextInput input {
            background: rgba(255,255,255,0.05) !important;
            border: 1px solid rgba(255,255,255,0.25) !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            font-size: 1.05rem !important;
        }

        .stButton > button {
            min-height: 52px;
            font-weight: 700;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.28);
        }

        .st-emotion-cache-16idsys p, .stMarkdown p {
            line-height: 1.55;
        }

        @keyframes fadeInUp {
            from {opacity: 0; transform: translateY(8px);}
            to {opacity: 1; transform: translateY(0);}
        }

        @media (max-width: 900px) {
            .app-title {font-size: 2.2rem;}
            .tagline {font-size: 1rem;}
            .status-row {gap: 0.45rem;}
            .status-pill {font-size: 0.74rem; padding: 0.3rem 0.6rem;}
            .panel-card {padding: 0.85rem; border-radius: 14px;}
            .card-body {font-size: 1.02rem;}
            .stButton > button {width: 100%;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class='app-title'><span class='emergency-pulse'></span>Last Message</div>
        <div class='tagline'>AI-powered emergency communication when panic takes over.</div>
        <div class='status-row'>
          <div class='status-pill ok'>Offline Ready</div>
          <div class='status-pill alert'>Powered by Gemma 4</div>
          <div class='status-pill ok'>Local AI Active</div>
          <div class='status-pill'>Mesh Relay Ready</div>
          <div class='status-pill'>Low Connectivity Mode</div>
          <div class='status-pill'>Battery Safe Mode</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_packet(packet: dict) -> None:
    def card(title: str, body: str, severity: str = "INFO") -> None:
        lines = _short_lines(body, max_lines=3)
        bullets = "".join([f"<li>{ln}</li>" for ln in lines])
        sev_class = "alert" if severity in {"CRITICAL", "HIGH"} else ("ok" if severity in {"LOW", "SAFE"} else "")
        st.markdown(
            f"""
            <div class='panel-card'>
              <div class='card-title'>{title}</div>
              <div class='card-body'>
                <span class='status-pill {sev_class}'>{severity}</span>
                <ul>{bullets}</ul>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    priority = str(packet.get("priority_level", "HIGH")).upper()
    card("Emergency Summary", packet.get("emergency_summary", "Unknown"), severity=priority)
    card("Medical Status", packet.get("medical_status", "Unknown"), severity=priority)
    card("Rescue Priority Level", packet.get("priority_level", "Unknown"), severity=priority)
    card("GPS / Context Packet", packet.get("location_context", "Unknown"), severity="INFO")
    card("Message to Rescuers", packet.get("message_to_rescuers", "Unknown"), severity=priority)
    card("Message to Family", packet.get("message_to_family", "Unknown"), severity="INFO")

    immediate_actions = packet.get("immediate_actions", [])
    if isinstance(immediate_actions, list):
        action_html = "".join([f"<li>{a}</li>" for a in immediate_actions])
    else:
        action_html = f"<li>{immediate_actions}</li>"

    st.markdown(
        f"""
        <div class='panel-card'>
          <div class='card-title'>Immediate Survival Steps</div>
          <div class='card-body'><span class='status-pill alert'>ACTION NOW</span><ol>{action_html}</ol></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    card("Emotional Reassurance", packet.get("emotional_support", "Unknown"), severity="SAFE")
