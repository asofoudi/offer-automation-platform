from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


RADIATOR_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "radiators.csv"
WORK_DISCOUNT_NOTE = "Αν είναι για δουλειά τότε γίνεται έξτρα έκπτωση έως -10%."


@dataclass(frozen=True)
class RadiatorRow:
    body_type: int
    height: int
    length_mm: int
    power_kcal_h: float
    price_eur: float


@dataclass(frozen=True)
class RadiatorQuote:
    radiator: RadiatorRow
    customer_type: str
    catalog_price: float
    final_price: float
    pricing_note: str

    @property
    def power_kw(self) -> float:
        return kcal_to_kw(self.radiator.power_kcal_h)


def load_radiators(path: Path = RADIATOR_DATA_FILE) -> list[RadiatorRow]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [
            RadiatorRow(
                body_type=int(row["type"]),
                height=int(row["height"]),
                length_mm=int(row["length_mm"]),
                power_kcal_h=float(row["power_kcal_h"]),
                price_eur=float(row["price_eur"]),
            )
            for row in reader
        ]


def available_body_types(rows: list[RadiatorRow]) -> list[int]:
    return sorted({row.body_type for row in rows})


def available_heights(rows: list[RadiatorRow], body_type: int) -> list[int]:
    return sorted({row.height for row in rows if row.body_type == body_type})


def available_lengths(rows: list[RadiatorRow], body_type: int, height: int) -> list[int]:
    return sorted(
        {
            row.length_mm
            for row in rows
            if row.body_type == body_type and row.height == height
        }
    )


def find_radiator(
    rows: list[RadiatorRow],
    body_type: int,
    height: int,
    length_mm: int,
) -> RadiatorRow:
    for row in rows:
        if (
            row.body_type == body_type
            and row.height == height
            and row.length_mm == length_mm
        ):
            return row
    raise ValueError("Δεν βρέθηκε σώμα για τον επιλεγμένο συνδυασμό.")


def price_for_customer(price_eur: float, customer_type: str) -> float:
    if customer_type == "Ιδιώτης":
        return float(math.ceil(price_eur * 1.10))
    return round(price_eur, 2)


def quote_radiator(radiator: RadiatorRow, customer_type: str) -> RadiatorQuote:
    if customer_type == "Ιδιώτης":
        pricing_note = (
            "Τελική τιμή = τιμή καταλόγου × 1.10, με στρογγυλοποίηση προς τα πάνω στο ευρώ."
        )
    else:
        pricing_note = "Τιμή επαγγελματία = τιμή καταλόγου όπως είναι στο αρχείο."

    return RadiatorQuote(
        radiator=radiator,
        customer_type=customer_type,
        catalog_price=radiator.price_eur,
        final_price=price_for_customer(radiator.price_eur, customer_type),
        pricing_note=pricing_note,
    )


def kcal_to_kw(power_kcal_h: float) -> float:
    return power_kcal_h / 860.0


def format_eur(value: float) -> str:
    return f"{value:,.2f} €"


def format_int(value: float) -> str:
    return f"{value:,.0f}"


def rows_for_display(rows: list[RadiatorRow]) -> list[dict[str, str]]:
    return [
        {
            "Τύπος": str(row.body_type),
            "Ύψος": f"{row.height} mm",
            "Μήκος": f"{row.length_mm} mm",
            "Ισχύς": f"{format_int(row.power_kcal_h)} kcal/h",
            "Τιμή καταλόγου": format_eur(row.price_eur),
        }
        for row in rows
    ]
