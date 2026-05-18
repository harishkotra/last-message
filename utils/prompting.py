from pathlib import Path


def load_emergency_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "emergency_packet_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")


def build_user_prompt(user_input: str, location_context: dict) -> str:
    location_block = (
        f"Latitude: {location_context.get('latitude', 'Unknown')}\n"
        f"Longitude: {location_context.get('longitude', 'Unknown')}\n"
        f"City: {location_context.get('city', 'Unknown')}\n"
        f"Nearby Landmark: {location_context.get('landmark', 'Unknown')}"
    )

    return (
        "Distressed user message:\n"
        f"{user_input.strip()}\n\n"
        "Location and context panel:\n"
        f"{location_block}\n\n"
        "Now generate the emergency packet JSON."
    )
