from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


YES = "Ναι"
NO = "Όχι"
INSTALLMENT_MONTHS = 36
ANNUAL_INSTALLMENT_RATE = 0.13
HEAT_PUMP_MODEL_FILE = Path(__file__).resolve().parents[1] / "data" / "heat_pump_models.csv"
PRIMARY_MODEL_KW = {8, 10, 12, 16, 26}


@dataclass(frozen=True)
class HeatPumpQuestionnaire:
    install_interest: str
    program_purchase: str
    funding_rate_choice: str | None
    wants_installments: str
    interest_type: str
    solar_people_band: str | None
    has_engineer_study: str
    house_type: str
    area_m2: float
    year_category: str
    apt_floor_position: str
    renovation_done: str
    renovation_options: list[str]
    renovation_other: str
    project_type: str
    power_type: str
    usage_type: str
    znx_people: int | None
    change_radiators: str
    distribution_type: str
    emission_type: str
    boiler_type: str
    boiler_other: str
    boiler_power_known: str
    boiler_power_unit: str | None
    boiler_power_value: float | None
    fuel_consumption_known: str
    fuel_consumption_type: str | None
    fuel_consumption_value: float | None
    has_solar: str
    has_pv: str
    has_outdoor_space: str
    outdoor_desc: str
    noise_limits: str
    noise_desc: str
    comments: str
    name: str
    phone: str
    email: str
    address: str


@dataclass(frozen=True)
class HeatPumpModel:
    model_id: str
    brand: str
    model_name: str
    series: str
    kw: int
    voltage: str
    price: float
    image_path: str
    description: str
    cop: str
    dimensions: str
    erp_code: str
    is_alternative: bool = False

    @property
    def name(self) -> str:
        parts = [self.brand.strip(), self.model_name.strip()]
        return " ".join(part for part in parts if part)

    @property
    def display_name(self) -> str:
        return self.name or f"Αντλία {self.kw} kW"


@dataclass(frozen=True)
class HeatPumpOfferResult:
    low_kw: float | None
    high_kw: float | None
    avg_kw: float | None
    target_kw: float | None
    adjusted_w_per_m2: float | None
    selected_model: HeatPumpModel | None
    alternative_model: HeatPumpModel | None
    notes: list[str]
    pump_cost: float
    labor_materials_cost: float
    solar_cost: float
    total_cost: float
    subsidy_rate: float
    subsidy_amount: float
    customer_contribution: float
    monthly_installment: float | None
    installment_total: float | None

    @property
    def has_estimate(self) -> bool:
        return self.selected_model is not None and self.avg_kw is not None

    @property
    def kw_range_label(self) -> str:
        if self.low_kw is None or self.high_kw is None or self.avg_kw is None:
            return "Δεν υπολογίστηκε"
        return f"{self.low_kw:.1f} - {self.high_kw:.1f} kW (κέντρο ~{self.avg_kw:.1f} kW)"


@dataclass(frozen=True)
class HeatPumpAlternativeQuote:
    model: HeatPumpModel
    pump_cost: float
    labor_materials_cost: float
    solar_cost: float
    total_cost: float
    subsidy_rate: float
    subsidy_amount: float
    customer_contribution: float
    monthly_installment: float | None
    installment_total: float | None
    additional_cost: float


def default_heat_pump_models() -> list[HeatPumpModel]:
    return [
        HeatPumpModel(
            model_id="hyundai_model_s_8",
            brand="Hyundai",
            model_name="Model S 8 kW",
            series="Economy",
            kw=8,
            voltage="230V",
            price=2690,
            image_path="assets/heat_pumps/hyundai_model_s_8.png",
            description="Οικονομική επιλογή για μικρομεσαίες κατοικίες",
            cop="",
            dimensions="",
            erp_code="",
        ),
        HeatPumpModel(
            model_id="hyundai_compact_9",
            brand="Hyundai",
            model_name="Compact 9 kW",
            series="Compact",
            kw=9,
            voltage="230V",
            price=3490,
            image_path="assets/heat_pumps/hyundai_compact_9.png",
            description="Εναλλακτική compact λύση με υψηλότερο κόστος",
            cop="",
            dimensions="",
            erp_code="",
            is_alternative=True,
        ),
        HeatPumpModel(
            model_id="generic_heat_pump_10",
            brand="",
            model_name="Αντλία 10 kW",
            series="Placeholder",
            kw=10,
            voltage="",
            price=4000,
            image_path="",
            description="Placeholder γραμμή μέχρι να δοθούν τελικά εμπορικά στοιχεία",
            cop="",
            dimensions="",
            erp_code="",
        ),
        HeatPumpModel(
            model_id="generic_heat_pump_12",
            brand="",
            model_name="Αντλία 12 kW",
            series="Placeholder",
            kw=12,
            voltage="",
            price=4350,
            image_path="",
            description="Placeholder γραμμή μέχρι να δοθούν τελικά εμπορικά στοιχεία",
            cop="",
            dimensions="",
            erp_code="",
        ),
        HeatPumpModel(
            model_id="generic_heat_pump_16",
            brand="",
            model_name="Αντλία 16 kW",
            series="Placeholder",
            kw=16,
            voltage="",
            price=4590,
            image_path="",
            description="Placeholder γραμμή μέχρι να δοθούν τελικά εμπορικά στοιχεία",
            cop="",
            dimensions="",
            erp_code="",
        ),
        HeatPumpModel(
            model_id="generic_heat_pump_26",
            brand="",
            model_name="Αντλία 26 kW",
            series="Placeholder",
            kw=26,
            voltage="",
            price=7410,
            image_path="",
            description="Placeholder γραμμή μέχρι να δοθούν τελικά εμπορικά στοιχεία",
            cop="",
            dimensions="",
            erp_code="",
        ),
    ]


def load_heat_pump_models(path: Path = HEAT_PUMP_MODEL_FILE) -> list[HeatPumpModel]:
    required_fields = {
        "model_id",
        "brand",
        "model_name",
        "series",
        "kw",
        "voltage",
        "price",
        "image_path",
        "description",
        "cop",
        "dimensions",
        "erp_code",
    }
    if not path.exists():
        return default_heat_pump_models()

    models: list[HeatPumpModel] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames or not required_fields.issubset(set(reader.fieldnames)):
                return default_heat_pump_models()

            for row in reader:
                try:
                    models.append(
                        HeatPumpModel(
                            model_id=(row.get("model_id") or "").strip(),
                            brand=(row.get("brand") or "").strip(),
                            model_name=(row.get("model_name") or "").strip(),
                            series=(row.get("series") or "").strip(),
                            kw=int(float(row.get("kw") or 0)),
                            voltage=(row.get("voltage") or "").strip(),
                            price=float(row.get("price") or 0),
                            image_path=(row.get("image_path") or "").strip(),
                            description=(row.get("description") or "").strip(),
                            cop=(row.get("cop") or "").strip(),
                            dimensions=(row.get("dimensions") or "").strip(),
                            erp_code=(row.get("erp_code") or "").strip(),
                            is_alternative=(row.get("model_id") or "").strip() == "hyundai_compact_9",
                        )
                    )
                except (TypeError, ValueError):
                    continue
    except (OSError, UnicodeDecodeError, csv.Error):
        return default_heat_pump_models()

    return models or default_heat_pump_models()


AVAILABLE_MODELS = load_heat_pump_models()


def primary_heat_pump_models(models: list[HeatPumpModel] | None = None) -> list[HeatPumpModel]:
    models = models or AVAILABLE_MODELS
    return sorted(
        [
            model
            for model in models
            if model.kw in PRIMARY_MODEL_KW and model.model_id != "hyundai_compact_9"
        ],
        key=lambda model: model.kw,
    )


def compact_9kw_model(models: list[HeatPumpModel] | None = None) -> HeatPumpModel | None:
    models = models or AVAILABLE_MODELS
    for model in models:
        if model.model_id == "hyundai_compact_9":
            return model
    return None


def base_w_per_m2_for_year(year_category: str) -> float:
    if year_category == "Πριν το 1980":
        return 110
    if year_category == "1980–2000":
        return 90
    if year_category == "2001–2009":
        return 75
    return 60


def renovation_reduction(renovation_done: str, renovation_options: list[str]) -> float:
    if renovation_done != YES:
        return 0

    reduction = 0.0
    if "Θερμομόνωση κελύφους" in renovation_options:
        reduction += 0.15
    if "Θερμομόνωση δώματος / ταράτσας" in renovation_options:
        reduction += 0.10
    if "Αντικατάσταση κουφωμάτων" in renovation_options:
        reduction += 0.10
    return min(reduction, 0.30)


def apply_home_type_adjustment(
    w_per_m2: float,
    house_type: str,
    apt_floor_position: str,
) -> tuple[float, str]:
    if house_type == "Μονοκατοικία" or apt_floor_position.startswith("Δεν ισχύει"):
        return w_per_m2 * 1.10, "Μονοκατοικία - ελαφρώς αυξημένες απώλειες."

    if apt_floor_position == "Ενδιάμεσος όροφος":
        return w_per_m2 * 0.85, "Διαμέρισμα ενδιάμεσο - λιγότερες απώλειες."

    if apt_floor_position == "Τελευταίος όροφος / ρετιρέ":
        return w_per_m2, "Διαμέρισμα τελευταίος όροφος - κανονικές προς αυξημένες απώλειες."

    return w_per_m2, "Διαμέρισμα."


def apply_emitter_adjustment(w_per_m2: float, emission_type: str) -> tuple[float, str]:
    if emission_type == "Ενδοδαπέδια":
        return (
            w_per_m2 * 0.90,
            "Ενδοδαπέδια - χαμηλές θερμοκρασίες, μπορεί να δουλεύει με χαμηλότερα kW.",
        )
    if emission_type == "Fan coil":
        return w_per_m2 * 0.95, "Fan coil - χαμηλές/μέσες θερμοκρασίες, καλό για αντλία."
    if emission_type == "Μικτό σύστημα":
        return w_per_m2 * 1.05, "Μικτό σύστημα - κρατάμε λίγο παραπάνω απόθεμα."

    return w_per_m2 * 1.05, "Καλοριφέρ - πιθανότατα χρειάζονται υψηλότερες θερμοκρασίες."


def estimate_heat_pump_kw(answers: HeatPumpQuestionnaire) -> tuple[tuple[float, float, float] | None, float | None, list[str]]:
    if answers.area_m2 is None or answers.area_m2 <= 0:
        return None, None, ["Δεν δόθηκαν m², δεν μπορεί να γίνει εκτίμηση."]

    w_per_m2 = base_w_per_m2_for_year(answers.year_category)
    notes = [f"Αρχική βάση: {w_per_m2:.0f} W/m² για {answers.year_category}."]

    reduction = renovation_reduction(answers.renovation_done, answers.renovation_options)
    if reduction:
        w_per_m2 *= 1 - reduction
        notes.append(f"Μείωση λόγω ενεργειακών επεμβάσεων: {reduction * 100:.0f}%.")

    w_per_m2, home_note = apply_home_type_adjustment(
        w_per_m2,
        answers.house_type,
        answers.apt_floor_position,
    )
    notes.append(home_note)

    w_per_m2, emitter_note = apply_emitter_adjustment(w_per_m2, answers.emission_type)
    notes.append(emitter_note)
    notes.append(f"Τελική βάση υπολογισμού: ~{w_per_m2:.0f} W/m² μετά τις διορθώσεις.")

    if answers.boiler_power_known == YES and answers.boiler_power_value and answers.boiler_power_value > 0:
        if answers.boiler_power_unit == "kW":
            kw_from_boiler = answers.boiler_power_value
        else:
            kw_from_boiler = answers.boiler_power_value / 860.0
        notes.append(f"Δήλωση ισχύος υπάρχοντος λέβητα: ~{kw_from_boiler:.1f} kW (μόνο ως ένδειξη).")

    if answers.fuel_consumption_known == YES and answers.fuel_consumption_value and answers.fuel_consumption_value > 0:
        if answers.fuel_consumption_type and answers.fuel_consumption_type.startswith("Ποσότητα"):
            notes.append(
                f"Δηλωμένη κατανάλωση καυσίμου: {answers.fuel_consumption_value:.0f} λίτρα/κιλά (ενδεικτικό)."
            )
        elif answers.fuel_consumption_type:
            notes.append(f"Δηλωμένο κόστος καυσίμου: {answers.fuel_consumption_value:.0f} € (ενδεικτικό).")

    avg_kw = answers.area_m2 * w_per_m2 / 1000
    low_kw = max(0, avg_kw * 0.85)
    high_kw = avg_kw * 1.15
    return (low_kw, high_kw, avg_kw), w_per_m2, notes


def pick_model_for_kw(avg_kw: float | None) -> tuple[HeatPumpModel | None, HeatPumpModel | None, float | None]:
    if avg_kw is None:
        return None, None, None

    target_kw = avg_kw * 1.05
    primary_models = primary_heat_pump_models()
    suitable = [model for model in primary_models if model.kw >= target_kw]
    selected = suitable[0] if suitable else primary_models[-1]

    alternative = None
    compact_model = compact_9kw_model()
    if compact_model and 8 < target_kw <= compact_model.kw and selected.kw == 10:
        alternative = compact_model

    return selected, alternative, target_kw


def compatible_heat_pump_models(
    target_kw: float | None,
    models: list[HeatPumpModel] | None = None,
) -> list[HeatPumpModel]:
    models = models or AVAILABLE_MODELS
    if target_kw is None:
        return []

    compatible = [model for model in models if model.kw >= target_kw]
    if not compatible:
        compatible = [max(models, key=lambda model: model.kw)]

    return sorted(compatible, key=lambda model: (model.price, model.kw, model.display_name))


def quote_heat_pump_model_alternative(
    model: HeatPumpModel,
    answers: HeatPumpQuestionnaire,
    cheapest_total_cost: float,
) -> HeatPumpAlternativeQuote:
    pump_cost = model.price
    labor_materials_cost = labor_materials_for_kw(model.kw)
    solar_cost = solar_cost_for_answers(answers)
    total_cost = pump_cost + labor_materials_cost + solar_cost
    subsidy_rate = subsidy_rate_for_answers(answers)
    subsidy_amount = total_cost * subsidy_rate
    customer_contribution = total_cost - subsidy_amount

    monthly_installment = None
    installment_total = None
    if answers.wants_installments == YES and customer_contribution > 0:
        monthly_installment = annuity_payment(customer_contribution)
        installment_total = monthly_installment * INSTALLMENT_MONTHS

    return HeatPumpAlternativeQuote(
        model=model,
        pump_cost=pump_cost,
        labor_materials_cost=labor_materials_cost,
        solar_cost=solar_cost,
        total_cost=total_cost,
        subsidy_rate=subsidy_rate,
        subsidy_amount=subsidy_amount,
        customer_contribution=customer_contribution,
        monthly_installment=monthly_installment,
        installment_total=installment_total,
        additional_cost=max(total_cost - cheapest_total_cost, 0),
    )


def heat_pump_alternative_quotes(
    models: list[HeatPumpModel],
    answers: HeatPumpQuestionnaire,
) -> list[HeatPumpAlternativeQuote]:
    raw_totals = [
        model.price + labor_materials_for_kw(model.kw) + solar_cost_for_answers(answers)
        for model in models
    ]
    cheapest_total_cost = min(raw_totals) if raw_totals else 0
    return [
        quote_heat_pump_model_alternative(
            model=model,
            answers=answers,
            cheapest_total_cost=cheapest_total_cost,
        )
        for model in models
    ]


def labor_materials_for_kw(kw: int) -> float:
    if kw == 8:
        return 1820
    if kw == 9:
        return 1875
    return 1820 * kw / 8


def solar_cost_for_answers(answers: HeatPumpQuestionnaire) -> float:
    if answers.interest_type != "Αντλία & Ηλιακός":
        return 0
    if answers.solar_people_band == "3–4 άτομα":
        return 1800
    if answers.solar_people_band == "4–5 άτομα":
        return 2200
    if answers.solar_people_band == "Πάνω από 5 άτομα":
        return 2600
    return 2000


def subsidy_rate_for_answers(answers: HeatPumpQuestionnaire) -> float:
    if answers.program_purchase != YES:
        return 0
    if answers.funding_rate_choice == "60%":
        return 0.60
    return 0.50


def annuity_payment(
    principal: float,
    months: int = INSTALLMENT_MONTHS,
    annual_rate: float = ANNUAL_INSTALLMENT_RATE,
) -> float:
    if principal <= 0:
        return 0
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal / months
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** (-months))


def calculate_heat_pump_offer(answers: HeatPumpQuestionnaire) -> HeatPumpOfferResult:
    hp_result, adjusted_w_per_m2, notes = estimate_heat_pump_kw(answers)
    if hp_result is None:
        return HeatPumpOfferResult(
            low_kw=None,
            high_kw=None,
            avg_kw=None,
            target_kw=None,
            adjusted_w_per_m2=adjusted_w_per_m2,
            selected_model=None,
            alternative_model=None,
            notes=notes,
            pump_cost=0,
            labor_materials_cost=0,
            solar_cost=0,
            total_cost=0,
            subsidy_rate=subsidy_rate_for_answers(answers),
            subsidy_amount=0,
            customer_contribution=0,
            monthly_installment=None,
            installment_total=None,
        )

    low_kw, high_kw, avg_kw = hp_result
    selected_model, alternative_model, target_kw = pick_model_for_kw(avg_kw)
    if selected_model is None:
        pump_cost = 0
        labor_materials_cost = 0
    else:
        pump_cost = selected_model.price
        labor_materials_cost = labor_materials_for_kw(selected_model.kw)

    solar_cost = solar_cost_for_answers(answers)
    total_cost = pump_cost + labor_materials_cost + solar_cost
    subsidy_rate = subsidy_rate_for_answers(answers)
    subsidy_amount = total_cost * subsidy_rate
    customer_contribution = total_cost - subsidy_amount

    monthly_installment = None
    installment_total = None
    if answers.wants_installments == YES and customer_contribution > 0:
        monthly_installment = annuity_payment(customer_contribution)
        installment_total = monthly_installment * INSTALLMENT_MONTHS

    return HeatPumpOfferResult(
        low_kw=low_kw,
        high_kw=high_kw,
        avg_kw=avg_kw,
        target_kw=target_kw,
        adjusted_w_per_m2=adjusted_w_per_m2,
        selected_model=selected_model,
        alternative_model=alternative_model,
        notes=notes,
        pump_cost=pump_cost,
        labor_materials_cost=labor_materials_cost,
        solar_cost=solar_cost,
        total_cost=total_cost,
        subsidy_rate=subsidy_rate,
        subsidy_amount=subsidy_amount,
        customer_contribution=customer_contribution,
        monthly_installment=monthly_installment,
        installment_total=installment_total,
    )


def format_euro(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} €"


def format_euro_rounded(value: float) -> str:
    formatted = f"{value:,.0f}".replace(",", ".")
    return f"{formatted} €"


def heat_pump_alternatives_for_display(
    quotes: list[HeatPumpAlternativeQuote],
) -> list[dict[str, str]]:
    rows = []
    for quote in quotes:
        model = quote.model
        rows.append(
            {
                "Μοντέλο": model.display_name,
                "Σειρά": model.series,
                "Ισχύς": f"{model.kw} kW",
                "Τάση": model.voltage or "-",
                "Τιμή αντλίας": format_euro_rounded(quote.pump_cost),
                "Εργασίες & υλικά": format_euro_rounded(quote.labor_materials_cost),
                "Σύνολο προ επιδότησης": format_euro_rounded(quote.total_cost),
                "Επιπλέον από οικονομικότερη": format_euro_rounded(quote.additional_cost),
                "Συμμετοχή πελάτη": format_euro_rounded(quote.customer_contribution),
                "ERP": model.erp_code or "-",
                "Περιγραφή": model.description,
            }
        )
    return rows


def _indent_multiline(text: str, prefix: str = "  ") -> str:
    return prefix + text.replace("\n", "\n" + prefix)


def generate_heat_pump_summary(
    answers: HeatPumpQuestionnaire,
    offer: HeatPumpOfferResult | None = None,
    created_at: datetime | None = None,
) -> str:
    created_at = created_at or datetime.now()
    offer = offer or calculate_heat_pump_offer(answers)

    lines: list[str] = [
        "=== ΕΡΩΤΗΜΑΤΟΛΟΓΙΟ ΑΝΤΛΙΑΣ ΘΕΡΜΟΤΗΤΑΣ ===",
        f"Ημερομηνία: {created_at.strftime('%d/%m/%Y %H:%M')}",
        "",
        "1) Επιθυμίες & Τρόπος Αγοράς",
        f"- Εγκατάσταση: {answers.install_interest}",
        f"- Αγορά μέσω προγράμματος: {answers.program_purchase}",
    ]
    if answers.program_purchase == YES:
        lines.append(f"- Ποσοστό χρηματοδότησης: {answers.funding_rate_choice or '50%'}")

    lines.extend(
        [
            f"- Ενδιαφέρον: {answers.interest_type}",
            f"- Μελέτη μηχανικού: {answers.has_engineer_study}",
            f"- Δόσεις 36 μηνών: {answers.wants_installments}",
        ]
    )
    if answers.interest_type == "Αντλία & Ηλιακός":
        lines.append(f"- Ηλιακός: άτομα στο σπίτι: {answers.solar_people_band or '—'}")

    lines.extend(
        [
            "",
            "2) Στοιχεία Κατοικίας",
            f"- Τύπος κατοικίας: {answers.house_type}",
            f"- Θέση στο κτήριο: {answers.apt_floor_position}",
            f"- Εμβαδόν: {answers.area_m2} m²",
            f"- Χρονολογία κατασκευής: {answers.year_category}",
            f"- Έργο: {answers.project_type}",
            f"- Ανακαίνιση/ενεργειακή αναβάθμιση: {answers.renovation_done}",
        ]
    )
    if answers.renovation_done == YES:
        lines.append(f"  Επεμβάσεις: {', '.join(answers.renovation_options) if answers.renovation_options else '—'}")
        if answers.renovation_other:
            lines.append(f"  Άλλες επεμβάσεις: {answers.renovation_other}")

    lines.extend(
        [
            f"- Ρεύμα: {answers.power_type}",
            f"- Χρήση αντλίας: {answers.usage_type}",
        ]
    )
    if "ΖΝΧ" in answers.usage_type:
        lines.append(f"- Άτομα για ΖΝΧ: {answers.znx_people}")

    lines.extend(
        [
            "",
            "3) Υφιστάμενο Σύστημα Θέρμανσης",
            f"- Αλλαγή/προσθήκη σωμάτων: {answers.change_radiators}",
            f"- Τρόπος θέρμανσης: {answers.distribution_type}",
            f"- Τύπος εκπομπής: {answers.emission_type}",
            f"- Τύπος λέβητα/πηγής: {answers.boiler_type}",
        ]
    )
    if answers.boiler_type == "Άλλο" and answers.boiler_other:
        lines.append(f"  Περιγραφή: {answers.boiler_other}")
    lines.append(f"- Γνωστή ισχύς λέβητα: {answers.boiler_power_known}")
    if answers.boiler_power_known == YES and answers.boiler_power_value is not None:
        lines.append(f"  Ισχύς λέβητα: {answers.boiler_power_value} {answers.boiler_power_unit}")

    lines.extend(
        [
            "",
            "Κατανάλωση καυσίμου προηγούμενης σεζόν",
            f"- Γνωστή κατανάλωση: {answers.fuel_consumption_known}",
        ]
    )
    if answers.fuel_consumption_known == YES and answers.fuel_consumption_value is not None:
        if answers.fuel_consumption_type and answers.fuel_consumption_type.startswith("Ποσότητα"):
            lines.append(f"  Ποσότητα: {answers.fuel_consumption_value} λίτρα/κιλά")
        elif answers.fuel_consumption_type:
            lines.append(f"  Ποσό: {answers.fuel_consumption_value} €")

    lines.extend(
        [
            "",
            "4) Πρόσθετα Συστήματα & Τοποθέτηση",
            f"- Ηλιακός θερμοσίφωνας: {answers.has_solar}",
            f"- Φωτοβολταϊκά: {answers.has_pv}",
            f"- Διαθέσιμος εξωτερικός χώρος: {answers.has_outdoor_space}",
        ]
    )
    if answers.outdoor_desc:
        lines.append("  Περιγραφή χώρου:")
        lines.append(_indent_multiline(answers.outdoor_desc))

    lines.append(f"- Περιορισμοί θορύβου: {answers.noise_limits}")
    if answers.noise_desc:
        lines.append("  Περιγραφή θορύβου:")
        lines.append(_indent_multiline(answers.noise_desc))
    if answers.comments:
        lines.extend(["", "Σχόλια / Παρατηρήσεις:", answers.comments])

    lines.extend(
        [
            "",
            "5) Στοιχεία Επικοινωνίας",
            f"- Ονοματεπώνυμο: {answers.name}",
            f"- Τηλέφωνο: {answers.phone}",
            f"- Email: {answers.email}",
            f"- Διεύθυνση ακινήτου: {answers.address}",
            "",
            "6) Ενδεικτική προτεινόμενη ισχύς αντλίας",
        ]
    )
    if offer.has_estimate and offer.selected_model:
        lines.append(f"- Εκτιμώμενο εύρος: {offer.kw_range_label}")
        lines.append(f"- Στόχος επιλογής με safety factor 5%: {offer.target_kw:.1f} kW")
        lines.append(f"- Προτεινόμενο μοντέλο: {offer.selected_model.name} (~{offer.selected_model.kw} kW)")
        if offer.alternative_model:
            lines.append(
                f"- Εναλλακτικό μόνο αν χρειαστεί: {offer.alternative_model.name} "
                f"({format_euro_rounded(offer.alternative_model.price)})"
            )
        lines.append("- Σημειώσεις υπολογισμού:")
        for note in offer.notes:
            lines.append(f"  - {note}")
        lines.append("ΠΡΟΣΟΧΗ: Η ισχύς λέβητα και η κατανάλωση καυσίμου είναι πληροφοριακά μόνο.")
    else:
        lines.append("- Δεν μπορεί να γίνει εκτίμηση (λείπουν βασικά στοιχεία m²).")

    lines.extend(["", "7) Ενδεικτική τάξη μεγέθους κόστους"])
    if offer.has_estimate:
        lines.append(f"- Αντλία: {format_euro_rounded(offer.pump_cost)}")
        lines.append(f"- Εργασίες & υλικά: {format_euro_rounded(offer.labor_materials_cost)}")
        if offer.solar_cost:
            lines.append(f"- Ηλιακός: {format_euro_rounded(offer.solar_cost)}")
        lines.append(f"- Σύνολο προ επιδότησης: {format_euro_rounded(offer.total_cost)}")
        lines.append(f"- Ποσοστό επιδότησης: {offer.subsidy_rate * 100:.0f}%")
        lines.append(f"- Επιδότηση: {format_euro_rounded(offer.subsidy_amount)}")
        lines.append(f"- Συμμετοχή πελάτη: {format_euro_rounded(offer.customer_contribution)}")
        if offer.monthly_installment is not None:
            lines.append(
                f"- 36 δόσεις με 13% ετήσιο σταθερό επιτόκιο: "
                f"{format_euro_rounded(offer.monthly_installment)} / μήνα"
            )
    else:
        lines.append("- Δεν υπολογίστηκε κόστος.")

    return "\n".join(lines)
