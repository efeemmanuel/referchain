import io
import qrcode
import secrets
import string

from django.core.files.base import ContentFile
from referrals.models import Referral


def generate_referral_code():
    """
    Generates a unique 10 character alphanumeric code for a referral.
    Format: REF- followed by 8 random characters.
    Example: REF-A3XK92PL
    """
    characters = string.ascii_uppercase + string.digits

    while True:
        code = 'REF-' + ''.join(secrets.choice(characters) for _ in range(8))
        if not Referral.objects.filter(unique_code=code).exists():
            return code


def generate_referral_qr(data: str, filename: str):
    """
    Generates a QR code for a referral unique code.
    Returns a Django ContentFile ready to save to an ImageField.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return ContentFile(buffer.read(), name=filename)