from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping, MutableSequence, Sequence
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DEFAULT_DISCLAIMER = (
    "Η προσφορά είναι ενδεικτική και βασίζεται στα στοιχεία που έχουν καταχωρηθεί. "
    "Η τελική επιβεβαίωση γίνεται μετά από τεχνικό έλεγχο, διαθεσιμότητα προϊόντων "
    "και οριστικοποίηση των εργασιών."
)


class PdfOfferError(RuntimeError):
    pass


class GreekFontError(PdfOfferError):
    pass


@dataclass(frozen=True)
class RegisteredFonts:
    regular: str
    bold: str
    family: str


@dataclass(frozen=True)
class CompanyInfo:
    name: str = "Η εταιρεία σας"
    address: str = ""
    phone: str = ""
    email: str = ""
    tax_id: str = ""
    tax_office: str = ""
    logo_path: str | Path | None = None


@dataclass(frozen=True)
class ProductLine:
    description: str
    quantity: float
    unit: str
    unit_price: float
    total_price: float | None = None
    notes: str = ""

    @property
    def line_total(self) -> float:
        if self.total_price is not None:
            return self.total_price
        return self.quantity * self.unit_price


@dataclass(frozen=True)
class OfferTotals:
    subtotal: float
    discount: float
    vat_rate: float
    vat_amount: float
    total: float


@dataclass(frozen=True)
class FinancingOption:
    name: str
    installments: int
    monthly_amount: float
    total_amount: float
    note: str = ""


_REGISTERED_FONTS: RegisteredFonts | None = None


def create_offer_pdf(
    *,
    customer: Mapping[str, Any] | Any,
    products: Sequence[ProductLine | Mapping[str, Any]],
    company: CompanyInfo | Mapping[str, Any] | None = None,
    offer_title: str = "Προσφορά",
    offer_number: str | None = None,
    offer_date: date | str | None = None,
    logo_path: str | Path | None = None,
    totals: OfferTotals | Mapping[str, Any] | None = None,
    discount: float = 0.0,
    vat_rate: float = 0.0,
    financing_options: Sequence[FinancingOption | Mapping[str, Any]] | None = None,
    disclaimer: str = DEFAULT_DISCLAIMER,
    font_path: str | Path | None = None,
    bold_font_path: str | Path | None = None,
) -> bytes:
    fonts = register_greek_fonts(font_path=font_path, bold_font_path=bold_font_path)
    styles = build_offer_styles(fonts)
    product_lines = normalize_products(products)
    offer_totals = normalize_totals(
        totals=totals,
        products=product_lines,
        discount=discount,
        vat_rate=vat_rate,
    )
    company_info = normalize_company(company, logo_path=logo_path)
    pdf_buffer = BytesIO()

    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title=offer_title,
    )

    elements: list[Any] = []
    add_company_header(
        elements,
        company=company_info,
        styles=styles,
        offer_title=offer_title,
        offer_number=offer_number,
        offer_date=offer_date,
    )
    add_customer_section(elements, customer=customer, styles=styles)
    add_products_table(elements, products=product_lines, styles=styles)
    add_totals_section(elements, totals=offer_totals, styles=styles)
    add_financing_section(
        elements,
        financing_options=financing_options or [],
        styles=styles,
    )
    add_disclaimer_section(elements, disclaimer=disclaimer, styles=styles)

    def draw_footer(canvas: Any, document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont(fonts.regular, 8)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawString(
            document.leftMargin,
            10 * mm,
            "Ενιαία πλατφόρμα προσφορών",
        )
        canvas.drawRightString(
            A4[0] - document.rightMargin,
            10 * mm,
            f"Σελίδα {document.page}",
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


def add_customer_section(
    elements: MutableSequence[Any],
    customer: Mapping[str, Any] | Any,
    styles: Mapping[str, ParagraphStyle] | None = None,
) -> None:
    styles = styles or build_offer_styles(register_greek_fonts())
    customer_data = object_to_dict(customer)
    rows = [
        ["Ονοματεπώνυμο", value_from(customer_data, "full_name", "name", "Ονοματεπώνυμο")],
        ["Τηλέφωνο", value_from(customer_data, "phone", "telephone", "Τηλέφωνο")],
        ["Email", value_from(customer_data, "email", "Email")],
        ["Περιοχή", value_from(customer_data, "area", "region", "Περιοχή")],
        ["Σχόλια", value_from(customer_data, "comments", "notes", "Σχόλια")],
    ]

    table_rows = [
        [
            Paragraph(paragraph_text(label), styles["table_label"]),
            Paragraph(paragraph_text(value or "—"), styles["table_cell"]),
        ]
        for label, value in rows
    ]

    elements.append(Paragraph("Στοιχεία πελάτη", styles["section_title"]))
    elements.append(
        Table(
            table_rows,
            colWidths=[42 * mm, 124 * mm],
            hAlign="LEFT",
            style=base_table_style(),
        )
    )
    elements.append(Spacer(1, 7 * mm))


def add_products_table(
    elements: MutableSequence[Any],
    products: Sequence[ProductLine | Mapping[str, Any]],
    styles: Mapping[str, ParagraphStyle] | None = None,
) -> list[ProductLine]:
    styles = styles or build_offer_styles(register_greek_fonts())
    product_lines = normalize_products(products)
    rows: list[list[Any]] = [
        [
            Paragraph("Περιγραφή", styles["table_header"]),
            Paragraph("Ποσ.", styles["table_header"]),
            Paragraph("Μονάδα", styles["table_header"]),
            Paragraph("Τιμή μονάδας", styles["table_header"]),
            Paragraph("Σύνολο", styles["table_header"]),
        ]
    ]

    for product in product_lines:
        description = product.description
        if product.notes:
            description = f"{description}\n{product.notes}"

        rows.append(
            [
                Paragraph(paragraph_text(description), styles["table_cell"]),
                Paragraph(format_quantity(product.quantity), styles["table_cell_right"]),
                Paragraph(paragraph_text(product.unit), styles["table_cell"]),
                Paragraph(format_eur(product.unit_price), styles["table_cell_right"]),
                Paragraph(format_eur(product.line_total), styles["table_cell_right"]),
            ]
        )

    elements.append(Paragraph("Προϊόντα και τιμολόγηση", styles["section_title"]))
    elements.append(
        Table(
            rows,
            colWidths=[74 * mm, 18 * mm, 23 * mm, 28 * mm, 28 * mm],
            repeatRows=1,
            hAlign="LEFT",
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244653")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), styles["font_bold"]),
                    ("FONTNAME", (0, 1), (-1, -1), styles["font_regular"]),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )
    )
    elements.append(Spacer(1, 7 * mm))
    return product_lines


def add_financing_section(
    elements: MutableSequence[Any],
    financing_options: Sequence[FinancingOption | Mapping[str, Any]],
    styles: Mapping[str, ParagraphStyle] | None = None,
) -> None:
    styles = styles or build_offer_styles(register_greek_fonts())
    normalized_options = normalize_financing_options(financing_options)

    elements.append(Paragraph("Χρηματοδότηση και δόσεις", styles["section_title"]))
    if not normalized_options:
        elements.append(
            Paragraph(
                "Δεν έχει προστεθεί πρόγραμμα δόσεων για αυτή την προσφορά.",
                styles["body"],
            )
        )
        elements.append(Spacer(1, 7 * mm))
        return

    rows: list[list[Any]] = [
        [
            Paragraph("Πλάνο", styles["table_header"]),
            Paragraph("Δόσεις", styles["table_header"]),
            Paragraph("Μηνιαία δόση", styles["table_header"]),
            Paragraph("Σύνολο", styles["table_header"]),
            Paragraph("Σημείωση", styles["table_header"]),
        ]
    ]
    for option in normalized_options:
        rows.append(
            [
                Paragraph(paragraph_text(option.name), styles["table_cell"]),
                Paragraph(str(option.installments), styles["table_cell_right"]),
                Paragraph(format_eur(option.monthly_amount), styles["table_cell_right"]),
                Paragraph(format_eur(option.total_amount), styles["table_cell_right"]),
                Paragraph(paragraph_text(option.note or "—"), styles["table_cell"]),
            ]
        )

    elements.append(
        Table(
            rows,
            colWidths=[46 * mm, 18 * mm, 30 * mm, 30 * mm, 47 * mm],
            hAlign="LEFT",
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244653")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), styles["font_bold"]),
                    ("FONTNAME", (0, 1), (-1, -1), styles["font_regular"]),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )
    )
    elements.append(Spacer(1, 7 * mm))


def add_company_header(
    elements: MutableSequence[Any],
    *,
    company: CompanyInfo,
    styles: Mapping[str, ParagraphStyle],
    offer_title: str,
    offer_number: str | None,
    offer_date: date | str | None,
) -> None:
    logo = create_logo_image(company.logo_path)
    company_lines = [company.name]
    if company.address:
        company_lines.append(company.address)
    if company.phone:
        company_lines.append(f"Τηλ.: {company.phone}")
    if company.email:
        company_lines.append(f"Email: {company.email}")
    if company.tax_id:
        tax_line = f"ΑΦΜ: {company.tax_id}"
        if company.tax_office:
            tax_line = f"{tax_line} | ΔΟΥ: {company.tax_office}"
        company_lines.append(tax_line)

    offer_lines = [offer_title]
    if offer_number:
        offer_lines.append(f"Αριθμός προσφοράς: {offer_number}")
    offer_lines.append(f"Ημερομηνία: {format_offer_date(offer_date)}")

    left_cell = logo if logo is not None else Paragraph(paragraph_text(company.name), styles["company_name"])
    right_cell = Paragraph(
        paragraph_text("\n".join(offer_lines)),
        styles["offer_meta"],
    )
    header_rows = [[left_cell, right_cell]]
    elements.append(
        Table(
            header_rows,
            colWidths=[72 * mm, 99 * mm],
            hAlign="LEFT",
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        )
    )
    elements.append(Paragraph(paragraph_text("\n".join(company_lines)), styles["company_details"]))
    elements.append(Spacer(1, 7 * mm))


def add_totals_section(
    elements: MutableSequence[Any],
    totals: OfferTotals,
    styles: Mapping[str, ParagraphStyle],
) -> None:
    rows: list[list[Any]] = [
        ["Καθαρή αξία", format_eur(totals.subtotal)],
    ]
    if totals.discount:
        rows.append(["Έκπτωση", f"-{format_eur(totals.discount)}"])
    if totals.vat_rate or totals.vat_amount:
        rows.append([f"ΦΠΑ {format_percent(totals.vat_rate)}", format_eur(totals.vat_amount)])
    rows.append(["Σύνολο προσφοράς", format_eur(totals.total)])

    table_rows = [
        [
            Paragraph(paragraph_text(label), styles["table_label"]),
            Paragraph(paragraph_text(value), styles["table_cell_right"]),
        ]
        for label, value in rows
    ]

    elements.append(Paragraph("Σύνολα", styles["section_title"]))
    elements.append(
        Table(
            table_rows,
            colWidths=[112 * mm, 54 * mm],
            hAlign="RIGHT",
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), styles["font_regular"]),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E7F0F2")),
                    ("FONTNAME", (0, -1), (-1, -1), styles["font_bold"]),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )
    )
    elements.append(Spacer(1, 7 * mm))


def add_disclaimer_section(
    elements: MutableSequence[Any],
    disclaimer: str,
    styles: Mapping[str, ParagraphStyle],
) -> None:
    elements.append(Paragraph("Παρατηρήσεις", styles["section_title"]))
    elements.append(Paragraph(paragraph_text(disclaimer), styles["body"]))


def normalize_company(
    company: CompanyInfo | Mapping[str, Any] | None,
    logo_path: str | Path | None = None,
) -> CompanyInfo:
    if company is None:
        return CompanyInfo(logo_path=logo_path)
    if isinstance(company, CompanyInfo):
        return CompanyInfo(
            name=company.name,
            address=company.address,
            phone=company.phone,
            email=company.email,
            tax_id=company.tax_id,
            tax_office=company.tax_office,
            logo_path=logo_path or company.logo_path,
        )

    company_data = object_to_dict(company)
    return CompanyInfo(
        name=str(value_from(company_data, "name", "company_name", "Επωνυμία") or "Η εταιρεία σας"),
        address=str(value_from(company_data, "address", "Διεύθυνση") or ""),
        phone=str(value_from(company_data, "phone", "telephone", "Τηλέφωνο") or ""),
        email=str(value_from(company_data, "email", "Email") or ""),
        tax_id=str(value_from(company_data, "tax_id", "vat_number", "ΑΦΜ") or ""),
        tax_office=str(value_from(company_data, "tax_office", "ΔΟΥ") or ""),
        logo_path=logo_path or value_from(company_data, "logo_path", "Λογότυπο"),
    )


def normalize_products(products: Sequence[ProductLine | Mapping[str, Any]]) -> list[ProductLine]:
    return [normalize_product(product) for product in products]


def normalize_product(product: ProductLine | Mapping[str, Any]) -> ProductLine:
    if isinstance(product, ProductLine):
        return product

    product_data = object_to_dict(product)
    total_value = value_from(product_data, "total_price", "line_total", "total", "Σύνολο")
    return ProductLine(
        description=str(value_from(product_data, "description", "name", "product", "Περιγραφή", "Προϊόν") or ""),
        quantity=as_float(value_from(product_data, "quantity", "qty", "Ποσότητα"), default=1.0),
        unit=str(value_from(product_data, "unit", "Μονάδα") or "τεμ."),
        unit_price=as_float(value_from(product_data, "unit_price", "price", "Τιμή μονάδας")),
        total_price=None if total_value in (None, "") else as_float(total_value),
        notes=str(value_from(product_data, "notes", "comments", "Σχόλια") or ""),
    )


def normalize_totals(
    *,
    totals: OfferTotals | Mapping[str, Any] | None,
    products: Sequence[ProductLine],
    discount: float,
    vat_rate: float,
) -> OfferTotals:
    if isinstance(totals, OfferTotals):
        return totals
    if totals is not None:
        totals_data = object_to_dict(totals)
        return OfferTotals(
            subtotal=as_float(value_from(totals_data, "subtotal", "Καθαρή αξία")),
            discount=as_float(value_from(totals_data, "discount", "Έκπτωση")),
            vat_rate=as_float(value_from(totals_data, "vat_rate", "ΦΠΑ %")),
            vat_amount=as_float(value_from(totals_data, "vat_amount", "ΦΠΑ")),
            total=as_float(value_from(totals_data, "total", "Σύνολο")),
        )

    subtotal = sum(product.line_total for product in products)
    taxable_amount = max(subtotal - discount, 0)
    vat_amount = taxable_amount * vat_rate
    return OfferTotals(
        subtotal=subtotal,
        discount=discount,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        total=taxable_amount + vat_amount,
    )


def normalize_financing_options(
    financing_options: Sequence[FinancingOption | Mapping[str, Any]],
) -> list[FinancingOption]:
    normalized: list[FinancingOption] = []
    for option in financing_options:
        if isinstance(option, FinancingOption):
            normalized.append(option)
            continue

        option_data = object_to_dict(option)
        normalized.append(
            FinancingOption(
                name=str(value_from(option_data, "name", "plan", "Πλάνο") or ""),
                installments=int(as_float(value_from(option_data, "installments", "months", "Δόσεις"))),
                monthly_amount=as_float(value_from(option_data, "monthly_amount", "monthly", "Μηνιαία δόση")),
                total_amount=as_float(value_from(option_data, "total_amount", "total", "Σύνολο")),
                note=str(value_from(option_data, "note", "notes", "Σημείωση") or ""),
            )
        )
    return normalized


def build_offer_styles(fonts: RegisteredFonts) -> dict[str, Any]:
    sample = getSampleStyleSheet()
    return {
        "font_regular": fonts.regular,
        "font_bold": fonts.bold,
        "title": ParagraphStyle(
            "OfferTitle",
            parent=sample["Title"],
            fontName=fonts.bold,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#17313A"),
            spaceAfter=5,
        ),
        "company_name": ParagraphStyle(
            "CompanyName",
            parent=sample["Normal"],
            fontName=fonts.bold,
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#17313A"),
        ),
        "company_details": ParagraphStyle(
            "CompanyDetails",
            parent=sample["Normal"],
            fontName=fonts.regular,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#374151"),
        ),
        "offer_meta": ParagraphStyle(
            "OfferMeta",
            parent=sample["Normal"],
            fontName=fonts.bold,
            fontSize=11,
            leading=14,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#17313A"),
        ),
        "section_title": ParagraphStyle(
            "SectionTitle",
            parent=sample["Heading2"],
            fontName=fonts.bold,
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#17313A"),
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "GreekBody",
            parent=sample["Normal"],
            fontName=fonts.regular,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#374151"),
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=sample["Normal"],
            fontName=fonts.bold,
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "table_label": ParagraphStyle(
            "TableLabel",
            parent=sample["Normal"],
            fontName=fonts.bold,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#17313A"),
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=sample["Normal"],
            fontName=fonts.regular,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#374151"),
        ),
        "table_cell_right": ParagraphStyle(
            "TableCellRight",
            parent=sample["Normal"],
            fontName=fonts.regular,
            fontSize=8.5,
            leading=11,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#374151"),
        ),
    }


def register_greek_fonts(
    font_path: str | Path | None = None,
    bold_font_path: str | Path | None = None,
) -> RegisteredFonts:
    global _REGISTERED_FONTS

    if _REGISTERED_FONTS is not None and font_path is None and bold_font_path is None:
        return _REGISTERED_FONTS

    regular_path = Path(font_path).expanduser() if font_path else find_font(regular_font_candidates())
    if regular_path is None:
        raise GreekFontError(
            "Δεν βρέθηκε γραμματοσειρά Unicode με υποστήριξη ελληνικών. "
            "Ορίστε font_path στο create_offer_pdf ή εγκαταστήστε Arial/DejaVu Sans."
        )

    bold_path = Path(bold_font_path).expanduser() if bold_font_path else find_font(bold_font_candidates())
    if bold_path is None:
        bold_path = regular_path

    fonts = RegisteredFonts(
        regular="OfferGreekRegular",
        bold="OfferGreekBold",
        family="OfferGreek",
    )
    pdfmetrics.registerFont(TTFont(fonts.regular, str(regular_path)))
    pdfmetrics.registerFont(TTFont(fonts.bold, str(bold_path)))
    pdfmetrics.registerFontFamily(
        fonts.family,
        normal=fonts.regular,
        bold=fonts.bold,
        italic=fonts.regular,
        boldItalic=fonts.bold,
    )

    if font_path is None and bold_font_path is None:
        _REGISTERED_FONTS = fonts
    return fonts


def regular_font_candidates() -> list[Path]:
    return [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]


def bold_font_candidates() -> list[Path]:
    return [
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
    ]


def find_font(candidates: Sequence[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def create_logo_image(logo_path: str | Path | None) -> Image | None:
    if not logo_path:
        return None

    path = Path(logo_path).expanduser()
    if not path.exists():
        return None

    logo = Image(str(path))
    logo._restrictSize(45 * mm, 25 * mm)
    return logo


def base_table_style() -> TableStyle:
    return TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), "OfferGreekRegular"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]
    )


def object_to_dict(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return {}


def value_from(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def as_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace(".", "").replace(",", ".") if "," in str(value) else value)


def paragraph_text(value: Any) -> str:
    return escape(str(value)).replace("\n", "<br/>")


def format_offer_date(value: date | str | None) -> str:
    if value is None:
        value = date.today()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)


def format_eur(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} €"


def format_quantity(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".replace(".", ",").rstrip("0").rstrip(",")


def format_percent(value: float) -> str:
    return f"{value * 100:.0f}%"
