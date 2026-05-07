from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class HeatPumpQuestionnaire:
    install_interest: str
    program_purchase: str
    interest_type: str
    has_engineer_study: str
    house_type: str
    area_m2: float
    year_category: str
    project_type: str
    power_type: str
    usage_type: str
    znx_people: int | None
    change_radiators: str
    distribution_type: str
    boiler_type: str
    boiler_other: str
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


def _indent_multiline(text: str, prefix: str = "  ") -> str:
    return prefix + text.replace("\n", "\n" + prefix)


def generate_heat_pump_summary(
    answers: HeatPumpQuestionnaire,
    created_at: datetime | None = None,
) -> str:
    """Build the customer-folder text summary used by the original questionnaire."""
    created_at = created_at or datetime.now()

    lines: list[str] = [
        "=== ΕΡΩΤΗΜΑΤΟΛΟΓΙΟ ΑΝΤΛΙΑΣ ΘΕΡΜΟΤΗΤΑΣ ===",
        f"Ημερομηνία: {created_at.strftime('%d/%m/%Y %H:%M')}",
        "",
        "1) Επιθυμίες & τρόπος αγοράς",
        f"- Εγκατάσταση: {answers.install_interest}",
        f"- Αγορά μέσω προγράμματος: {answers.program_purchase}",
        f"- Ενδιαφέρον: {answers.interest_type}",
        f"- Μελέτη μηχανικού: {answers.has_engineer_study}",
        "",
        "2) Στοιχεία κατοικίας",
        f"- Τύπος κατοικίας: {answers.house_type}",
        f"- Εμβαδόν: {answers.area_m2} m²",
        f"- Χρονολογία κατασκευής: {answers.year_category}",
        f"- Έργο: {answers.project_type}",
        f"- Ρεύμα: {answers.power_type}",
        f"- Χρήση αντλίας: {answers.usage_type}",
    ]

    if "ΖΝΧ" in answers.usage_type:
        lines.append(f"- Άτομα για ΖΝΧ: {answers.znx_people}")

    lines.extend(
        [
            "",
            "3) Υφιστάμενο σύστημα θέρμανσης",
            f"- Αλλαγή/προσθήκη σωμάτων: {answers.change_radiators}",
            f"- Τρόπος θέρμανσης: {answers.distribution_type}",
            f"- Τύπος λέβητα/πηγής: {answers.boiler_type}",
        ]
    )
    if answers.boiler_type == "Άλλο" and answers.boiler_other:
        lines.append(f"  Περιγραφή: {answers.boiler_other}")

    lines.extend(
        [
            "",
            "4) Πρόσθετα συστήματα & τοποθέτηση",
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
        lines.extend(["", "Σχόλια / παρατηρήσεις:", answers.comments])

    lines.extend(
        [
            "",
            "5) Στοιχεία επικοινωνίας",
            f"- Ονοματεπώνυμο: {answers.name}",
            f"- Τηλέφωνο: {answers.phone}",
            f"- Email: {answers.email}",
            f"- Διεύθυνση ακινήτου: {answers.address}",
        ]
    )

    return "\n".join(lines)
