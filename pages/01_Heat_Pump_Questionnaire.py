from datetime import datetime

import streamlit as st

from utils.heat_pump_questionnaire import HeatPumpQuestionnaire, generate_heat_pump_summary

try:
    from utils.pdf_offer import (
        FinancingOption,
        GreekFontError,
        OfferTotals,
        ProductLine,
        create_offer_pdf,
        format_eur,
    )
except ModuleNotFoundError as exc:
    FinancingOption = None
    GreekFontError = RuntimeError
    OfferTotals = None
    ProductLine = None
    create_offer_pdf = None
    format_eur = None
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


def default_recommended_model(answers: HeatPumpQuestionnaire) -> str:
    if "ηλιακό" in answers.interest_type.lower():
        return "Αντλία θερμότητας αέρα-νερού με πρόβλεψη συνεργασίας με ηλιακό"
    return "Αντλία θερμότητας αέρα-νερού προς τελική επιλογή"


def default_kw_range(answers: HeatPumpQuestionnaire) -> str:
    if answers.has_engineer_study == YES:
        return "Σύμφωνα με τη μελέτη μηχανικού"
    return "Προς επιβεβαίωση με μελέτη θερμικών απωλειών"


def subsidy_requested(answers: HeatPumpQuestionnaire) -> bool:
    return answers.program_purchase.startswith(YES)


def build_heat_pump_pdf(
    *,
    answers: HeatPumpQuestionnaire,
    submitted_at: datetime,
    recommended_model: str,
    estimated_kw_range: str,
    cost_estimate: float,
    subsidy_amount: float,
    installments: int,
) -> bytes:
    applied_subsidy = min(subsidy_amount, cost_estimate) if cost_estimate else 0
    net_total = max(cost_estimate - applied_subsidy, 0)
    subsidy_text = (
        f"Ενδεικτική επιδότηση: {format_eur(applied_subsidy)}"
        if applied_subsidy
        else "Η επιδότηση θα επιβεβαιωθεί μετά τον έλεγχο επιλεξιμότητας."
    )
    model_notes = "\n".join(
        [
            f"Εκτιμώμενη περιοχή ισχύος: {estimated_kw_range or 'Προς επιβεβαίωση'}",
            f"Χρήση: {answers.usage_type}",
            f"Τύπος κατοικίας: {answers.house_type}, {answers.area_m2:g} m²",
            f"Υφιστάμενο σύστημα: {answers.boiler_type}",
            subsidy_text if subsidy_requested(answers) else "Χωρίς καταχωρημένη αγορά μέσω προγράμματος επιδότησης.",
        ]
    )

    products = [
        ProductLine(
            description=f"Προτεινόμενη λύση: {recommended_model or 'Προς τελική επιλογή'}",
            quantity=1,
            unit="σύστημα",
            unit_price=cost_estimate,
            notes=model_notes,
        )
    ]
    totals = OfferTotals(
        subtotal=cost_estimate,
        discount=applied_subsidy,
        vat_rate=0,
        vat_amount=0,
        total=net_total,
    )

    financing_options = []
    if installments and net_total:
        financing_options.append(
            FinancingOption(
                name=f"Ενδεικτικό πλάνο {installments} δόσεων",
                installments=installments,
                monthly_amount=net_total / installments,
                total_amount=net_total,
                note="Ενδεικτικός υπολογισμός δόσης χωρίς τραπεζική ή προγραμματική έγκριση.",
            )
        )

    customer = {
        "full_name": answers.name,
        "phone": answers.phone,
        "email": answers.email,
        "area": answers.address,
        "comments": answers.comments,
    }

    return create_offer_pdf(
        customer=customer,
        products=products,
        offer_title="Προκοστολόγηση αντλίας θερμότητας",
        offer_number=f"HP-{submitted_at.strftime('%Y%m%d-%H%M')}",
        offer_date=submitted_at.date(),
        totals=totals,
        financing_options=financing_options,
        disclaimer=PRE_COSTING_DISCLAIMER,
    )


st.set_page_config(
    page_title="Ερωτηματολόγιο Αντλίας Θερμότητας",
    page_icon="🔥",
    layout="wide",
)

st.title("Αλλαγή Συστήματος Θέρμανσης - Επιλογή Αντλίας Θερμότητας")
st.markdown(
    "Συμπληρώστε τις παρακάτω πληροφορίες ώστε να προτείνουμε την κατάλληλη "
    "αντλία θερμότητας για τον χώρο του πελάτη."
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
        [YES, NO, "Δεν γνωρίζω ακόμα"],
        horizontal=True,
    )

col3, col4 = st.columns(2)
with col3:
    interest_type = st.radio(
        "Ενδιαφέρεστε για:",
        ["Μόνο αντλία θερμότητας", "Αντλία & ηλιακό"],
    )
with col4:
    has_engineer_study = st.radio(
        "Έχετε μελέτη μηχανικού για την απαιτούμενη ισχύ;",
        [YES, NO],
        horizontal=True,
    )

st.divider()

st.subheader("2. Στοιχεία κατοικίας")
col5, col6 = st.columns(2)
with col5:
    house_type = st.radio(
        "Τύπος κατοικίας:",
        ["Μονοκατοικία", "Διαμέρισμα"],
    )
with col6:
    area_m2 = st.number_input(
        "Εμβαδόν κατοικίας (m²)",
        min_value=0.0,
        step=1.0,
    )

year_category = st.selectbox(
    "Χρονολογία κατασκευής:",
    [
        "Πριν το 1980",
        "1980-2000",
        "2001-2009",
        "2010 και μετά",
    ],
)

project_type = st.radio(
    "Το έργο αφορά:",
    ["Απλή αντικατάσταση", "Ανακαίνιση", "Νεόδμητο σπίτι"],
)

col7, col8 = st.columns(2)
with col7:
    power_type = st.radio(
        "Ρεύμα κατοικίας:",
        ["Μονοφασικό", "Τριφασικό", NOT_SURE],
    )
with col8:
    usage_type = st.radio(
        "Τι ζητάτε από την αντλία;",
        ["Μόνο θέρμανση", "Θέρμανση & ΖΝΧ", "Θέρμανση, ΖΝΧ & ψύξη"],
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
    "Θα χρειαστεί αλλαγή ή προσθήκη σε κάποιο θερμαντικό σώμα;",
    [YES, NO, NOT_SURE],
    horizontal=True,
)

distribution_type = st.radio(
    "Τώρα με τι σύστημα ζεσταίνεστε;",
    ["Κεντρικό", "Αυτόνομο"],
    horizontal=True,
)

boiler_type = st.selectbox(
    "Τύπος λέβητα / πηγή θερμότητας:",
    [
        "Λέβητας πετρελαίου",
        "Λέβητας φυσικού αερίου",
        "Λέβητας pellet",
        "Ξυλολέβητας",
        "Άλλο",
    ],
)
boiler_other = ""
if boiler_type == "Άλλο":
    boiler_other = st.text_input("Περιγραφή άλλου τύπου λέβητα / συστήματος:")

st.divider()

st.subheader("4. Πρόσθετα συστήματα & τοποθέτηση")
col9, col10 = st.columns(2)
with col9:
    has_solar = st.radio(
        "Έχετε ηλιακό θερμοσίφωνα;",
        [YES, NO],
        horizontal=True,
    )
with col10:
    has_pv = st.radio(
        "Υπάρχουν φωτοβολταϊκά;",
        [YES, NO],
        horizontal=True,
    )

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
    "Υπάρχουν περιορισμοί θορύβου (γειτονικά σπίτια, πολυκατοικία κ.λπ.);",
    [YES, NO],
    horizontal=True,
)
noise_desc = st.text_area(
    "Αν ναι, περιγράψτε:",
    height=80,
)

comments = st.text_area(
    "Σχόλια / παρατηρήσεις (π.χ. ώρες λειτουργίας, ιδιαίτερες ανάγκες):",
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
    answers = HeatPumpQuestionnaire(
        install_interest=install_interest,
        program_purchase=program_purchase,
        interest_type=interest_type,
        has_engineer_study=has_engineer_study,
        house_type=house_type,
        area_m2=area_m2,
        year_category=year_category,
        project_type=project_type,
        power_type=power_type,
        usage_type=usage_type,
        znx_people=znx_people,
        change_radiators=change_radiators,
        distribution_type=distribution_type,
        boiler_type=boiler_type,
        boiler_other=boiler_other,
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

    summary_text = generate_heat_pump_summary(answers, created_at=submitted_at)
    st.session_state["heat_pump_answers"] = answers
    st.session_state["heat_pump_summary_text"] = summary_text
    st.session_state["heat_pump_submitted_at"] = submitted_at
    st.session_state["heat_pump_pdf_model"] = default_recommended_model(answers)
    st.session_state["heat_pump_pdf_kw_range"] = default_kw_range(answers)
    st.session_state["heat_pump_pdf_cost"] = 0.0
    st.session_state["heat_pump_pdf_subsidy"] = 0.0
    st.session_state["heat_pump_pdf_installments"] = 0

if "heat_pump_answers" in st.session_state:
    answers = st.session_state["heat_pump_answers"]
    summary_text = st.session_state["heat_pump_summary_text"]
    submitted_at = st.session_state["heat_pump_submitted_at"]

    st.success("Η υποβολή καταχωρήθηκε. Δείτε παρακάτω τη σύνοψη για τον φάκελο του πελάτη.")
    st.markdown("### Σύνοψη απαντήσεων")
    st.text(summary_text)

    st.download_button(
        "Κατέβασμα σύνοψης (txt)",
        data=summary_text.encode("utf-8"),
        file_name="questionnaire_heat_pump.txt",
        mime="text/plain",
    )

    st.divider()
    st.markdown("### PDF προκοστολόγησης")

    if PDF_IMPORT_ERROR is not None:
        st.error("Λείπει η βιβλιοθήκη `reportlab`. Εκτελέστε `pip install -r requirements.txt` για δημιουργία PDF.")
    else:
        st.caption(
            "Συμπληρώστε τα στοιχεία προκοστολόγησης που θα εμφανιστούν στο PDF. "
            "Οι υπάρχοντες κανόνες του ερωτηματολογίου δεν αλλάζουν."
        )

        pdf_col1, pdf_col2 = st.columns(2)
        with pdf_col1:
            recommended_model = st.text_input(
                "Προτεινόμενο μοντέλο / λύση",
                value=default_recommended_model(answers),
                key="heat_pump_pdf_model",
            )
            estimated_kw_range = st.text_input(
                "Εκτιμώμενη περιοχή ισχύος (kW)",
                value=default_kw_range(answers),
                key="heat_pump_pdf_kw_range",
                help="Αν υπάρχει μελέτη μηχανικού, καταχωρήστε την περιοχή ισχύος από τη μελέτη.",
            )
        with pdf_col2:
            cost_estimate = st.number_input(
                "Ενδεικτικό κόστος με ΦΠΑ (€)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                key="heat_pump_pdf_cost",
            )
            subsidy_amount = st.number_input(
                "Ενδεικτική επιδότηση (€)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                key="heat_pump_pdf_subsidy",
                disabled=not subsidy_requested(answers),
            )

        installments = st.number_input(
            "Αριθμός δόσεων (0 = χωρίς πλάνο δόσεων)",
            min_value=0,
            max_value=120,
            value=0,
            step=1,
            key="heat_pump_pdf_installments",
        )

        applied_subsidy = min(subsidy_amount, cost_estimate) if cost_estimate else 0
        net_estimate = max(cost_estimate - applied_subsidy, 0)
        total_col1, total_col2, total_col3 = st.columns(3)
        total_col1.metric("Εκτίμηση κόστους", format_eur(cost_estimate))
        total_col2.metric("Επιδότηση", format_eur(applied_subsidy))
        total_col3.metric("Εκτιμώμενο πληρωτέο", format_eur(net_estimate))

        if cost_estimate == 0:
            st.warning(
                "Δεν έχει καταχωρηθεί ενδεικτικό κόστος. Το PDF θα δημιουργηθεί ως προκοστολόγηση "
                "χωρίς οικονομικό ποσό μέχρι να επιλεγεί μοντέλο/τιμή."
            )
        if subsidy_requested(answers) and subsidy_amount == 0:
            st.info("Η αγορά έχει δηλωθεί ως πιθανή μέσω προγράμματος. Η επιδότηση θα σημειωθεί ως προς επιβεβαίωση.")

        try:
            pdf_bytes = build_heat_pump_pdf(
                answers=answers,
                submitted_at=submitted_at,
                recommended_model=recommended_model,
                estimated_kw_range=estimated_kw_range,
                cost_estimate=float(cost_estimate),
                subsidy_amount=float(subsidy_amount),
                installments=int(installments),
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

    st.info(
        "Μπορείτε να εκτυπώσετε τη σύνοψη ή να την αποθηκεύσετε στον φάκελο του πελάτη "
        "μαζί με την πρόταση αντλίας."
    )
else:
    st.info("Συμπληρώστε τα στοιχεία και πατήστε «Υποβολή ερωτηματολογίου».")
