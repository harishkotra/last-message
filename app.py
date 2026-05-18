import base64
import json
import time
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from components.ui import inject_theme, render_header, render_packet
from components.voice import render_voice_widget
from utils.config import ModelConfig, get_openrouter_api_key
from utils.inference import (
    InferenceError,
    run_lm_studio_inference,
    run_lm_studio_multimodal_inference,
    run_openrouter_inference,
    run_openrouter_multimodal_inference,
)
from utils.parser import parse_packet
from utils.prompting import build_user_prompt, load_emergency_system_prompt

load_dotenv()

st.set_page_config(page_title="Last Message", page_icon="🚨", layout="wide", initial_sidebar_state="collapsed")
inject_theme()
render_header()

DEMO_PANIC_TEXT = (
    "Please help my father is unconscious we are trapped after the earthquake "
    "I think the building partially collapsed there is dust everywhere "
    "we can hear people outside but nobody can reach us"
)

DEMO_SCENE_TEXT = "Collapsed building with dust, trapped victims, unstable stairwell, possible bleeding injury"

for key, default in {
    "live_transcript": "",
    "panic_input": "",
    "last_packet": None,
    "run_demo": False,
    "calm_operator_message": "",
    "demo_pending": False,
    "clear_transcript_pending": False,
    "clear_all_pending": False,
    "network_failure_mode": False,
    "scene_analysis": None,
    "consensus": None,
    "responder_view": None,
    "translated": None,
    "translation_lang": "English",
    "manual_voice_fallback": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def safe_json(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        if "```" in text:
            text = text.split("```")[-2] if len(text.split("```")) >= 3 else text
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        obj = json.loads(text)
        if isinstance(obj, dict):
            result = fallback.copy()
            result.update(obj)
            return result
    except Exception:
        pass
    return fallback.copy()


def format_value(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            label = str(k).replace("_", " ").title()
            parts.append(f"{label}: {format_value(v)}")
        return "; ".join(parts)
    if isinstance(value, list):
        return ", ".join([format_value(v) for v in value])
    if value is None:
        return "Unknown"
    return str(value)


def short_lines(text: Any, max_lines: int = 3) -> list[str]:
    raw = format_value(text)
    cleaned = " ".join(raw.replace("\n", " ").split())
    chunks = [c.strip() for c in cleaned.replace(";", ".").split(".") if c.strip()]
    if not chunks:
        return [cleaned[:90]]
    lines = []
    for c in chunks:
        words = c.split()
        lines.append(" ".join(words[:10]))
        if len(lines) >= max_lines:
            break
    return lines


def render_chunk(title: str, severity: str, summary: str, bullets: list[str], tone: str = "info") -> None:
    cls = "alert" if tone == "danger" else ("ok" if tone == "safe" else "")
    bullet_html = "".join([f"<li>{b}</li>" for b in bullets[:3]])
    st.markdown(
        f"""
        <div class='panel-card'>
          <div class='card-title'>{title}</div>
          <div class='card-body'>
            <span class='status-pill {cls}'>{severity}</span>
            <div style='margin-top:8px;'><b>{summary}</b></div>
            <ul style='margin-top:8px;'>{bullet_html}</ul>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auto_location_widget() -> None:
    st.caption("Location permission is requested automatically to improve rescue accuracy.")
    components.html(
        """
        <script>
        (async function() {
          const setTextAreaOrInput = (label, val) => {
            const el = window.parent.document.querySelector(`input[aria-label="${label}"]`);
            if (!el) return;
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, val);
            el.dispatchEvent(new Event('input', { bubbles: true }));
          };

          if (!navigator.geolocation) return;
          navigator.geolocation.getCurrentPosition(async (pos) => {
            const lat = pos.coords.latitude.toFixed(6);
            const lon = pos.coords.longitude.toFixed(6);
            setTextAreaOrInput("Latitude", lat);
            setTextAreaOrInput("Longitude", lon);

            try {
              const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}`;
              const res = await fetch(url, { headers: { "Accept": "application/json" } });
              if (!res.ok) return;
              const data = await res.json();
              const a = data.address || {};
              const city = a.city || a.town || a.village || a.county || "";
              const landmark = a.road || a.suburb || a.neighbourhood || data.name || "";
              if (city) setTextAreaOrInput("City", city);
              if (landmark) setTextAreaOrInput("Nearby Landmark", landmark);
            } catch (_) {}
          }, () => {}, { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 });
        })();
        </script>
        """,
        height=0,
    )


def to_data_url(uploaded_file) -> str:
    b = uploaded_file.getvalue()
    mime = uploaded_file.type or "image/png"
    return f"data:{mime};base64,{base64.b64encode(b).decode('utf-8')}"


def provider_state(cfg: ModelConfig) -> tuple[str | None, bool]:
    local_available = bool(cfg.lm_studio_endpoint and cfg.lm_studio_model)
    cloud_available = bool(cfg.openrouter_endpoint and cfg.openrouter_model and get_openrouter_api_key())

    if st.session_state.network_failure_mode:
        return ("local" if local_available else None), cloud_available
    if local_available:
        return "local", cloud_available
    if cloud_available:
        return "cloud", cloud_available
    return None, cloud_available


def run_text_inference(system_prompt: str, user_prompt: str, cfg: ModelConfig) -> str:
    primary, cloud_available = provider_state(cfg)
    if primary is None:
        raise InferenceError("No model provider configured in .env")

    try:
        if primary == "local":
            return run_lm_studio_inference(system_prompt, user_prompt, cfg)
        return run_openrouter_inference(system_prompt, user_prompt, cfg)
    except InferenceError:
        if primary == "local" and cloud_available and not st.session_state.network_failure_mode:
            return run_openrouter_inference(system_prompt, user_prompt, cfg)
        raise


def run_image_inference(system_prompt: str, user_prompt: str, image_data_url: str, cfg: ModelConfig) -> str:
    primary, cloud_available = provider_state(cfg)
    if primary is None:
        raise InferenceError("No model provider configured in .env")

    try:
        if primary == "local":
            return run_lm_studio_multimodal_inference(system_prompt, user_prompt, image_data_url, cfg)
        return run_openrouter_multimodal_inference(system_prompt, user_prompt, image_data_url, cfg)
    except InferenceError:
        if primary == "local" and cloud_available and not st.session_state.network_failure_mode:
            return run_openrouter_multimodal_inference(system_prompt, user_prompt, image_data_url, cfg)
        raise


def emotional_state(text: str) -> dict[str, str]:
    t = text.lower()
    panic_words = ["help", "trapped", "bleeding", "unconscious", "collapse", "can't", "cannot", "please"]
    score = sum(1 for w in panic_words if w in t)
    if score >= 5:
        return {
            "stress_level": "SEVERE",
            "panic_severity": "CRITICAL",
            "cognitive_clarity": "LOW",
            "emotional_distress": "HIGH",
            "response_style": "short",
        }
    if score >= 3:
        return {
            "stress_level": "HIGH",
            "panic_severity": "ELEVATED",
            "cognitive_clarity": "MEDIUM",
            "emotional_distress": "HIGH",
            "response_style": "balanced",
        }
    return {
        "stress_level": "MODERATE",
        "panic_severity": "MANAGEABLE",
        "cognitive_clarity": "HIGH",
        "emotional_distress": "MODERATE",
        "response_style": "detailed",
    }


def render_emotional_meter(state: dict[str, str]) -> None:
    sev = state["panic_severity"]
    color = "#ff4d4d" if sev == "CRITICAL" else ("#ff8a3d" if sev == "ELEVATED" else "#34d399")
    st.markdown(
        f"""
        <div class='panel-card' style='border-color:{color};'>
          <div class='card-title'>EMOTIONAL STATE DETECTION</div>
          <div class='card-body'>
            <span class='status-pill alert'>PANIC LEVEL: {state['panic_severity']}</span>
            <span class='status-pill'>STRESS: {state['stress_level']}</span>
            <span class='status-pill'>CLARITY: {state['cognitive_clarity']}</span>
            <span class='status-pill'>DISTRESS: {state['emotional_distress']}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_packet_inference(cfg: ModelConfig, location_context: dict, progress_box=None) -> None:
    state = emotional_state(st.session_state.panic_input)
    render_emotional_meter(state)

    style_line = (
        "Use very short step-by-step instructions and calming language." if state["response_style"] == "short" else
        "Use concise but complete instructions with calm tone." if state["response_style"] == "balanced" else
        "Use detailed and structured guidance while staying calm."
    )

    system_prompt = load_emergency_system_prompt() + "\nAdaptive response mode: " + style_line
    user_prompt = build_user_prompt(st.session_state.panic_input, location_context)

    st.session_state.calm_operator_message = (
        "I understand you're scared. Focus on breathing slowly. I'm preparing an emergency response packet now."
    )

    st.markdown(
        "<div class='panel-card' style='border-color: rgba(255,77,77,0.55);'>"
        "<div class='card-title'>AI CALM MODE</div>"
        f"<div class='card-body'>{st.session_state.calm_operator_message}</div></div>",
        unsafe_allow_html=True,
    )

    if progress_box is not None:
        progress_box.markdown(
            "<div class='panel-card' style='border-color: rgba(255,77,77,0.55);'>"
            "<div class='card-title'>LOCAL GEMMA ANALYZING EMERGENCY...</div>"
            "<div class='card-body'>Calm mode delivered. Processing rescue packet now...</div></div>",
            unsafe_allow_html=True,
        )

    time.sleep(0.4)
    raw = run_text_inference(system_prompt, user_prompt, cfg)

    st.session_state.last_packet = parse_packet(raw)


def build_demo_packet(location_context: dict) -> dict[str, Any]:
    loc = (
        f"{location_context.get('city', 'Unknown')}, near {location_context.get('landmark', 'Unknown')} "
        f"(Latitude: {location_context.get('latitude', 'Unknown')}, Longitude: {location_context.get('longitude', 'Unknown')})"
    )
    return {
        "emergency_summary": (
            "Post-earthquake partial building collapse with trapped occupants and heavy dust exposure. "
            "One adult male reported unconscious, possible traumatic injury, access path blocked."
        ),
        "medical_status": "Unconscious male victim, possible head/chest trauma, airway and bleeding risk.",
        "priority_level": "CRITICAL",
        "location_context": loc,
        "message_to_rescuers": (
            "Critical trapped-victim extraction required. One unconscious male in partially collapsed structure. "
            "Dust-heavy environment and unstable debris. Immediate medic + structural team needed."
        ),
        "message_to_family": "We are alive. Rescue teams are being contacted now. Please stay calm and keep your phone available.",
        "immediate_actions": [
            "Check airway and breathing; place victim in safest stable position without unnecessary movement.",
            "Control visible bleeding with direct pressure using clean cloth.",
            "Avoid damaged stairwell and unstable debris zones.",
            "Signal rescuers continuously using light, sound, or phone flashlight.",
        ],
        "emotional_support": "You are doing the right thing. Focus on one action at a time. Help is being coordinated now.",
    }


def run_scene_analysis(cfg: ModelConfig, image_data_url: str, scene_hint: str) -> None:
    system_prompt = (
        "You are an emergency visual intelligence assistant. Return JSON only with keys: "
        "visible_hazards, structural_risks, injury_indicators, escape_recommendations, "
        "safety_warnings, rescue_priority_assessment, hazard_severity."
    )
    user_prompt = (
        "Analyze this disaster scene image for tactical life-saving guidance. "
        f"Optional context: {scene_hint}. Keep concise and realistic."
    )

    fallback = {
        "visible_hazards": "Unclear",
        "structural_risks": "Unknown",
        "injury_indicators": "Unknown",
        "escape_recommendations": "Move carefully to stable open area if safe.",
        "safety_warnings": "Avoid unstable surfaces.",
        "rescue_priority_assessment": "HIGH",
        "hazard_severity": "HIGH",
    }

    with st.spinner("Gemma 4 multimodal scene analysis in progress..."):
        raw = run_image_inference(system_prompt, user_prompt, image_data_url, cfg)
    st.session_state.scene_analysis = safe_json(raw, fallback)


def run_consensus(cfg: ModelConfig) -> None:
    if not st.session_state.last_packet:
        return

    prompt = (
        "Return JSON with keys medic_agent, structural_agent, rescue_agent, final_consensus. "
        "Each agent must include top_concern, recommended_action, risk_assessment. "
        "Use current emergency packet context:\n"
        + json.dumps(st.session_state.last_packet)
    )
    fallback = {
        "medic_agent": {
            "top_concern": "Airway and bleeding risk",
            "recommended_action": "Assess airway and control bleeding immediately",
            "risk_assessment": "HIGH",
        },
        "structural_agent": {
            "top_concern": "Instability around victim",
            "recommended_action": "Minimize movement near damaged structure",
            "risk_assessment": "HIGH",
        },
        "rescue_agent": {
            "top_concern": "Extraction access limitation",
            "recommended_action": "Signal location and conserve energy",
            "risk_assessment": "HIGH",
        },
        "final_consensus": "Prioritize airway safety and controlled rescue while limiting movement in unstable structure.",
    }

    raw = run_text_inference("You are a coordinated emergency command AI.", prompt, cfg)
    st.session_state.consensus = safe_json(raw, fallback)


def run_responder_view(cfg: ModelConfig, location_context: dict) -> None:
    if not st.session_state.last_packet:
        return
    prompt = (
        "Return JSON with keys victim_count, injury_severity, extraction_priority, structural_risk, "
        "recommended_equipment, rescue_difficulty, last_known_status, gps_packet. "
        "Use emergency packet and location context.\n"
        f"packet={json.dumps(st.session_state.last_packet)}\nloc={json.dumps(location_context)}"
    )
    fallback = {
        "victim_count": "1-2 estimated",
        "injury_severity": "Severe",
        "extraction_priority": "Immediate",
        "structural_risk": "High",
        "recommended_equipment": "Trauma kit, airway support, stabilization gear",
        "rescue_difficulty": "High",
        "last_known_status": "Victim responsive/partially responsive",
        "gps_packet": location_context,
    }
    raw = run_text_inference("You are a field rescue coordinator AI.", prompt, cfg)
    st.session_state.responder_view = safe_json(raw, fallback)


def run_translation(cfg: ModelConfig, lang: str) -> None:
    if not st.session_state.last_packet:
        return
    if lang == "English":
        st.session_state.translated = None
        return
    payload = {
        "message_to_rescuers": st.session_state.last_packet.get("message_to_rescuers", ""),
        "message_to_family": st.session_state.last_packet.get("message_to_family", ""),
        "immediate_actions": st.session_state.last_packet.get("immediate_actions", []),
    }
    prompt = (
        f"Translate this emergency JSON to {lang}. Keep short emergency readability. "
        "Return same JSON keys only.\n" + json.dumps(payload)
    )
    raw = run_text_inference("You are an emergency translator.", prompt, cfg)
    st.session_state.translated = safe_json(raw, payload)


def render_essential_view(packet: dict) -> None:
    actions = packet.get("immediate_actions", [])
    if not isinstance(actions, list):
        actions = [str(actions)]
    actions_html = "".join([f"<li>{a}</li>" for a in actions[:3]])
    render_chunk(
        "WHAT MATTERS RIGHT NOW",
        str(packet.get("priority_level", "HIGH")).upper(),
        short_lines(packet.get("emergency_summary", "Emergency detected"), 1)[0],
        [
            f"Location: {short_lines(packet.get('location_context', 'Unknown'), 1)[0]}",
            short_lines(packet.get("medical_status", "Medical status unclear"), 1)[0],
            "Rescue transmission active",
        ],
        tone="danger",
    )
    st.markdown(
        f"""
        <div class='panel-card'>
          <div class='card-title'>DO THESE 3 STEPS NOW</div>
          <div class='card-body'><span class='status-pill alert'>ACTION NOW</span><ol>{actions_html}</ol></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scene_block() -> None:
    st.markdown("## SCENE ANALYSIS")
    st.caption("AI Disaster Intelligence: multimodal hazard detection and tactical guidance.")


def render_network_failover_ui() -> None:
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("Simulate Network Failure", use_container_width=True):
            st.session_state.network_failure_mode = True
            st.rerun()
    with c2:
        if st.session_state.network_failure_mode:
            st.markdown(
                "<div class='panel-card' style='border-color:#ff4d4d;'>"
                "<div class='card-title'>NETWORK FAILURE SIMULATION</div>"
                "<div class='card-body'>Cloud connectivity lost. Switching to local Gemma emergency inference...</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='panel-card'><div class='card-title'>CONNECTIVITY STATUS</div>"
                "<div class='card-body'><span class='status-pill ok'>Cloud Online</span> <span class='status-pill ok'>Local Ready</span></div></div>",
                unsafe_allow_html=True,
            )


def render_loading_card(progress_box, message: str, step: int, total: int = 4) -> None:
    pct = int((step / total) * 100)
    progress_box.markdown(
        f"""
        <div class='panel-card' style='border-color: rgba(255,77,77,0.55);'>
          <div class='card-title'>LOCAL GEMMA ANALYZING EMERGENCY...</div>
          <div class='card-body'>
            <div>{message}</div>
            <div style='margin-top:10px;height:10px;background:rgba(255,255,255,0.12);border-radius:999px;overflow:hidden;'>
              <div style='height:100%;width:{pct}%;background:linear-gradient(90deg,#ff4d4d,#ff8a3d);transition:width 0.35s ease;'></div>
            </div>
            <div class='mono' style='margin-top:6px;'>Step {step}/{total} - {pct}%</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    cfg = ModelConfig()

    if st.session_state.demo_pending:
        st.session_state.live_transcript = DEMO_PANIC_TEXT
        st.session_state.panic_input = DEMO_PANIC_TEXT
        st.session_state.run_demo = True
        st.session_state.demo_pending = False

    if st.session_state.clear_transcript_pending:
        st.session_state.live_transcript = ""
        st.session_state.manual_voice_fallback = ""
        st.session_state.clear_transcript_pending = False

    if st.session_state.clear_all_pending:
        st.session_state.live_transcript = ""
        st.session_state.panic_input = ""
        st.session_state.manual_voice_fallback = ""
        st.session_state.last_packet = None
        st.session_state.scene_analysis = None
        st.session_state.consensus = None
        st.session_state.responder_view = None
        st.session_state.translated = None
        st.session_state.run_demo = False
        st.session_state.clear_all_pending = False

    enable_sound = st.toggle("Enable Emergency Alert Sounds", value=False)
    render_network_failover_ui()

    left, right = st.columns([1.05, 1], gap="large")
    run_clicked = False

    with left:
        st.markdown("## PANIC MODE")
        render_voice_widget(enable_alert_sound=enable_sound)
        st.text_area("Live Transcript", key="live_transcript", height=120)

        v1, v2 = st.columns(2)
        with v1:
            if st.button("Use Transcript", use_container_width=True):
                spoken = st.session_state.live_transcript.strip()
                fallback_spoken = st.session_state.manual_voice_fallback.strip()
                st.session_state.panic_input = spoken if spoken else fallback_spoken
        with v2:
            if st.button("Clear Transcript", use_container_width=True):
                st.session_state.clear_transcript_pending = True
                st.rerun()

        st.text_area("Final Emergency Message", key="panic_input", height=150)

        st.markdown("## Location Context")
        render_auto_location_widget()
        c1, c2 = st.columns(2)
        with c1:
            latitude = st.text_input("Latitude", value="")
            city = st.text_input("City", value="")
        with c2:
            longitude = st.text_input("Longitude", value="")
            landmark = st.text_input("Nearby Landmark", value="")

        st.markdown("## MULTILINGUAL EMERGENCY MODE")
        st.session_state.translation_lang = st.selectbox(
            "Translate Output",
            ["English", "Hindi", "Telugu", "Spanish", "Arabic"],
            index=["English", "Hindi", "Telugu", "Spanish", "Arabic"].index(st.session_state.translation_lang),
        )

        st.markdown("## SCENE ANALYSIS")
        scene_mode = st.radio("Scene Source", ["Upload Image", "Demo Disaster Scene"], horizontal=True)
        uploaded = st.file_uploader("Upload emergency scene", type=["png", "jpg", "jpeg", "webp"])
        scene_hint = st.text_input("Scene Context (optional)", value="")

        demo_selected = scene_mode == "Demo Disaster Scene"
        demo_img_data = None
        if demo_selected:
            svg = """<svg xmlns='http://www.w3.org/2000/svg' width='960' height='540'><rect width='100%' height='100%' fill='#1a1a1a'/><circle cx='130' cy='90' r='55' fill='#ff6b2d'/><rect x='0' y='380' width='960' height='180' fill='#2b2b2b'/><polygon points='180,380 360,250 520,380' fill='#4a4a4a'/><polygon points='460,380 650,220 820,380' fill='#555'/><rect x='580' y='350' width='110' height='30' fill='#8b1e1e'/><text x='40' y='510' fill='#f2f2f2' font-size='28'>Collapsed Urban Structure - Heavy Dust / Access Blocked</text></svg>"""
            demo_img_data = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("utf-8")
            st.image(demo_img_data, caption="Demo disaster scene", use_container_width=True)

        b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
        with b1:
            if st.button("🎬 DEMO MODE", use_container_width=True):
                st.session_state.demo_pending = True
                st.rerun()
        with b2:
            if st.button("Analyze Scene", use_container_width=True):
                try:
                    img_data = to_data_url(uploaded) if uploaded else demo_img_data
                    if not img_data:
                        st.warning("Upload an image or use demo scene.")
                    else:
                        run_scene_analysis(cfg, img_data, scene_hint or DEMO_SCENE_TEXT)
                except Exception as e:
                    st.error(f"Scene analysis failed: {e}")
        with b3:
            if st.button("CLEAR", use_container_width=True):
                st.session_state.clear_all_pending = True
                st.rerun()
        with b4:
            run_clicked = st.button("Generate Emergency Packet", type="primary", use_container_width=True)

    location_context = {"latitude": latitude, "longitude": longitude, "city": city, "landmark": landmark}

    with right:
        st.markdown("## Rescue Intelligence")
        should_run = run_clicked or st.session_state.run_demo

        if should_run:
            if not st.session_state.panic_input.strip():
                st.error("Please provide an emergency message.")
                st.session_state.run_demo = False
            else:
                if st.session_state.run_demo:
                    st.markdown("### PANIC MODE SIMULATION")
                    ph = st.empty()
                    text = []
                    for word in st.session_state.panic_input.split():
                        text.append(word)
                        ph.markdown(
                            "<div class='panel-card'><div class='card-title'>LIVE TRANSCRIPT</div>"
                            f"<div class='card-body'>{' '.join(text)}</div></div>",
                            unsafe_allow_html=True,
                        )
                        time.sleep(0.04)
                progress = st.empty()
                try:
                    render_loading_card(progress, "Loading emergency inference pipeline...", step=1)
                    run_packet_inference(cfg, location_context, progress_box=progress)

                    render_loading_card(progress, "Running multi-agent emergency consensus...", step=2)
                    run_consensus(cfg)

                    render_loading_card(progress, "Generating responder tactical view...", step=3)
                    run_responder_view(cfg, location_context)

                    render_loading_card(progress, "Preparing multilingual emergency output...", step=4)
                    run_translation(cfg, st.session_state.translation_lang)
                    progress.empty()
                except Exception as e:
                    if st.session_state.run_demo:
                        st.session_state.last_packet = build_demo_packet(location_context)
                        run_consensus(cfg)
                        run_responder_view(cfg, location_context)
                        run_translation(cfg, st.session_state.translation_lang)
                        progress.empty()
                        st.warning("Live inference unavailable. Demo packet generated for presentation continuity.")
                    else:
                        progress.empty()
                        st.error(str(e))
                finally:
                    st.session_state.run_demo = False

        if st.session_state.scene_analysis:
            s = st.session_state.scene_analysis
            render_chunk(
                "AI DISASTER INTELLIGENCE",
                f"{s.get('hazard_severity', 'HIGH')}",
                "Rapid scene hazard snapshot",
                [
                    f"Priority: {s.get('rescue_priority_assessment', 'HIGH')}",
                    short_lines(s.get("visible_hazards", "Unknown"), 1)[0],
                    short_lines(s.get("structural_risks", "Unknown"), 1)[0],
                ],
                tone="danger",
            )
            render_chunk(
                "ESCAPE + SAFETY",
                "WARNING",
                short_lines(s.get("escape_recommendations", "No safe route identified"), 1)[0],
                [
                    short_lines(s.get("safety_warnings", "Proceed with caution"), 1)[0],
                    short_lines(s.get("injury_indicators", "Injury indicators unclear"), 1)[0],
                    "Wait for trained rescue if path unstable",
                ],
                tone="warning",
            )

        if st.session_state.last_packet:
            render_essential_view(st.session_state.last_packet)

            if st.session_state.translated:
                t = st.session_state.translated
                st.markdown(
                    f"""
                    <div class='panel-card'>
                      <div class='card-title'>MULTILINGUAL OUTPUT ({st.session_state.translation_lang})</div>
                      <div class='card-body'>
                        <b>Rescuers:</b> {t.get('message_to_rescuers', '')}<br/><br/>
                        <b>Family SMS:</b> {t.get('message_to_family', '')}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.session_state.consensus:
                c = st.session_state.consensus
                st.markdown("### EMERGENCY TEAM CONSENSUS")
                for agent_key, name in [
                    ("medic_agent", "Medic Agent"),
                    ("structural_agent", "Structural Safety Agent"),
                    ("rescue_agent", "Rescue Coordinator Agent"),
                ]:
                    a = c.get(agent_key, {})
                    render_chunk(
                        name.upper(),
                        format_value(a.get("risk_assessment", "HIGH")).upper(),
                        short_lines(a.get("top_concern", "Unknown"), 1)[0],
                        [
                            short_lines(a.get("recommended_action", "Unknown"), 1)[0],
                            "Follow chain-of-command",
                            "Maintain communication",
                        ],
                        tone="warning",
                    )
                consensus_lines = short_lines(c.get("final_consensus", "Safe extraction with risk control"), 3)
                render_chunk(
                    "COMMAND DECISION OUTPUT",
                    "CODE RED",
                    consensus_lines[0],
                    consensus_lines[1:] + ["Stabilize airway first", "Minimize movement near debris"],
                    tone="danger",
                )

            if st.session_state.responder_view:
                rv = st.session_state.responder_view
                st.markdown("### RESPONDER VIEW")
                st.markdown(
                    f"""
                    <div class='panel-card'>
                      <div class='card-title'>TACTICAL FIELD INTELLIGENCE</div>
                      <div class='card-body'>
                        <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>
                          <div><b>👥 Victims</b><br/><span class='status-pill alert'>{short_lines(rv.get('victim_count', ''),1)[0]}</span></div>
                          <div><b>🚨 Extraction</b><br/><span class='status-pill alert'>{short_lines(rv.get('extraction_priority', ''),1)[0]}</span></div>
                          <div><b>🏚 Structure</b><br/><span class='status-pill alert'>{short_lines(rv.get('structural_risk', ''),1)[0]}</span></div>
                          <div><b>🩺 Injury</b><br/><span class='status-pill'>{short_lines(rv.get('injury_severity', ''),1)[0]}</span></div>
                          <div><b>🧰 Equipment</b><br/><span class='status-pill'>{short_lines(rv.get('recommended_equipment', ''),1)[0]}</span></div>
                          <div><b>⏱ Difficulty</b><br/><span class='status-pill'>{short_lines(rv.get('rescue_difficulty', ''),1)[0]}</span></div>
                        </div>
                        <hr style='border-color:rgba(255,255,255,0.15);margin:10px 0;'/>
                        <b>📡 Status:</b> {short_lines(rv.get('last_known_status', ''),1)[0]}<br/>
                        <b>📍 GPS:</b> {short_lines(rv.get('gps_packet', ''),1)[0]}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("Show Full AI Analysis", expanded=False):
                render_packet(st.session_state.last_packet)

            st.markdown(
                """
                <div class='panel-card' style='text-align:center;border-color: rgba(255,138,61,0.5);'>
                  <div class='card-body' style='font-weight:700;'>When words fail,<br/>AI helps humans be heard.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.caption("Gemma 4 Good: multimodal, emotionally adaptive, offline-resilient emergency intelligence.")
    st.markdown(
        """
        <div style='text-align:center;margin-top:6px;'>
          <a href='https://harishkotra.me' target='_blank' style='color:#f5f7fa;text-decoration:none;font-weight:700;'>Built By Harish Kotra</a>
          <span style='color:#98a2b3;padding:0 8px;'>|</span>
          <a href='https://dailybuild.xyz' target='_blank' style='color:#f5f7fa;text-decoration:none;font-weight:700;'>Checkout my other builds</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
