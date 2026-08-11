"""
ProtonAI - Data: DICOM Parser (CT / RTSTRUCT / RTDOSE / RTPLAN)
استخراج معلومات مهيكلة من كائنات DICOM (تعمل على أي كائن بسمات):
- CT: الأبعاد + spacing + سماكة الشريحة.
- RTSTRUCT: أسماء وأرقام الـ ROIs.
- RTDOSE: أبعاد شبكة الجرعة + scaling + عدد الـ frames.
- RTPLAN: الحزم + الجرعة الموصوفة للهدف.
"""


def parse_ct(ds) -> dict:
    """معلومات هندسية لشريحة/دراسة CT"""
    return {
        "modality": getattr(ds, "Modality", ""),
        "rows": int(getattr(ds, "Rows", 0)),
        "columns": int(getattr(ds, "Columns", 0)),
        "pixel_spacing": [float(x) for x in getattr(ds, "PixelSpacing", [1, 1])],
        "slice_thickness": float(getattr(ds, "SliceThickness", 0.0)),
    }


def parse_rtstruct(ds) -> list:
    """قائمة الـ ROIs (رقم + اسم) من RTSTRUCT"""
    rois = []
    for i, roi in enumerate(getattr(ds, "StructureSetROISequence", [])):
        rois.append({
            "number": int(getattr(roi, "ROINumber", i)),
            "name": getattr(roi, "ROIName", f"ROI-{i}"),
        })
    return rois


def parse_rtdose(ds) -> dict:
    """معلومات شبكة الجرعة من RTDOSE"""
    return {
        "rows": int(getattr(ds, "Rows", 0)),
        "columns": int(getattr(ds, "Columns", 0)),
        "dose_grid_scaling": float(getattr(ds, "DoseGridScaling", 1.0)),
        "frames": len(getattr(ds, "GridFrameOffsetVector", [0])),
    }


def parse_rtplan(ds) -> dict:
    """الحزم + الجرعة الموصوفة للهدف من RTPLAN"""
    beams = [getattr(b, "BeamName", f"beam-{i}")
             for i, b in enumerate(getattr(ds, "BeamSequence", []))]
    prescribed = None
    for ref in getattr(ds, "DoseReferenceSequence", []):
        if getattr(ref, "DoseReferenceType", "") == "TARGET":
            prescribed = float(getattr(ref, "TargetPrescribedDose", 0.0))
    return {"beams": beams, "num_beams": len(beams),
            "prescribed_dose": prescribed}
