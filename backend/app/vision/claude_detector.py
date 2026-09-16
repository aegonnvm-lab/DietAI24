"""
Claude Vision Detector — Phase 5

WHAT IT DOES:
    Uses Anthropic's Claude API (with vision capabilities) to analyze
    a meal image and detect food items.

WHY WE NEED IT:
    Claude is a powerful vision-language model that can accurately identify
    Indian food items from photographs. This is the "real" vision mode
    that replaces the mock detector.

WHEN TO USE:
    Set VISION_MODE=claude in your .env file.
    Requires: ANTHROPIC_API_KEY in your .env file.

COST:
    Claude API calls cost money. For development, use mock mode instead.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Optional

from backend.app.vision.base import DetectedFood, VisionModel, VisionResult
from backend.app.vision.parser import parse_vision_response
from backend.app.vision.prompts import FOOD_DETECTION_PROMPT


class ClaudeVisionModel(VisionModel):
    """
    Claude-based vision model using the Anthropic API.

    Uses Claude's image analysis capabilities to identify
    food items in meal photographs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024,
    ):
        """
        Initialize the Claude vision model.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Claude model to use. Default is Claude Sonnet (good balance of cost/quality).
            max_tokens: Maximum tokens in the response.
        """
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._client: Optional[Any] = None

    def _get_client(self):
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "anthropic package is required for Claude vision mode.\n"
                    "Install it with: python -m pip install anthropic"
                )

            import os
            api_key = self._api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not set.\n"
                    "Set it in your .env file or pass it directly.\n"
                    "Get a key at: https://console.anthropic.com/"
                )

            self._client = anthropic.Anthropic(api_key=api_key)

        return self._client

    @property
    def model_name(self) -> str:
        return f"Claude ({self._model})"

    @property
    def mode(self) -> str:
        return "claude"

    def detect_foods(self, image_path: str) -> VisionResult:
        """
        Analyze a meal image using Claude's vision capabilities.

        Args:
            image_path: Path to the image file.

        Returns:
            VisionResult with detected foods.
        """
        path = Path(image_path)

        # Validate image exists
        if not path.exists():
            return VisionResult(
                foods=[],
                model_name=self.model_name,
                mode=self.mode,
                error=f"Image file not found: {image_path}",
            )

        # Read and encode image
        try:
            image_data = path.read_bytes()
            base64_image = base64.standard_b64encode(image_data).decode("utf-8")

            # Determine media type
            mime_type, _ = mimetypes.guess_type(str(path))
            if mime_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
                mime_type = "image/jpeg"  # Default fallback

        except Exception as e:
            return VisionResult(
                foods=[],
                model_name=self.model_name,
                mode=self.mode,
                error=f"Could not read image: {e}",
            )

        # Call Claude API
        try:
            client = self._get_client()

            message = client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": base64_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": FOOD_DETECTION_PROMPT,
                            },
                        ],
                    }
                ],
            )

            first_block = message.content[0]
            raw_response = getattr(first_block, "text", str(first_block))

            # Parse the response
            foods = parse_vision_response(raw_response)

            if not foods:
                return VisionResult(
                    foods=[],
                    model_name=self.model_name,
                    mode=self.mode,
                    raw_response=raw_response,
                    error="No food items could be identified in the image.",
                )

            return VisionResult(
                foods=foods,
                model_name=self.model_name,
                mode=self.mode,
                raw_response=raw_response,
            )

        except ImportError:
            raise
        except ValueError:
            raise
        except Exception as e:
            return VisionResult(
                foods=[],
                model_name=self.model_name,
                mode=self.mode,
                error=f"Claude API error: {str(e)}",
            )
