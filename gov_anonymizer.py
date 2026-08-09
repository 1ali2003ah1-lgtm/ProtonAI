def is_deidentified(ds) -> bool:
    """هل الـ Dataset مُخفى الهوية فعلاً؟ (لا PHI متبقٍ + معلم كمُخفى)"""
    _require_pydicom()
    for tag in PHI_TAGS:
        if tag == "PatientName":
            continue  # يحمل الـ pseudonym عمداً — لا نعتبره تسريباً
        if getattr(ds, tag, "") not in ("", None):
            return False
    return getattr(ds, "PatientIdentityRemoved", "") == "YES"
