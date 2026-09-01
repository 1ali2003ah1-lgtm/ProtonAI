"""
ProtonAI - Test PHI Scrubber (Enterprise)
"""

from phi_scrubber import is_clean, phi_report, scrub, scrub_dict

SAMPLE = ("المريض: احمد محمد جاسم، الهاتف 07701234567، "
          "تاريخ 12/05/1980، رقم السجل 12345678، يسكن بغداد المنصور، "
          "البريد x@y.com، رابط http://a.b، العمر: 45.")

ARABIC = "هاتف ٠٧٧٠١٢٣٤٥٦٧ وتاريخ ١٢/٠٥/١٩٠ وسجل ١٢٣٤٥٦٧٨"


class TestScrub:
    def test_name(self):
        assert "[NAME]" in scrub(SAMPLE) and "احمد" not in scrub(SAMPLE)

    def test_phone(self):
        assert "[PHONE]" in scrub(SAMPLE) and "07701234567" not in scrub(SAMPLE)

    def test_date(self):
        assert "[DATE]" in scrub(SAMPLE) and "1980" not in scrub(SAMPLE)

    def test_id(self):
        assert "[ID]" in scrub(SAMPLE) and "12345678" not in scrub(SAMPLE)

    def test_addr(self):
        assert "[ADDR]" in scrub(SAMPLE) and "المنصور" not in scrub(SAMPLE)

    def test_email_url(self):
        out = scrub(SAMPLE)
        assert "[EMAIL]" in out and "[URL]" in out and "x@y.com" not in out

    def test_age(self):
        assert "[AGE]" in scrub(SAMPLE)

    def test_arabic_digits(self):
        out = scrub(ARABIC)
        assert "٠٧٧١٢٣٤٥٦٧" not in out and "١٩٨٠" not in out
        assert "[PHONE]" in out and "[DATE]" in out


class TestClean:
    def test_dirty(self):
        assert is_clean(SAMPLE) is False

    def test_clean_after(self):
        assert is_clean(scrub(SAMPLE)) is True

    def test_non_str(self):
        assert is_clean(70) is True


class TestReport:
    def test_counts(self):
        r = phi_report(SAMPLE)
        assert r.get("PHONE") == 1 and r.get("NAME") == 1

    def test_empty(self):
        assert phi_report("لا شيء") == {}


class TestDict:
    def test_dict(self):
        r = scrub_dict({"note": SAMPLE, "dose": 70})
        assert "[NAME]" in r["note"] and r["dose"] == 70
