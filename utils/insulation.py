from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path


PRICE_FILE = Path(__file__).resolve().parents[1] / "data" / "insulation_prices.csv"

DISCLAIMER = (
    "Η προσφορά αποτελεί προϊόν προκοστολόγησης. Το τελικό κόστος και οι τελικές "
    "ποσότητες πρέπει να επιβεβαιωθούν μετά από έλεγχο/αυτοψία και τεχνική επιβεβαίωση."
)


@dataclass(frozen=True)
class InsulationPrice:
    key: str
    code: str
    description: str
    unit: str
    unit_price: float


@dataclass(frozen=True)
class BomLine:
    code: str
    material: str
    need: str
    package: str
    quantity: float | None
    unit: str
    unit_price: float | None
    total: float | None
    notes: str = ""


@dataclass(frozen=True)
class InsulationOfferInput:
    area_m2: float
    insulation_type: str
    thickness_cm: int


@dataclass(frozen=True)
class InsulationOffer:
    inputs: InsulationOfferInput
    bom_lines: list[BomLine]
    total: float
    priced: bool
    warnings: list[str]


def load_insulation_prices(path: Path = PRICE_FILE) -> dict[str, InsulationPrice]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return {
            row["key"]: InsulationPrice(
                key=row["key"],
                code=row["code"],
                description=row["description"],
                unit=row["unit"],
                unit_price=float(row["unit_price"]),
            )
            for row in reader
        }


def ceil_units(required_quantity: float, package_quantity: float) -> int:
    if required_quantity <= 0:
        return 0
    return math.ceil(required_quantity / package_quantity)


def choose_primer_packages(required_liters: float) -> tuple[int, int, float]:
    """Choose 10L and 3L packages with the smallest overage."""
    if required_liters <= 0:
        return 0, 0, 0.0

    best: tuple[float, float, int, int, int] | None = None
    max_10l = math.ceil(required_liters / 10) + 2
    max_3l = math.ceil(required_liters / 3) + 4

    for packs_10l in range(max_10l + 1):
        for packs_3l in range(max_3l + 1):
            total_liters = packs_10l * 10 + packs_3l * 3
            if total_liters < required_liters:
                continue

            overage = total_liters - required_liters
            package_count = packs_10l + packs_3l
            candidate = (overage, total_liters, package_count, packs_10l, packs_3l)
            if best is None or candidate < best:
                best = candidate

    if best is None:
        return 0, 0, 0.0

    _, total_liters, _, packs_10l, packs_3l = best
    return packs_10l, packs_3l, float(total_liters)


def build_insulation_offer(
    inputs: InsulationOfferInput,
    prices: dict[str, InsulationPrice] | None = None,
) -> InsulationOffer:
    prices = prices or load_insulation_prices()
    area = inputs.area_m2
    thickness = inputs.thickness_cm
    warnings: list[str] = []
    bom_lines: list[BomLine] = []

    priced_board = inputs.insulation_type == "Γραφιτούχα"
    if priced_board:
        board = prices[f"graphite_{thickness}"]
        bom_lines.append(
            BomLine(
                code=board.code,
                material=board.description,
                need=f"{format_number(area)} m²",
                package="-",
                quantity=area,
                unit=board.unit,
                unit_price=board.unit_price,
                total=area * board.unit_price,
            )
        )
    else:
        warnings.append(
            "Δεν υπάρχει καταχωρημένη τιμή/κωδικός για εξηλασμένη μόνωση στο διαθέσιμο παλιό υλικό. "
            "Το σύνολο δεν περιλαμβάνει κόστος πλακών."
        )
        bom_lines.append(
            BomLine(
                code="-",
                material=f"Πλάκες θερμομόνωσης (Εξηλασμένη, {thickness} cm)",
                need=f"{format_number(area)} m²",
                package="-",
                quantity=None,
                unit="m²",
                unit_price=None,
                total=None,
                notes="Χρειάζεται τιμή πριν την τελική προσφορά.",
            )
        )

    glue = prices["glue"]
    glue_kg = area * 8
    glue_bags = ceil_units(glue_kg, 25)
    bom_lines.append(
        BomLine(
            code=glue.code,
            material=glue.description,
            need=f"{format_number(glue_kg)} kg",
            package="25 kg/σακί",
            quantity=float(glue_bags),
            unit=glue.unit,
            unit_price=glue.unit_price,
            total=glue_bags * glue.unit_price,
        )
    )

    mesh = prices["mesh"]
    mesh_m2 = area * 1.1
    mesh_rolls = ceil_units(mesh_m2, 50)
    bom_lines.append(
        BomLine(
            code=mesh.code,
            material="Υαλόπλεγμα (ποσότητα σε m²)",
            need=f"{format_number(mesh_m2)} m²",
            package="Ρολό 50 m²",
            quantity=float(mesh_rolls),
            unit=mesh.unit,
            unit_price=mesh.unit_price,
            total=mesh_rolls * mesh.unit_price,
        )
    )

    plugs = prices[f"plug_{thickness}"]
    plug_count = math.ceil(area * 5.5)
    plug_boxes = ceil_units(plug_count, 250)
    bom_lines.append(
        BomLine(
            code=plugs.code,
            material=plugs.description,
            need=f"{format_number(plug_count)} τεμ.",
            package="Κουτί 250 τεμ.",
            quantity=float(plug_boxes),
            unit=plugs.unit,
            unit_price=plugs.unit_price,
            total=plug_boxes * plugs.unit_price,
        )
    )

    required_primer_liters = area / 11
    packs_10l, packs_3l, total_primer_liters = choose_primer_packages(required_primer_liters)
    primer_10 = prices["primer_10"]
    primer_3 = prices["primer_3"]
    primer_note = (
        f"Ανάγκη {format_number(required_primer_liters)} L, "
        f"αγορά {format_number(total_primer_liters)} L."
    )
    bom_lines.append(
        BomLine(
            code=primer_10.code,
            material=primer_10.description,
            need=f"{format_number(required_primer_liters)} L",
            package="10 L",
            quantity=float(packs_10l),
            unit=primer_10.unit,
            unit_price=primer_10.unit_price,
            total=packs_10l * primer_10.unit_price,
            notes=primer_note,
        )
    )
    bom_lines.append(
        BomLine(
            code=primer_3.code,
            material=primer_3.description,
            need=f"{format_number(required_primer_liters)} L",
            package="3 L",
            quantity=float(packs_3l),
            unit=primer_3.unit,
            unit_price=primer_3.unit_price,
            total=packs_3l * primer_3.unit_price,
            notes=primer_note,
        )
    )

    paste = prices["paste"]
    paste_kg = area * 2.5
    paste_buckets = ceil_units(paste_kg, 25)
    bom_lines.append(
        BomLine(
            code=paste.code,
            material=paste.description,
            need=f"{format_number(paste_kg)} kg",
            package="25 kg/κουβάς",
            quantity=float(paste_buckets),
            unit=paste.unit,
            unit_price=paste.unit_price,
            total=paste_buckets * paste.unit_price,
        )
    )

    bom_lines.extend(
        [
            BomLine(
                code="-",
                material="Γωνιόκρανα (παρελκόμενο)",
                need="Κατά περίπτωση",
                package="-",
                quantity=None,
                unit="-",
                unit_price=None,
                total=None,
                notes="Δεν περιλαμβάνεται στο σύνολο.",
            ),
            BomLine(
                code="-",
                material="Αφρός χαμηλής διόγκωσης (παρελκόμενο)",
                need="Κατά περίπτωση",
                package="-",
                quantity=None,
                unit="-",
                unit_price=None,
                total=None,
                notes="Δεν περιλαμβάνεται στο σύνολο.",
            ),
        ]
    )

    total = sum(line.total for line in bom_lines if line.total is not None)
    return InsulationOffer(
        inputs=inputs,
        bom_lines=bom_lines,
        total=total,
        priced=priced_board,
        warnings=warnings,
    )


def format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{round(value):,}"
    return f"{value:,.2f}"


def format_eur(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:,.2f} €"


def offer_rows_for_display(offer: InsulationOffer) -> list[dict[str, str]]:
    rows = []
    for line in offer.bom_lines:
        rows.append(
            {
                "Κωδ.": line.code,
                "Υλικό": line.material,
                "Ανάγκη": line.need,
                "Συσκευασία": line.package,
                "Ποσότητα αγοράς": "-" if line.quantity is None else format_number(line.quantity),
                "Μονάδα": line.unit,
                "Τιμή μονάδας": format_eur(line.unit_price),
                "Σύνολο": format_eur(line.total),
                "Σημείωση": line.notes,
            }
        )
    return rows


def offer_rows_to_csv(offer: InsulationOffer) -> str:
    rows = offer_rows_for_display(offer)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def generate_insulation_summary(
    offer: InsulationOffer,
    customer: dict[str, str],
    created_at: datetime | None = None,
) -> str:
    created_at = created_at or datetime.now()
    inputs = offer.inputs

    lines = [
        "=== ΠΡΟΣΦΟΡΑ ΘΕΡΜΟΜΟΝΩΣΗΣ - ΠΡΟΚΟΣΤΟΛΟΓΗΣΗ ===",
        f"Ημερομηνία: {created_at.strftime('%d/%m/%Y %H:%M')}",
        "",
        "Στοιχεία πελάτη",
        f"- Ονοματεπώνυμο / Επωνυμία: {customer.get('name', '')}",
        f"- Τηλέφωνο: {customer.get('phone', '')}",
        f"- Email: {customer.get('email', '')}",
        f"- Τοποθεσία / διεύθυνση έργου: {customer.get('address', '')}",
        "",
        "Στοιχεία έργου",
        f"- Επιφάνεια μόνωσης: {format_number(inputs.area_m2)} m²",
        f"- Τύπος μόνωσης: {inputs.insulation_type}",
        f"- Πάχος μόνωσης: {inputs.thickness_cm} cm",
        "",
        "BOM και κοστολόγηση",
    ]

    for line in offer.bom_lines:
        total = format_eur(line.total)
        qty = "-" if line.quantity is None else format_number(line.quantity)
        lines.append(
            f"- {line.code} | {line.material} | Ανάγκη: {line.need} | "
            f"Αγορά: {qty} {line.unit} | Τιμή: {format_eur(line.unit_price)} | Σύνολο: {total}"
        )
        if line.notes:
            lines.append(f"  Σημείωση: {line.notes}")

    lines.extend(["", f"Σύνολο υλικών: {format_eur(offer.total)}"])
    if customer.get("comments"):
        lines.extend(["", "Σχόλια υπαλλήλου:", customer["comments"]])

    if offer.warnings:
        lines.extend(["", "Προειδοποιήσεις:"])
        lines.extend(f"- {warning}" for warning in offer.warnings)

    lines.extend(["", "Παρατήρηση:", DISCLAIMER])
    return "\n".join(lines)
