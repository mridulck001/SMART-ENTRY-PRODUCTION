"""
QR Code generation engine for the Smart Entry System.
Encodes a UUID string into a high-error-correction PNG returned as base64.
"""
import qrcode
import io
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class QREngine:

    @staticmethod
    def generate_base64_qr(data_string: str) -> Optional[str]:
        """
        Generate a QR code image from data_string and return it as a
        base64-encoded data URI ready to embed in an <img> tag.

        Args:
            data_string: The UUID to encode (never include PII directly).

        Returns:
            A 'data:image/png;base64,...' string, or None on failure.
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                # ERROR_CORRECT_H = 30% data recovery — best for physical scanning
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(data_string)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{b64}"

        except Exception as exc:
            logger.error(f"QR generation failed for '{data_string[:8]}...': {exc}")
            return None
