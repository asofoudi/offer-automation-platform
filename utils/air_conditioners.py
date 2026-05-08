from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


AC_PRICE_FILE = Path(__file__).resolve().parents[1] / "data" / "ac_prices.csv"
BTU_CATEGORIES = [9000, 12000, 18000, 24000]

SPACE_TYPE_LABELS = {
    "bedroom": "Υπνοδωμάτιο",
    "living_room": "Σαλόνι",
    "office": "Γραφείο",
    "shop": "Κατάστημα",
}
FLOOR_LABELS = {
    "ground": "Ισόγειο",
    "middle": "Μεσαίος όροφος",
    "top": "Τελευταίος όροφος",
}
SUN_EXPOSURE_LABELS = {
    "low": "Χαμηλή",
    "medium": "Μεσαία",
    "high": "Υψηλή",
}
INSULATION_LABELS = {
    "good": "Καλή",
    "medium": "Μέτρια",
    "poor": "Κακή",
}
MAIN_USE_LABELS = {
    "cooling": "Ψύξη",
    "heating": "Θέρμανση",
    "both": "Ψύξη και θέρμανση",
}
BUDGET_LABELS = {
    "economy": "Οικονομική",
    "value": "Value for money",
    "premium": "Premium",
}
INSTALLATION_DIFFICULTY_LABELS = {
    "easy": "Εύκολη εγκατάσταση",
    "difficult": "Δύσκολη εγκατάσταση",
}

SPACE_TYPE_FACTORS = {
    "bedroom": 0.95,
    "living_room": 1.00,
    "office": 1.05,
    "shop": 1.10,
}
FLOOR_FACTORS = {
    "ground": 0.95,
    "middle": 1.00,
    "top": 1.10,
}
SUN_EXPOSURE_FACTORS = {
    "low": 0.95,
    "medium": 1.00,
    "high": 1.10,
}
INSULATION_FACTORS = {
    "good": 0.90,
    "medium": 1.00,
    "poor": 1.15,
}
MAIN_USE_FACTORS = {
    "cooling": 1.00,
    "heating": 1.10,
    "both": 1.05,
}

PRE_COSTING_DISCLAIMER = (
    "Η προσφορά αποτελεί ενδεικτική προκοστολόγηση. Η τελική επιλογή BTU, προϊόντος "
    "και κόστους εγκατάστασης πρέπει να επιβεβαιωθεί μετά από αυτοψία, έλεγχο σωληνώσεων, "
    "ηλεκτρολογικής παροχής, αποστάσεων εσωτερικής/εξωτερικής μονάδας και τεχνικών συνθηκών."
)


@dataclass(frozen=True)
class ACProduct:
    btu_category: int
    budget_tier: str
    product_name: str
    unit_price: float
    installation_easy: float
    installation_difficult: float
    notes: str = ""


@dataclass(frozen=True)
class ACQuotationInput:
    space_type: str
    square_meters: float
    floor: str
    sun_exposure: str
    insulation: str
    main_use: str
    installation_needed: bool
    installation_difficulty: str
    desired_budget: str


@dataclass(frozen=True)
class ACQuotation:
    inputs: ACQuotationInput
    recommended_btu: int
    estimated_btu: float
    product: ACProduct
    installation_cost: float
    total: float
    warnings: list[str]


def load_ac_products(path: Path = AC_PRICE_FILE) -> list[ACProduct]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [
            ACProduct(
                btu_category=int(row["btu_category"]),
                budget_tier=row["budget_tier"],
                product_name=row["product_name"],
                unit_price=float(row["unit_price_eur"]),
                installation_easy=float(row["installation_easy_eur"]),
                installation_difficult=float(row["installation_difficult_eur"]),
                notes=row.get("notes", ""),
            )
            for row in reader
        ]


def estimate_required_btu(inputs: ACQuotationInput) -> float:
    base_btu = inputs.square_meters * 500
    return (
        base_btu
        * SPACE_TYPE_FACTORS[inputs.space_type]
        * FLOOR_FACTORS[inputs.floor]
        * SUN_EXPOSURE_FACTORS[inputs.sun_exposure]
        * INSULATION_FACTORS[inputs.insulation]
        * MAIN_USE_FACTORS[inputs.main_use]
    )


def recommend_btu_category(estimated_btu: float) -> int:
    for category in BTU_CATEGORIES:
        if estimated_btu <= category:
            return category
    return BTU_CATEGORIES[-1]


def find_ac_product(
    products: list[ACProduct],
    btu_category: int,
    budget_tier: str,
) -> ACProduct:
    for product in products:
        if product.btu_category == btu_category and product.budget_tier == budget_tier:
            return product
    raise ValueError("Δεν βρέθηκε προϊόν για την επιλεγμένη κατηγορία BTU και budget.")


def installation_cost(product: ACProduct, installation_needed: bool, difficulty: str) -> float:
    if not installation_needed:
        return 0.0
    if difficulty == "difficult":
        return product.installation_difficult
    return product.installation_easy


def build_ac_quotation(
    inputs: ACQuotationInput,
    products: list[ACProduct] | None = None,
) -> ACQuotation:
    products = products or load_ac_products()
    estimated_btu = estimate_required_btu(inputs)
    recommended_btu = recommend_btu_category(estimated_btu)
    product = find_ac_product(products, recommended_btu, inputs.desired_budget)
    install_cost = installation_cost(
        product=product,
        installation_needed=inputs.installation_needed,
        difficulty=inputs.installation_difficulty,
    )
    warnings = []
    if estimated_btu > BTU_CATEGORIES[-1]:
        warnings.append(
            "Η εκτίμηση ξεπερνά τα 24.000 BTU. Μπορεί να απαιτηθούν περισσότερες μονάδες ή τεχνική μελέτη."
        )
    if inputs.square_meters <= 0:
        warnings.append("Τα τετραγωνικά πρέπει να είναι μεγαλύτερα από 0.")

    return ACQuotation(
        inputs=inputs,
        recommended_btu=recommended_btu,
        estimated_btu=estimated_btu,
        product=product,
        installation_cost=install_cost,
        total=product.unit_price + install_cost,
        warnings=warnings,
    )


def products_for_btu(products: list[ACProduct], btu_category: int) -> list[ACProduct]:
    return [product for product in products if product.btu_category == btu_category]


def products_for_display(products: list[ACProduct]) -> list[dict[str, str]]:
    return [
        {
            "BTU": f"{product.btu_category:,}".replace(",", "."),
            "Budget": BUDGET_LABELS.get(product.budget_tier, product.budget_tier),
            "Προϊόν": product.product_name,
            "Τιμή προϊόντος": format_eur(product.unit_price),
            "Εύκολη εγκατάσταση": format_eur(product.installation_easy),
            "Δύσκολη εγκατάσταση": format_eur(product.installation_difficult),
            "Σημείωση": product.notes,
        }
        for product in products
    ]


def format_eur(value: float) -> str:
    return f"{value:,.2f} €"


def format_btu(value: float | int) -> str:
    return f"{value:,.0f} BTU".replace(",", ".")
