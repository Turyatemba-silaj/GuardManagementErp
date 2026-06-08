from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
EXCEL_EXTENSIONS = {".xlsx", ".xlsm"}
SCHEDULE_EXTENSIONS = EXCEL_EXTENSIONS | {".csv"}
FILE_SIGNATURES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),
    ".pdf": (b"%PDF-",),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    ".xlsm": (b"PK\x03\x04",),
}


def file_extension(uploaded_file):
    return Path(uploaded_file.name or "").suffix.lower()


def file_starts_with(uploaded_file, signatures):
    position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else None
    header = uploaded_file.read(16)
    if position is not None and hasattr(uploaded_file, "seek"):
        uploaded_file.seek(position)
    return any(header.startswith(signature) for signature in signatures)


def validate_uploaded_file(uploaded_file, *, allowed_extensions=None, max_size=None, label="file"):
    if not uploaded_file:
        return
    extension = file_extension(uploaded_file)
    max_size = max_size or settings.MAX_UPLOAD_SIZE
    if uploaded_file.size and uploaded_file.size > max_size:
        raise ValidationError(f"The uploaded {label} is too large. Maximum size is {max_size // (1024 * 1024)} MB.")
    if allowed_extensions and extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValidationError(f"The uploaded {label} type is not allowed. Use one of: {allowed}.")
    signatures = FILE_SIGNATURES.get(extension)
    if signatures and not file_starts_with(uploaded_file, signatures):
        raise ValidationError(f"The uploaded {label} content does not match its file extension.")


def validate_excel_upload(uploaded_file):
    validate_uploaded_file(
        uploaded_file,
        allowed_extensions=EXCEL_EXTENSIONS,
        max_size=settings.MAX_EXCEL_UPLOAD_SIZE,
        label="Excel workbook",
    )


def validate_schedule_upload(uploaded_file):
    validate_uploaded_file(
        uploaded_file,
        allowed_extensions=SCHEDULE_EXTENSIONS,
        max_size=settings.MAX_EXCEL_UPLOAD_SIZE,
        label="schedule file",
    )


def validate_model_upload(field_name, uploaded_file):
    if field_name in {"passport_photo", "photos"}:
        validate_uploaded_file(uploaded_file, allowed_extensions=IMAGE_EXTENSIONS, label=field_name.replace("_", " "))
        return
    validate_uploaded_file(uploaded_file, allowed_extensions=DOCUMENT_EXTENSIONS, label=field_name.replace("_", " "))
