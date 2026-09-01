"""
ProtonAI - PHI Free-Text Scrubber (منظّف الملاحظات الحرة — نسخة مؤسسية)
يكمّل gov_anonymizer: يخفي تلقائياً كل معرفات النصوص السريرية
(عربي بأرقام ٠-٩ + لاتيني):
أسماء، هواتف، تواريخ (رقمية/مكتوبة)، سنوات، أعمار، أرقام سجلات،
عناوين، إيميلات، وروابط ⇒ tokens موحدة.
- scrub / scrub_dict: تنظيف.
- is_clean: تحقق سريع.
- phi_report: تقرير تدقيق بعدد كل نوع مكتشف.
الذكاء الاصطناعي يتدرّب على البنى لا الهويات — فالحذف = صفر خسارة.
"""

import re
from typing import Dict

__all__ = ["scrub", "scrub_dict", "is_clean", "phi_report"]

DIG = "0-9٠-٩"  # أرقام لاتينية + عربية-هندية

MONTHS = ("كانون الثاني|كانون الأول|شباط|آذار|نيسان|أيار|حزيران|تموز|آب|"
          "أيلول|تشرين الأول|تشرين الثاني|يناير|فبراير|مارس|أبريل|مايو|"
          "يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر")

# -- الأنماط (تُطبَّق بالترتيب داخل scrub) ------------------------------ #
NAME_AFTER = re.compile(
    r"(الاسم|اسم المريض|المريض|السيد|السيدة|الآنسة)\s*[:：]?\s*([^\n،,;]{3,40})")
ADDR_AFTER = re.compile(
    r"(العنوان|يسكن|يقطن|منطقة|محلة|زقاق)\s*[:：]?\s*([^\n،,;]{3,60})")
URL = re.compile(r"(?:https?://|www\.)\S+")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+|00)?[" + DIG + r"][" + DIG + r"\s\-()]{7,}[" + DIG + r"]")
DATE_SEP = re.compile(r"\b[" + DIG + r"]{1,2}[/.-][" + DIG + r"]{1,2}[/.-]["
                      + DIG + r"]{2,4}\b")
DATE_TXT = re.compile(r"[" + DIG + r"]{1,2}\s+(?:" + MONTHS + r")\s*(?:["
                      + DIG + r"]{4})?")
YEAR = re.compile(r"\b(?:19|20)[" + DIG + r"]{2}\b")
AGE = re.compile(r"(?:العمر|عمر|بعمر|بسنة|عمره|عمرها)\s*[:：]?\s*["
                 + DIG + r"]{1,3}")
IDNUM = re.compile(r"\b[" + DIG + r"]{6,}\b")

_ORDER = [
    ("NAME", NAME_AFTER, lambda m: f"{m.group(1)}: [NAME]"),
    ("ADDR", ADDR_AFTER, lambda m: f"{m.group(1)}: [ADDR]"),
    ("URL", URL, "[URL]"),
    ("EMAIL", EMAIL, "[EMAIL]"),
    ("PHONE", PHONE, "[PHONE]"),
    ("DATE", DATE_SEP, "[DATE]"),
    ("DATE", DATE_TXT, "[DATE]"),
    ("DATE", YEAR, "[DATE]"),
    ("AGE", AGE, "[AGE]"),
    ("ID", IDNUM, "[ID]"),
]

_CHECK = [URL, EMAIL, PHONE, DATE_SEP, DATE_TXT, YEAR, IDNUM]


def scrub(text) -> str:
    """تنظيف نص حر من كل المعرفات => tokens موحدة"""
    if not isinstance(text, str):
        return text
    for _name, pat, repl in _ORDER:
        if callable(repl):
            text = pat.sub(repl, text)
        else:
            text = pat.sub(repl, text)
    return text


def scrub_dict(fields: dict) -> dict:
    """تنظيف كل القيم النصية داخل dict"""
    return {k: (scrub(v) if isinstance(v, str) else v)
            for k, v in fields.items()}


def is_clean(text) -> bool:
    """True إذا لم يتبقَّ نمط معرف واضح"""
    if not isinstance(text, str):
        return True
    return not any(p.search(text) for p in _CHECK)


def phi_report(text) -> Dict[str, int]:
    """تقرير تدقيق: عدد كل نوع معرف مكتشف قبل التنظيف"""
    if not isinstance(text, str):
        return {}
    counts: Dict[str, int] = {}
    for name, pat, _repl in _ORDER:
        n = len(pat.findall(text))
        if n:
            counts[name] = counts.get(name, 0) + n
    return counts
