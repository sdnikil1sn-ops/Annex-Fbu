"""Image forensics via OpenCV: dimensions and Error-Level Analysis."""

from __future__ import annotations

import cv2

from app.application.ports.media import ForensicsAdapter, ForensicsReport
from app.infrastructure.media.utils import decode_image

# ELA mean-absolute-diff threshold that marks a "high" tamper signal.
_ELA_HIGH_THRESHOLD = 20.0


class OpenCvForensicsAdapter(ForensicsAdapter):
    """Computes tamper-relevant signals from an image.

    Error-Level Analysis (ELA) re-encodes the image at JPEG quality 90 and
    measures the mean absolute difference. Uniform areas of genuine JPEGs
    re-encode almost losslessly; edited regions light up with residuals.
    """

    def analyze(self, image_bytes: bytes) -> ForensicsReport:
        """Analyze image bytes for tamper signals.

        Args:
            image_bytes: Raw image data.

        Returns:
            A report with dimensions, ELA signal, and a risk score.

        Raises:
            MediaProcessingError: When the image cannot be decoded.
        """
        image = decode_image(image_bytes)
        height, width = image.shape[:2]

        encoded, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not encoded:
            raise ValueError("image re-encoding failed")
        resaved = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if resaved is None:
            raise ValueError("image re-encoding produced no output")
        diff = cv2.absdiff(image, resaved)
        ela_mean = float(diff.mean())
        risk = min(1.0, ela_mean / 40.0)

        signals = {
            "width": width,
            "height": height,
            "ela_mean": round(ela_mean, 4),
            "reencode_signal": "high" if ela_mean > _ELA_HIGH_THRESHOLD else "low",
        }
        return ForensicsReport(signals=signals, risk_score=round(risk, 4))
