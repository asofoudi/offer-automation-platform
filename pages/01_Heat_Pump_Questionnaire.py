from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from utils.heat_pump_questionnaire import (
    ANNUAL_INSTALLMENT_RATE,
    INSTALLMENT_MONTHS,
    HeatPumpOfferResult,
    HeatPumpQuestionnaire,
    calculate_heat_pump_offer,
    compatible_heat_pump_models,
    format_euro_rounded,
    generate_heat_pump_summary,
    heat_pump_alternative_quotes,
    heat_pump_alternatives_for_display,
)

try:
    from utils.pdf_offer import (
        FinancingOption,
        GreekFontError,
        OfferTotals,
        ProductLine,
        create_offer_pdf,
    )
except ModuleNotFoundError as exc:
    FinancingOption = None
    GreekFontError = RuntimeError
    OfferTotals = None
    ProductLine = None
    create_offer_pdf = None
    PDF_IMPORT_ERROR = exc
else:
    PDF_IMPORT_ERROR = None


YES = "Ναι"
NO = "Όχι"
NOT_SURE = "Δεν γνωρίζω"

PRE_COSTING_DISCLAIMER = (
    "Η παρούσα προσφορά είναι προκοστολόγηση βάσει των στοιχείων του ερωτηματολογίου. "
    "Δεν αποτελεί τελική τεχνική μελέτη ή δεσμευτική οικονομική προσφορά. "
    "Η τελική επιλογή μοντέλου, η απαιτούμενη ισχύς, οι εργασίες εγκατάστασης, "
    "η επιδότηση και οι δόσεις επιβεβαιώνονται μετά από τεχνικό έλεγχο, "
    "διαθεσιμότητα προϊόντων και έλεγχο επιλεξιμότητας προγράμματος."
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_heat_pump_pdf(
    *,
    answers: HeatPumpQuestionnaire,
    offer: HeatPumpOfferResult,
    selected_quotes: list,
    submitted_at: datetime,
) -> bytes:
    kw_label = offer.kw_range_label
    base_quote = min(selected_quotes, key=lambda quote: quote.total_cost)

    products = []
    for quote in selected_quotes:
        model = quote.model
        notes = [
            f"Εκτιμώμενη περιοχή ισχύος: {kw_label}",
            f"Ισχύς μοντέλου: {model.kw} kW",
            f"Σειρά: {model.series}",
            f"Τάση: {model.voltage or 'Προς επιβεβαίωση'}",
            f"Τιμή αντλίας: {format_euro_rounded(quote.pump_cost)}",
            f"Εργασίες & υλικά: {format_euro_rounded(quote.labor_materials_cost)}",
            f"Επιπλέον κόστος από την οικονομικότερη συμβατή επιλογή: {format_euro_rounded(quote.additional_cost)}",
            f"Συμμετοχή πελάτη μετά την επιδότηση: {format_euro_rounded(quote.customer_contribution)}",
            f"Τύπος εκπομπής: {answers.emission_type}",
            f"Χρήση: {answers.usage_type}",
        ]
        if model.cop:
            notes.append(f"COP: {model.cop}")
        if model.dimensions:
            notes.append(f"Διαστάσεις: {model.dimensions}")
        if model.erp_code:
            notes.append(f"ERP: {model.erp_code}")
        if model.description:
            notes.append(model.description)
        if quote.solar_cost:
            notes.append(f"Περιλαμβάνεται ηλιακός: {format_euro_rounded(quote.solar_cost)}")
        if quote.monthly_installment is not None:
            notes.append(
                f"{INSTALLMENT_MONTHS} δόσεις: {format_euro_rounded(quote.monthly_installment)} / μήνα"
            )

        products.append(
            ProductLine(
                description=f"Εναλλακτική αντλίας θερμότητας: {model.display_name}",
                quantity=1,
                unit="πακέτο",
                unit_price=quote.total_cost,
                total_price=quote.total_cost,
                notes="\n".join(notes),
            )
        )

    totals = OfferTotals(
        subtotal=base_quote.total_cost,
        discount=base_quote.subsidy_amount,
        vat_rate=0,
        vat_amount=0,
        total=base_quote.customer_contribution,
    )

    financing_options = []
    if base_quote.monthly_installment is not None and base_quote.installment_total is not None:
        financing_options.append(
            FinancingOption(
                name=f"{INSTALLMENT_MONTHS} μηνιαίες δόσεις",
                installments=INSTALLMENT_MONTHS,
                monthly_amount=base_quote.monthly_installment,
                total_amount=base_quote.installment_total,
                note=f"Υπολογισμός με ετήσιο σταθερό επιτόκιο {ANNUAL_INSTALLMENT_RATE * 100:.0f}%.",
            )
        )

    customer = {
        "full_name": answers.name,
        "phone": answers.phone,
        "email": answers.email,
        "area": answers.address,
        "comments": "\n".join(
            [
                answers.comments,
                f"Στα σύνολα εμφανίζεται η οικονομικότερη επιλεγμένη εναλλακτική: {base_quote.model.display_name}.",
            ]
        ).strip(),
    }

    return create_offer_pdf(
        customer=customer,
        products=products,
        offer_title="Προσφορά αντλίας θερμότητας",
        offer_number=f"HP-{submitted_at.strftime('%Y%m%d-%H%M')}",
        offer_date=submitted_at.date(),
        totals=totals,
        financing_options=financing_options,
        disclaimer=(
            f"{PRE_COSTING_DISCLAIMER}\n\n"
            "Το PDF περιλαμβάνει μόνο τις επιλεγμένες εναλλακτικές αντλιών θερμότητας. "
            f"Τα σύνολα υπολογίζονται με βάση την οικονομικότερη επιλεγμένη εναλλακτική: {base_quote.model.display_name}."
        ),
    )


def resolve_model_image_path(image_path: str) -> Path | None:
    if not image_path:
        return None
    path = Path(image_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path if path.exists() else None


def result_rows(offer: HeatPumpOfferResult) -> list[dict[str, str]]:
    rows = [
        {"Κατηγορία": "Αντλία", "Ποσό": format_euro_rounded(offer.pump_cost)},
        {"Κατηγορία": "Εργασίες & υλικά", "Ποσό": format_euro_rounded(offer.labor_materials_cost)},
    ]
    if offer.solar_cost:
        rows.append({"Κατηγορία": "Ηλιακός", "Ποσό": format_euro_rounded(offer.solar_cost)})

    rows.extend(
        [
            {"Κατηγορία": "Σύνολο προ επιδότησης", "Ποσό": format_euro_rounded(offer.total_cost)},
            {"Κατηγορία": f"Επιδότηση {offer.subsidy_rate * 100:.0f}%", "Ποσό": f"-{format_euro_rounded(offer.subsidy_amount)}"},
            {"Κατηγορία": "Συμμετοχή πελάτη", "Ποσό": format_euro_rounded(offer.customer_contribution)},
        ]
    )
    return rows


st.set_page_config(
    page_title="Ερωτηματολόγιο Αντλίας Θερμότητας",
    page_icon="🔥",
    layout="wide",
)

st.title("Αλλαγή Συστήματος Θέρμανσης - Επιλογή Αντλίας Θερμότητας")
st.markdown(
    "Συμπληρώστε τις παρακάτω πληροφορίες ώστε να μπορέσουμε να προτείνουμε "
    "ενδεικτική ισχύ, μοντέλο και προκοστολόγηση αντλίας θερμότητας."
)

st.divider()

st.subheader("1. Επιθυμίες & τρόπος αγοράς")
col1, col2 = st.columns(2)
with col1:
    install_interest = st.radio(
        "Σας ενδιαφέρει και η εγκατάσταση;",
        [YES, NO],
        horizontal=True,
    )
with col2:
    program_purchase = st.radio(
        "Η αγορά θα γίνει μέσω προγράμματος επιδότησης;",
        [YES, NO, "Δεν γνωρίζω ακόμη"],
        horizontal=True,
    )

funding_rate_choice = None
if program_purchase == YES:
    funding_rate_choice = st.radio(
        "Ποσοστό χρηματοδότησης",
        ["50%", "60%", "Δεν γνωρίζω / δεν έχει οριστεί"],
        horizontal=True,
    )

col3, col4 = st.columns(2)
with col3:
    interest_type = st.radio(
        "Ενδιαφέρεστε για:",
        ["Μόνο Αντλία Θερμότητας", "Αντλία & Ηλιακός"],
    )
with col4:
    has_engineer_study = st.radio(
        "Έχετε μελέτη μηχανικού για την απαιτούμενη ισχύ;",
        [YES, NO],
        horizontal=True,
    )

wants_installments = st.radio(
    f"Σας ενδιαφέρει πλάνο {INSTALLMENT_MONTHS} δόσεων;",
    [NO, YES],
    horizontal=True,
)

solar_people_band = None
if interest_type == "Αντλία & Ηλιακός":
    solar_people_band = st.radio(
        "Για τον ηλιακό, πόσα άτομα θα μένουν στο σπίτι;",
        ["3–4 άτομα", "4–5 άτομα", "Πάνω από 5 άτομα"],
        horizontal=True,
    )

st.divider()

st.subheader("2. Στοιχεία κατοικίας")
col5, col6 = st.columns(2)
with col5:
    house_type = st.radio("Τύπος κατοικίας:", ["Μονοκατοικία", "Διαμέρισμα"])
with col6:
    area_m2 = st.number_input("Εμβαδόν κατοικίας (m²)", min_value=0.0, step=1.0)

year_category = st.selectbox(
    "Χρονολογία κατασκευής:",
    ["Πριν το 1980", "1980–2000", "2001–2009", "2010 και μετά"],
)

apt_floor_position = st.radio(
    "Θέση κατοικίας στο κτήριο",
    ["Δεν ισχύει (μονοκατοικία)", "Ενδιάμεσος όροφος", "Τελευταίος όροφος / ρετιρέ"],
)

renovation_done = st.radio(
    "Έχει γίνει ανακαίνιση / ενεργειακή αναβάθμιση;",
    [NO, YES],
    horizontal=True,
)
renovation_options = []
renovation_other = ""
if renovation_done == YES:
    renovation_options = st.multiselect(
        "Τι έχει γίνει;",
        [
            "Θερμομόνωση κελύφους",
            "Θερμομόνωση δώματος / ταράτσας",
            "Αντικατάσταση κουφωμάτων",
            "Αλλαγή λεβητοστασίου / συστήματος",
            "Άλλο",
        ],
    )
    if "Άλλο" in renovation_options:
        renovation_other = st.text_input("Περιγράψτε άλλες επεμβάσεις:")

project_type = st.radio(
    "Το έργο αφορά:",
    ["Απλή αντικατάσταση", "Ανακαίνιση", "Νεόδμητο σπίτι"],
)

col7, col8 = st.columns(2)
with col7:
    power_type = st.radio("Ρεύμα κατοικίας:", ["Μονοφασικό", "Τριφασικό", NOT_SURE])
with col8:
    usage_type = st.radio(
        "Τι ζητάτε από την αντλία;",
        ["Μόνο Θέρμανση", "Θέρμανση & ΖΝΧ", "Θέρμανση, ΖΝΧ & Ψύξη"],
    )

znx_people = None
if "ΖΝΧ" in usage_type:
    znx_people = st.number_input(
        "Αν χρειάζεστε ΖΝΧ, πόσα άτομα θα μένουν στο σπίτι;",
        min_value=0,
        step=1,
    )

st.divider()

st.subheader("3. Υφιστάμενο σύστημα θέρμανσης")
change_radiators = st.radio(
    "Θα χρειαστεί αλλαγή ή προσθήκη σε θερμαντικό σώμα;",
    [YES, NO, NOT_SURE],
    horizontal=True,
)

distribution_type = st.radio(
    "Τώρα με τι σύστημα ζεσταίνεστε;",
    ["Κεντρικό", "Αυτόνομο"],
    horizontal=True,
)

emission_type = st.radio(
    "Με τι θερμαίνεται ο χώρος;",
    ["Καλοριφέρ (σώματα)", "Ενδοδαπέδια", "Fan coil", "Μικτό σύστημα"],
)

boiler_type = st.selectbox(
    "Τύπος λέβητα / πηγής θερμότητας:",
    ["Λέβητας πετρελαίου", "Λέβητας φυσικού αερίου", "Λέβητας pellet", "Ξυλολέβητας", "Άλλο"],
)
boiler_other = ""
if boiler_type == "Άλλο":
    boiler_other = st.text_input("Περιγραφή άλλου τύπου λέβητα / συστήματος:")

boiler_power_known = st.radio(
    "Γνωρίζετε την ονομαστική ισχύ του υπάρχοντος λέβητα;",
    [YES, NO],
    horizontal=True,
)
boiler_power_unit = None
boiler_power_value = None
if boiler_power_known == YES:
    boiler_power_unit = st.selectbox("Μονάδα ισχύος:", ["kW", "kcal/h"])
    boiler_power_value = st.number_input("Ισχύς λέβητα", min_value=0.0, step=0.1)

st.markdown("### Κατανάλωση καυσίμου προηγούμενης σεζόν")
fuel_consumption_known = st.radio(
    "Γνωρίζετε περίπου την κατανάλωση καυσίμου την προηγούμενη σεζόν;",
    [YES, NO],
    horizontal=True,
)
fuel_consumption_type = None
fuel_consumption_value = None
if fuel_consumption_known == YES:
    fuel_consumption_type = st.radio(
        "Σε τι μονάδα μπορείτε να την δώσετε;",
        ["Ποσότητα (λίτρα / κιλά)", "Ποσό σε €"],
    )
    if fuel_consumption_type.startswith("Ποσότητα"):
        fuel_consumption_value = st.number_input("Ποσότητα καυσίμου (λίτρα / κιλά)", min_value=0.0, step=1.0)
    else:
        fuel_consumption_value = st.number_input("Κόστος καυσίμου την προηγούμενη σεζόν (€)", min_value=0.0, step=50.0)

st.divider()

st.subheader("4. Πρόσθετα συστήματα & τοποθέτηση")
col9, col10 = st.columns(2)
with col9:
    has_solar = st.radio("Έχετε ηλιακό θερμοσίφωνα;", [YES, NO], horizontal=True)
with col10:
    has_pv = st.radio("Υπάρχουν φωτοβολταϊκά;", [YES, NO], horizontal=True)

has_outdoor_space = st.radio(
    "Υπάρχει διαθέσιμος εξωτερικός χώρος για την αντλία θερμότητας;",
    [YES, NO],
    horizontal=True,
)
outdoor_desc = st.text_area(
    "Αν ναι, περιγράψτε τον χώρο (μπαλκόνι, ταράτσα, αυλή κ.λπ.):",
    height=80,
)

noise_limits = st.radio(
    "Υπάρχουν περιορισμοί θορύβου;",
    [YES, NO],
    horizontal=True,
)
noise_desc = st.text_area("Αν ναι, περιγράψτε:", height=80)

comments = st.text_area(
    "Σχόλια / Παρατηρήσεις",
    height=100,
)

st.divider()

st.subheader("5. Στοιχεία επικοινωνίας")
col11, col12 = st.columns(2)
with col11:
    name = st.text_input("Ονοματεπώνυμο")
    phone = st.text_input("Τηλέφωνο")
with col12:
    email = st.text_input("Email")
    address = st.text_input("Διεύθυνση ακινήτου (πόλη / περιοχή)")

submitted = st.button("Υποβολή ερωτηματολογίου", type="primary")

if submitted:
    submitted_at = datetime.now()
    for key in list(st.session_state.keys()):
        if str(key).startswith("heat_pump_offer_model_"):
            del st.session_state[key]

    answers = HeatPumpQuestionnaire(
        install_interest=install_interest,
        program_purchase=program_purchase,
        funding_rate_choice=funding_rate_choice,
        wants_installments=wants_installments,
        interest_type=interest_type,
        solar_people_band=solar_people_band,
        has_engineer_study=has_engineer_study,
        house_type=house_type,
        area_m2=area_m2,
        year_category=year_category,
        apt_floor_position=apt_floor_position,
        renovation_done=renovation_done,
        renovation_options=renovation_options,
        renovation_other=renovation_other,
        project_type=project_type,
        power_type=power_type,
        usage_type=usage_type,
        znx_people=znx_people,
        change_radiators=change_radiators,
        distribution_type=distribution_type,
        emission_type=emission_type,
        boiler_type=boiler_type,
        boiler_other=boiler_other,
        boiler_power_known=boiler_power_known,
        boiler_power_unit=boiler_power_unit,
        boiler_power_value=boiler_power_value,
        fuel_consumption_known=fuel_consumption_known,
        fuel_consumption_type=fuel_consumption_type,
        fuel_consumption_value=fuel_consumption_value,
        has_solar=has_solar,
        has_pv=has_pv,
        has_outdoor_space=has_outdoor_space,
        outdoor_desc=outdoor_desc,
        noise_limits=noise_limits,
        noise_desc=noise_desc,
        comments=comments,
        name=name,
        phone=phone,
        email=email,
        address=address,
    )
    offer = calculate_heat_pump_offer(answers)
    summary_text = generate_heat_pump_summary(answers, offer=offer, created_at=submitted_at)

    st.session_state["heat_pump_answers"] = answers
    st.session_state["heat_pump_offer"] = offer
    st.session_state["heat_pump_summary_text"] = summary_text
    st.session_state["heat_pump_submitted_at"] = submitted_at

if "heat_pump_answers" in st.session_state:
    answers = st.session_state["heat_pump_answers"]
    offer = st.session_state["heat_pump_offer"]
    summary_text = st.session_state["heat_pump_summary_text"]
    submitted_at = st.session_state["heat_pump_submitted_at"]

    st.success("Η υποβολή καταχωρήθηκε. Δείτε παρακάτω την εκτίμηση και τα αρχεία προσφοράς.")

    selected_alternative_quotes = []

    if offer.has_estimate and offer.selected_model:
        st.subheader("6. Πρόταση αντλίας")
        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Προτεινόμενο μοντέλο", offer.selected_model.display_name)
        metric2.metric("Εκτιμώμενη ισχύς", offer.kw_range_label)
        metric3.metric("Βάση υπολογισμού", f"{offer.adjusted_w_per_m2:.0f} W/m²")

        if offer.alternative_model:
            st.info(
                f"Εναλλακτικά, μόνο αν κριθεί τεχνικά επαρκές, μπορεί να εξεταστεί "
                f"{offer.alternative_model.display_name} με τιμή {format_euro_rounded(offer.alternative_model.price)}."
            )

        with st.expander("Σημειώσεις υπολογισμού ισχύος", expanded=False):
            for note in offer.notes:
                st.write(f"- {note}")
            st.caption("Η ισχύς λέβητα και η κατανάλωση καυσίμου παραμένουν πληροφοριακά στοιχεία μόνο.")

        st.subheader("7. Κόστος και συμμετοχή πελάτη")
        st.dataframe(result_rows(offer), hide_index=True, use_container_width=True)

        cost_col1, cost_col2, cost_col3 = st.columns(3)
        cost_col1.metric("Σύνολο προ επιδότησης", format_euro_rounded(offer.total_cost))
        cost_col2.metric("Επιδότηση", format_euro_rounded(offer.subsidy_amount))
        cost_col3.metric("Συμμετοχή πελάτη", format_euro_rounded(offer.customer_contribution))

        if offer.monthly_installment is not None:
            st.metric(
                f"{INSTALLMENT_MONTHS} δόσεις με {ANNUAL_INSTALLMENT_RATE * 100:.0f}% ετήσιο σταθερό επιτόκιο",
                f"{format_euro_rounded(offer.monthly_installment)} / μήνα",
                help="Υπολογισμός με τον κλασικό τύπο δανείου/annuity.",
            )

        compatible_models = compatible_heat_pump_models(offer.target_kw)
        alternative_quotes = heat_pump_alternative_quotes(compatible_models, answers)

        st.subheader("8. Συμβατές εναλλακτικές αντλιών")
        st.caption(
            "Οι παρακάτω επιλογές είναι συμβατές με τον υπολογισμένο στόχο kW. "
            "Το επιπλέον κόστος συγκρίνεται με την οικονομικότερη συμβατή επιλογή."
        )
        st.dataframe(
            heat_pump_alternatives_for_display(alternative_quotes),
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("### Επιλογή μοντέλων για την τελική προσφορά")
        for quote in alternative_quotes:
            model = quote.model
            checkbox_col, details_col, image_col = st.columns([1, 4, 2])
            with checkbox_col:
                selected = st.checkbox(
                    "Στην προσφορά",
                    value=model.model_id == offer.selected_model.model_id,
                    key=f"heat_pump_offer_model_{model.model_id}",
                )
            with details_col:
                st.markdown(f"**{model.display_name}**")
                st.write(
                    f"{model.series} | {model.kw} kW | "
                    f"Αντλία: {format_euro_rounded(quote.pump_cost)} | "
                    f"Σύνολο προ επιδότησης: {format_euro_rounded(quote.total_cost)} | "
                    f"Επιπλέον: {format_euro_rounded(quote.additional_cost)}"
                )
                if model.description:
                    st.caption(model.description)
            with image_col:
                image_path = resolve_model_image_path(model.image_path)
                if image_path is not None:
                    st.image(str(image_path), caption=model.display_name, use_column_width=True)
            if selected:
                selected_alternative_quotes.append(quote)

        st.subheader("9. Επιλεγμένα μοντέλα για την τελική προσφορά")
        if selected_alternative_quotes:
            st.dataframe(
                heat_pump_alternatives_for_display(selected_alternative_quotes),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.warning("Επιλέξτε τουλάχιστον ένα μοντέλο για να δημιουργηθεί το PDF προσφοράς.")
    else:
        st.warning("Δεν μπορεί να γίνει εκτίμηση ισχύος και κόστους χωρίς εμβαδόν κατοικίας.")
        for note in offer.notes:
            st.write(f"- {note}")

    st.subheader("10. Σύνοψη και αρχεία")
    st.download_button(
        "Κατέβασμα σύνοψης (TXT)",
        data=summary_text.encode("utf-8"),
        file_name="questionnaire_heat_pump.txt",
        mime="text/plain",
    )

    if PDF_IMPORT_ERROR is not None:
        st.error("Λείπει η βιβλιοθήκη `reportlab`. Εκτελέστε `pip install -r requirements.txt` για δημιουργία PDF.")
    elif not offer.has_estimate:
        st.info("Το PDF προσφοράς θα ενεργοποιηθεί μόλις υπάρχει έγκυρη εκτίμηση ισχύος.")
    elif not selected_alternative_quotes:
        st.info("Επιλέξτε τουλάχιστον ένα μοντέλο αντλίας για να ενεργοποιηθεί το PDF προσφοράς.")
    else:
        try:
            pdf_bytes = build_heat_pump_pdf(
                answers=answers,
                offer=offer,
                selected_quotes=selected_alternative_quotes,
                submitted_at=submitted_at,
            )
        except GreekFontError as exc:
            st.error(str(exc))
        else:
            st.download_button(
                "Λήψη PDF προσφοράς",
                data=pdf_bytes,
                file_name="prosfora_antlias_thermotitas.pdf",
                mime="application/pdf",
                type="primary",
            )

    with st.expander("Προβολή πλήρους σύνοψης", expanded=False):
        st.text(summary_text)

    st.info(PRE_COSTING_DISCLAIMER)
else:
    st.info("Συμπληρώστε τα στοιχεία και πατήστε «Υποβολή ερωτηματολογίου».")
