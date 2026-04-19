"""
Pixel Pro — Patient Report PDF Generator
Matches the dashboard design language: crimson red, Georgia headings,
warm off-white background, clean card sections.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Flowable
from reportlab.lib.colors import HexColor
import os, io

# ─── COLOUR TOKENS ───────────────────────────────────────────────────────────
RED       = HexColor("#B91C1C")
RED_DARK  = HexColor("#991B1B")
RED_LIGHT = HexColor("#FEE2E2")
RED_PALE  = HexColor("#FFF5F5")
BG        = HexColor("#F7F4F0")
WHITE     = HexColor("#FFFFFF")
BORDER    = HexColor("#E8E3DC")
TEXT      = HexColor("#1C1410")
TEXT2     = HexColor("#6B5E52")
TEXT3     = HexColor("#A8998C")
GREEN     = HexColor("#15803D")

W, H = A4   # 595.27 x 841.89 pt
MARGIN_X = 28*mm
MARGIN_Y = 20*mm
CONTENT_W = W - 2 * MARGIN_X


# ─── CUSTOM FLOWABLES ────────────────────────────────────────────────────────

class SectionBanner(Flowable):
    """Full-width dark-red rounded banner — section title."""
    def __init__(self, title, width=CONTENT_W, height=34):
        super().__init__()
        self.title  = title
        self._width = width
        self._height = height

    def wrap(self, *args):
        return self._width, self._height

    def draw(self):
        c = self.canv
        r = 8  # corner radius
        c.saveState()

        # gradient-ish background: dark red fill
        c.setFillColor(RED_DARK)
        c.roundRect(0, 0, self._width, self._height, r, fill=1, stroke=0)

        # thin highlight at top
        c.setFillColor(HexColor("#C62828"))
        c.roundRect(0, self._height - 6, self._width, 6, r, fill=1, stroke=0)
        c.roundRect(0, self._height - 6, self._width, 3, 0, fill=1, stroke=0)

        # title text
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(self._width / 2, self._height / 2 - 4, self.title)
        c.restoreState()


class HospitalHeader(Flowable):
    """Top header: logo placeholder on left, hospital name + address on right."""
    def __init__(self, hospital_name, address, logo_path=None, width=CONTENT_W, height=72):
        super().__init__()
        self.hospital_name = hospital_name
        self.address       = address
        self.logo_path     = logo_path
        self._width        = width
        self._height       = height

    def wrap(self, *args):
        return self._width, self._height

    def draw(self):
        c = self.canv
        c.saveState()

        # Outer card background
        c.setFillColor(WHITE)
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.6)
        c.roundRect(0, 0, self._width, self._height, 10, fill=1, stroke=1)

        # Left red accent bar
        c.setFillColor(RED)
        c.setStrokeColor(RED)
        c.roundRect(0, 8, 4, self._height - 16, 2, fill=1, stroke=0)

        logo_w = 60
        pad = 16

        # Logo area (placeholder box or actual image)
        logo_x = pad + 6
        logo_y = (self._height - logo_w) / 2
        if self.logo_path and os.path.exists(self.logo_path):
            c.drawImage(self.logo_path, logo_x, logo_y, width=logo_w, height=logo_w,
                        preserveAspectRatio=True, mask='auto')
        else:
            # Placeholder
            c.setFillColor(RED_LIGHT)
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.8)
            c.roundRect(logo_x, logo_y, logo_w, logo_w, 6, fill=1, stroke=1)
            c.setFillColor(RED)
            c.setFont("Helvetica", 7)
            c.drawCentredString(logo_x + logo_w / 2, logo_y + logo_w / 2 - 2, "HOSPITAL")
            c.drawCentredString(logo_x + logo_w / 2, logo_y + logo_w / 2 - 11, "LOGO")

        # Vertical divider
        div_x = logo_x + logo_w + 14
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.8)
        c.line(div_x, 12, div_x, self._height - 12)

        # Text block
        txt_x = div_x + 14
        txt_w = self._width - txt_x - pad

        # Hospital name
        c.setFillColor(RED_DARK)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(txt_x, self._height - 22, self.hospital_name)

        # Address lines
        c.setFillColor(TEXT2)
        c.setFont("Helvetica", 9)
        lines = self.address if isinstance(self.address, list) else [self.address]
        y = self._height - 37
        for line in lines[:3]:
            c.drawString(txt_x, y, line)
            y -= 13

        c.restoreState()


class AccentLine(Flowable):
    """A thin coloured horizontal rule."""
    def __init__(self, color=RED, width=CONTENT_W, thickness=1.5):
        super().__init__()
        self._color = color
        self._width = width
        self._thickness = thickness

    def wrap(self, *args):
        return self._width, self._thickness + 1

    def draw(self):
        c = self.canv
        c.saveState()
        c.setStrokeColor(self._color)
        c.setLineWidth(self._thickness)
        c.line(0, 0, self._width, 0)
        c.restoreState()


class ImagePlaceholder(Flowable):
    """Renders a grid of image placeholders (or real images)."""
    def __init__(self, images, cols=4, width=CONTENT_W, img_h=110):
        super().__init__()
        self.images = images   # list of file paths or None
        self.cols   = cols
        self._width = width
        self.img_h  = img_h
        gap = 8
        self.cell_w = (width - gap * (cols - 1)) / cols
        rows = (len(images) + cols - 1) // cols
        self._height = rows * (img_h + gap) - gap

    def wrap(self, *args):
        return self._width, self._height

    def draw(self):
        c = self.canv
        gap = 8
        rows = (len(self.images) + self.cols - 1) // self.cols
        for idx, img_path in enumerate(self.images):
            col = idx % self.cols
            row = idx // self.cols
            x = col * (self.cell_w + gap)
            y = self._height - (row + 1) * (self.img_h + gap) + gap

            c.saveState()
            if img_path and os.path.exists(img_path):
                c.drawImage(img_path, x, y, self.cell_w, self.img_h,
                            preserveAspectRatio=True, mask='auto')
            else:
                # Placeholder card
                c.setFillColor(HexColor("#EEEBE7"))
                c.setStrokeColor(BORDER)
                c.setLineWidth(0.6)
                c.roundRect(x, y, self.cell_w, self.img_h, 8, fill=1, stroke=1)
                # Mountain + circle icon
                cx = x + self.cell_w / 2
                cy = y + self.img_h / 2
                # Sun circle
                c.setFillColor(HexColor("#D6CFC5"))
                c.circle(cx - self.cell_w * 0.15, cy + 18, 10, fill=1, stroke=0)
                # Mountains
                c.setFillColor(HexColor("#C8BFB4"))
                p = c.beginPath()
                p.moveTo(x + 14, y + 28)
                p.lineTo(cx - 5, cy + 14)
                p.lineTo(x + self.cell_w - 14, y + 28)
                p.close()
                c.drawPath(p, fill=1, stroke=0)
                c.setFillColor(HexColor("#B8AFA4"))
                p2 = c.beginPath()
                p2.moveTo(x + 30, y + 28)
                p2.lineTo(cx + self.cell_w * 0.15, cy + 26)
                p2.lineTo(x + self.cell_w - 8, y + 28)
                p2.close()
                c.drawPath(p2, fill=1, stroke=0)
            c.restoreState()


# ─── STYLES ──────────────────────────────────────────────────────────────────

def make_styles():
    return {
        "field_label": ParagraphStyle(
            "field_label",
            fontName="Helvetica",
            fontSize=9.5,
            textColor=TEXT2,
            leading=14,
        ),
        "field_value": ParagraphStyle(
            "field_value",
            fontName="Helvetica-Bold",
            fontSize=10.5,
            textColor=RED_DARK,
            leading=14,
        ),
        "section_sub": ParagraphStyle(
            "section_sub",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=TEXT2,
            leading=14,
        ),
        "image_label": ParagraphStyle(
            "image_label",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=TEXT2,
            leading=14,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=TEXT3,
            alignment=TA_CENTER,
            leading=11,
        ),
        "report_id": ParagraphStyle(
            "report_id",
            fontName="Courier",
            fontSize=8,
            textColor=TEXT3,
            alignment=TA_RIGHT,
            leading=11,
        ),
    }


def field_row(label_text, value_text, styles):
    """Returns a 2-cell paragraph pair for inline label: value."""
    lbl = Paragraph(f"{label_text} :", styles["field_label"])
    val = Paragraph(value_text, styles["field_value"])
    return [lbl, val]


def two_col_fields(pairs, styles, col_ratio=(1, 1)):
    """Lay out up to 2 pairs per row as a Table."""
    rows = []
    for i in range(0, len(pairs), 2):
        left  = pairs[i]
        right = pairs[i + 1] if i + 1 < len(pairs) else (None, None)

        left_lbl  = Paragraph(f"{left[0]} :", styles["field_label"])  if left[0]  else Paragraph("", styles["field_label"])
        left_val  = Paragraph(left[1],        styles["field_value"])   if left[1]  else Paragraph("", styles["field_value"])
        right_lbl = Paragraph(f"{right[0]} :", styles["field_label"]) if right[0] else Paragraph("", styles["field_label"])
        right_val = Paragraph(right[1],        styles["field_value"])  if right[1] else Paragraph("", styles["field_value"])

        left_cell  = Table([[left_lbl],  [left_val]],  colWidths=[CONTENT_W * 0.46])
        right_cell = Table([[right_lbl], [right_val]], colWidths=[CONTENT_W * 0.46])
        left_cell.setStyle(TableStyle([
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ]))
        right_cell.setStyle(TableStyle([
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ]))
        rows.append([left_cell, right_cell])

    tbl = Table(rows, colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5])
    tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return tbl


def full_width_field(label_text, value_text, styles):
    """Single full-width label+value row."""
    lbl = Paragraph(f"{label_text} :", styles["field_label"])
    val = Paragraph(value_text, styles["field_value"])
    tbl = Table([[lbl], [val]], colWidths=[CONTENT_W])
    tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
    ]))
    return tbl


def section_card(elements, padding=14):
    """Wraps elements in a white rounded card via Table."""
    inner = Table([[e] for e in elements], colWidths=[CONTENT_W - 2*padding])
    inner.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
    ]))
    outer = Table([[inner]], colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), WHITE),
        ("ROUNDEDCORNERS",(0,0), (-1,-1), [10]),
        ("BOX",           (0,0), (-1,-1), 0.6, BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), padding),
        ("BOTTOMPADDING", (0,0), (-1,-1), padding),
        ("LEFTPADDING",   (0,0), (-1,-1), padding),
        ("RIGHTPADDING",  (0,0), (-1,-1), padding),
    ]))
    return outer


# ─── MAIN REPORT BUILDER ─────────────────────────────────────────────────────

def build_report(output_path, data: dict):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_Y,
        bottomMargin=MARGIN_Y,
    )

    styles = make_styles()
    story  = []

    # ── HOSPITAL HEADER ──────────────────────────────────────────────────────
    hosp = data.get("hospital", {})
    story.append(HospitalHeader(
        hospital_name=hosp.get("name", "City Eye & General Hospital"),
        address=hosp.get("address", [
            "Flat 101, Medical Complex, MG Road, Andheri West",
            "Mumbai – 400053  |  +91 22 6789 0123  |  info@cityeyehospital.com",
        ]),
        logo_path=hosp.get("logo_path", None),
    ))
    story.append(Spacer(1, 10))
    story.append(AccentLine(color=RED, thickness=1.5))
    story.append(Spacer(1, 5))

    # Report meta row (right-aligned ID + date)
    from datetime import datetime
    now_str  = datetime.now().strftime("%d %B %Y  %I:%M %p")
    report_id = data.get("report_id", "RPT-00001")
    meta_tbl = Table(
        [[Paragraph("", styles["footer"]),
          Paragraph(f"Report ID : {report_id}     Generated : {now_str}", styles["report_id"])]],
        colWidths=[CONTENT_W * 0.4, CONTENT_W * 0.6],
    )
    meta_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 10))

    # ── PATIENT REPORT SECTION ───────────────────────────────────────────────
    story.append(SectionBanner("Patient Report"))
    story.append(Spacer(1, 10))

    pt  = data.get("patient", {})
    med = data.get("medical", {})
    patient_inner = []

    # Name (full width) then two-col for DOB / Gender / Phone
    name_full = f"{pt.get('first_name', '—')} {pt.get('last_name', '—')}".strip()
    patient_inner.append(full_width_field("Patient Name", name_full, styles))
    patient_inner.append(Spacer(1, 4))
    patient_inner.append(two_col_fields([
        ("Date of Birth",    pt.get("dob",   "—")),
        ("Gender",           pt.get("gender","—")),
        ("Contact Number",   pt.get("phone", "—")),
        ("Referring Doctor", med.get("referring_doctor", "—")),
    ], styles))
    patient_inner.append(Spacer(1, 4))
    patient_inner.append(full_width_field("Address", pt.get("address", "—"), styles))

    story.append(section_card(patient_inner))
    story.append(Spacer(1, 16))

    # ── IMAGES SECTION ───────────────────────────────────────────────────────
    image_paths = data.get("images", [None] * 4)
    if image_paths:
        story.append(SectionBanner("Medical Images"))
        story.append(Spacer(1, 10))

        img_inner = [
            Spacer(1, 2),
            ImagePlaceholder(image_paths, cols=4),
            Spacer(1, 4),
        ]
        story.append(section_card(img_inner))
        story.append(Spacer(1, 16))

    # ── OBSERVATIONS (optional) ───────────────────────────────────────────────
    obs = data.get("observations")
    if obs:
        story.append(SectionBanner("Observations"))
        story.append(Spacer(1, 10))
        story.append(section_card([Paragraph(obs, ParagraphStyle(
            "obs", fontName="Helvetica", fontSize=10, textColor=TEXT, leading=16))]))
        story.append(Spacer(1, 16))

    # ── DIAGNOSIS (optional) ─────────────────────────────────────────────────
    diag = data.get("diagnosis")
    if diag:
        story.append(SectionBanner("Diagnosis / Impression"))
        story.append(Spacer(1, 10))
        story.append(section_card([Paragraph(diag, ParagraphStyle(
            "diag", fontName="Helvetica-Bold", fontSize=10, textColor=TEXT, leading=16))]))
        story.append(Spacer(1, 16))

    # ── VISIT NOTES (optional) ───────────────────────────────────────────────
    notes = data.get("visit_notes")
    if notes:
        story.append(SectionBanner("Visit Notes"))
        story.append(Spacer(1, 10))
        notes_inner = [Paragraph(notes, ParagraphStyle(
            "notes", fontName="Helvetica", fontSize=10,
            textColor=TEXT, leading=16,
        ))]
        story.append(section_card(notes_inner))
        story.append(Spacer(1, 16))

    # ── REPORTING DOCTOR ─────────────────────────────────────────────────────
    sig = data.get("signature") or data.get("reporting_doctor", "")
    dept = data.get("department", "")
    if sig or dept:
        story.append(SectionBanner("Reporting Doctor"))
        story.append(Spacer(1, 10))
        sig_pairs = []
        if data.get("reporting_doctor"): sig_pairs.append(("Reporting Doctor", data["reporting_doctor"]))
        if dept:                         sig_pairs.append(("Department",        dept))
        if sig and sig != data.get("reporting_doctor"): sig_pairs.append(("Signature", sig))
        if sig_pairs:
            story.append(section_card([two_col_fields(sig_pairs, styles)]))
            story.append(Spacer(1, 16))

    # ── FOOTER ───────────────────────────────────────────────────────────────
    story.append(AccentLine(color=BORDER, thickness=0.8))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"This report was generated by Pixel Pro Medical Imaging Software · {hosp.get('name', 'City Eye & General Hospital')} · "
        "Confidential — For authorised medical personnel only.",
        styles["footer"],
    ))

    doc.build(story)
    print(f"Report saved → {output_path}")


# ─── DEMO ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demo_data = {
        "report_id": "RPT-20260311-042",
        "hospital": {
            "name": "City Eye & General Hospital",
            "address": [
                "Medical Complex, MG Road, Andheri West, Mumbai – 400053",
                "Tel: +91 22 6789 0123  |  info@cityeyehospital.com",
            ],
            "logo_path": None,   # replace with actual path e.g. "hospital_logo.png"
        },
        "patient": {
            "first_name": "Yash",
            "last_name":  "Angre",
            "gender":     "Male",
            "dob":        "10th November 2002",
            "phone":      "123456789",
            "email":      "abcdekg@gmail.com",
            "address":    "Flat 203, Green Residency, JVPD Road, Andheri West, Mumbai – 400053",
        },
        "medical": {
            "current_medications": "Amlodipine 5mg (OD), Multivitamin",
            "existing_medical":    "Hypertension (diagnosed 2020)",
            "past_history":        "Appendicitis Surgery (2010)",
            "allergies":           "Penicillin",
            "referring_doctor":    "Dr. Priya Mehta (Cardiologist)",
        },
        "images": [None, None, None, None],   # replace None with actual image paths
        "visit_notes": (
            "Patient presented for routine follow-up. Blood pressure stable at 128/82 mmHg. "
            "Fundus imaging performed — no new haemorrhages noted. Advised to continue current "
            "medication regimen and return in 3 months."
        ),
    }

    build_report("/mnt/user-data/outputs/patient_report.pdf", demo_data)
