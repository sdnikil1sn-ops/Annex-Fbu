"""Shared image-decoding helpers for media adapters."""

from __future__ import annotations

import cv2
import numpy as np

from app.application.ports.media import MediaProcessingError


def decode_image(image_bytes: bytes) -> np.ndarray:
    """Decode image bytes into an OpenCV BGR array.

    Args:
        image_bytes: Raw image data (PNG, JPEG, ...).

    Returns:
        The decoded image as a numpy array.

    Raises:
        MediaProcessingError: When the bytes are not a decodable image.
    """
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise MediaProcessingError("cannot decode image bytes")
    return image
