import io
import qrcode
import secrets
import string

from django.core.files.base import ContentFile
from patients.models import Patient


def generate_unique_code():
    """
    Generates a unique 8 character alphanumeric code for a patient.
    Keeps regenerating until it finds one that does not already exist.
    Example output: A3XK92PL
    """
    characters = string.ascii_uppercase + string.digits

    while True:
        code = ''.join(secrets.choice(characters) for _ in range(8))

        # Make sure this code does not already exist in the database
        if not Patient.objects.filter(unique_code=code).exists():
            return code


def generate_qr_code(data: str, filename: str):
    """
    Generates a QR code image from a string and returns it
    as a Django ContentFile ready to be saved to an ImageField.

    data     — the string to encode in the QR code
    filename — what to name the saved file
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Create the image
    img = qr.make_image(fill_color="black", back_color="white")

    # Save image to an in-memory buffer instead of disk
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return ContentFile(buffer.read(), name=filename)