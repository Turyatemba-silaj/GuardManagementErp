from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
EXCEL_EXTENSIONS = {".xlsx", ".xlsm"}


def file_extension(uploaded_file):
    return Path(uploaded_file.name or "").suffix.lower()


def validate_uploaded_file(uploaded_file, *, allowed_extensions=None, max_size=None, label="file"):
    if not uploaded_file:
        return
    max_size = max_size or settings.MAX_UPLOAD_SIZE
    if uploaded_file.size and uploaded_file.size > max_size:
        raise ValidationError(f"The uploaded {label} is too large. Maximum size is {max_size // (1024 * 1024)} MB.")
    if allowed_extensions and file_extension(uploaded_file) not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValidationError(f"The uploaded {label} type is not allowed. Use one of: {allowed}.")


def validate_excel_upload(uploaded_file):
    validate_uploaded_file(
        uploaded_file,
        allowed_extensions=EXCEL_EXTENSIONS,
        max_size=settings.MAX_EXCEL_UPLOAD_SIZE,
        label="Excel workbook",
    )


def validate_model_upload(field_name, uploaded_file):
    if field_name in {"passport_photo", "photos"}:
        validate_uploaded_file(uploaded_file, allowed_extensions=IMAGE_EXTENSIONS, label=field_name.replace("_", " "))
        return
    validate_uploaded_file(uploaded_file, allowed_extensions=DOCUMENT_EXTENSIONS, label=field_name.replace("_", " "))
