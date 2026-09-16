"""
Vision Response Parser — Phase 5

WHAT IT DOES:
    Parses the raw text output from a vision/language model into
    structured DetectedFood objects.

WHY WE NEED IT:
    AI models sometimes return messy output — extra text before/after JSON,
    markdown code fences, trailing commas, etc. This parser handles all
    those edge cases robustly.

HOW IT WORKS:
    raw model output → clean up → extract JSON → parse → DetectedFood list
"""

from __future__ import annotations

import json
import re
from typing import List, Optional

from backend.app.vision.base import DetectedFood


def parse_vision_response(raw_response: str) -> List[DetectedFood]:
    """
    Parse raw vision model output into a list of DetectedFood objects.

    Handles common issues:
    - Markdown code fences (```json ... ```)
    - Extra text before/after JSON
    - Trailing commas
    - Single quotes instead of double quotes
    - Missing confidence values

    Args:
        raw_response: The raw text output from the vision model.

    Returns:
        List of DetectedFood objects. Empty list if parsing fails.
    """
    if not raw_response or not raw_response.strip():
        return []

    # Step 1: Try to extract JSON from the response
    json_str = _extract_json(raw_response)
    if not json_str:
        return []

    # Step 2: Clean up common JSON issues
    json_str = _clean_json(json_str)

    # Step 3: Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Last resort: try to find any array of food objects
        return _fallback_parse(raw_response)

    # Step 4: Extract food items
    foods = _extract_foods(data)
    return foods


def _extract_json(text: str) -> Optional[str]:
    """Extract JSON object or array from text that may contain other content."""
    # Remove markdown code fences
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # Try to find a JSON object
    # Look for the outermost { ... }
    brace_start = text.find('{')
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    return text[brace_start:i + 1]

    # Try to find a JSON array
    bracket_start = text.find('[')
    if bracket_start >= 0:
        depth = 0
        for i in range(bracket_start, len(text)):
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
                if depth == 0:
                    return text[bracket_start:i + 1]

    return None


def _clean_json(json_str: str) -> str:
    """Fix common JSON formatting issues from LLM output."""
    # Remove trailing commas before } or ]
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    # Replace single quotes with double quotes (careful with apostrophes)
    # Only do this if the string doesn't already have double quotes
    if '"' not in json_str and "'" in json_str:
        json_str = json_str.replace("'", '"')
    return json_str


def _extract_foods(data) -> List[DetectedFood]:
    """Extract DetectedFood objects from parsed JSON data."""
    foods = []

    # Handle {"foods": [...]}
    if isinstance(data, dict) and "foods" in data:
        items = data["foods"]
    # Handle direct array [...]
    elif isinstance(data, list):
        items = data
    else:
        return []

    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name", "").strip()
        if not name:
            continue

        confidence = item.get("confidence", 0.5)
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
        except (ValueError, TypeError):
            confidence = 0.5

        # Extract optional visual portion fields
        estimated_grams = item.get("estimated_grams")
        if estimated_grams is not None:
            try:
                estimated_grams = float(estimated_grams)
            except (ValueError, TypeError):
                estimated_grams = None

        visual_portion_size = item.get("portion_size") or item.get("portion_hint")
        if visual_portion_size:
            visual_portion_size = str(visual_portion_size).lower().strip()

        container_type = item.get("container_type")
        if container_type:
            container_type = str(container_type).lower().strip()

        visual_cues = item.get("visual_cues") or item.get("notes")
        if visual_cues:
            visual_cues = str(visual_cues).strip()

        bounding_box = item.get("bounding_box")

        foods.append(DetectedFood(
            name=name.lower(),
            confidence=confidence,
            bounding_box=bounding_box,
            estimated_grams=estimated_grams,
            visual_portion_size=visual_portion_size,
            visual_cues=visual_cues,
            container_type=container_type,
        ))

    return foods


def _fallback_parse(text: str) -> List[DetectedFood]:
    """
    Last-resort parser for when JSON parsing fails completely.
    Tries to find food names in the text using simple patterns.
    """
    foods = []
    # Look for patterns like "name": "something" or name: something
    pattern = r'"?name"?\s*:\s*"([^"]+)"'
    matches = re.findall(pattern, text, re.IGNORECASE)

    for match in matches:
        name = match.strip().lower()
        if name and len(name) > 1:
            foods.append(DetectedFood(name=name, confidence=0.5))

    return foods
