import json
import re
from typing import Any, Dict


DEFAULT_PACKET = {
    "emergency_summary": "Unable to parse emergency summary.",
    "medical_status": "Unknown",
    "priority_level": "HIGH",
    "location_context": "Unknown",
    "message_to_rescuers": "Emergency reported. Details pending clarification.",
    "message_to_family": "We are trying to send an emergency update.",
    "immediate_actions": [
        "Stay calm and conserve phone battery.",
        "Move to the safest available area.",
        "Signal for help with light or sound."
    ],
    "emotional_support": "You are not alone. Focus on one safe step at a time."
}


def _extract_json_block(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)

    brace = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if brace:
        return brace.group(1)

    return text


def parse_packet(response_text: str) -> Dict[str, Any]:
    try:
        payload = json.loads(_extract_json_block(response_text))
    except Exception:
        return DEFAULT_PACKET.copy()

    packet = DEFAULT_PACKET.copy()
    packet.update({k: v for k, v in payload.items() if k in packet})

    if not isinstance(packet.get("immediate_actions"), list):
        packet["immediate_actions"] = DEFAULT_PACKET["immediate_actions"]

    return packet
