"""
Google Gemini Vision Detector — Phase 5 / Extension

WHAT IT DOES:
    Uses Google's Gemini Multimodal Vision API (e.g., gemini-1.5-flash or gemini-2.0-flash)
    to visually inspect meal images, identify Indian foods, and estimate visual portions.

WHY WE NEED IT:
    Gemini provides state-of-the-art multimodal vision with a free API tier,
    high throughput, and robust recognition of diverse regional cuisines.
"""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Optional
import urllib.error
import urllib.request

from backend.app.utils.logger import logger
from backend.app.vision.base import VisionModel, VisionResult
from backend.app.vision.parser import parse_vision_response
from backend.app.vision.prompts import FOOD_DETECTION_PROMPT


class GeminiVisionModel(VisionModel):
    """
    Google Gemini Multimodal Vision detector.
    Calls Google's Generative Language API with inline base64 image data.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash",
    ):
        self.api_key = api_key
        self.model = model

    @property
    def model_name(self) -> str:
        return f"Google Gemini Vision ({self.model})"

    @property
    def mode(self) -> str:
        return "gemini"

    def detect_foods(self, image_path: str) -> VisionResult:
        """
        Analyze meal image using Gemini Vision API.
        """
        if not self.api_key:
            return VisionResult(
                foods=[],
                model_name=self.model_name,
                mode=self.mode,
                error="GEMINI_API_KEY is not configured.",
            )

        path = Path(image_path)
        if not path.exists():
            return VisionResult(
                foods=[],
                model_name=self.model_name,
                mode=self.mode,
                error=f"Image file not found: {image_path}",
            )

        try:
            # Read and base64-encode image
            image_bytes = path.read_bytes()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type or not mime_type.startswith("image/"):
                mime_type = "image/jpeg"

            endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent?key={self.api_key}"
            )

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": FOOD_DETECTION_PROMPT},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": image_b64,
                                }
                            },
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                },
            }

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                result_data = json.loads(resp.read().decode("utf-8"))

            candidates = result_data.get("candidates", [])
            if not candidates:
                return VisionResult(
                    foods=[],
                    model_name=self.model_name,
                    mode=self.mode,
                    error="Gemini returned no candidates.",
                )

            raw_text = (
                candidates[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            foods = parse_vision_response(raw_text)

            logger.info(
                f"[Gemini Vision] Detected {len(foods)} foods from {path.name}"
            )

            return VisionResult(
                foods=foods,
                model_name=self.model_name,
                mode=self.mode,
                raw_response=raw_text,
            )

        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            logger.error(f"[Gemini Vision] HTTP Error {e.code}: {err_msg}")
            return VisionResult(
                foods=[],
                model_name=self.model_name,
                mode=self.mode,
                error=f"Gemini API HTTP {e.code}: {err_msg[:200]}",
            )
        except Exception as ex:
            logger.error(f"[Gemini Vision] Unexpected error: {ex}")
            return VisionResult(
                foods=[],
                model_name=self.model_name,
                mode=self.mode,
                error=f"Gemini Vision error: {str(ex)}",
            )
