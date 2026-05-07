from datetime import datetime

import streamlit as st

from utils.heat_pump_questionnaire import HeatPumpQuestionnaire, generate_heat_pump_summary


YES = "Ναι"
NO = "Όχι"
NOT_SURE = "Δεν γνωρίζω"


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

    summary_text = generate_heat_pump_summary(answers, created_at=datetime.now())
    st.success("Η υποβολή καταχωρήθηκε. Δείτε παρακάτω τη σύνοψη για τον φάκελο του πελάτη.")
    st.markdown("### Σύνοψη απαντήσεων")
    st.text(summary_text)

    st.download_button(
        "Κατέβασμα σύνοψης (txt)",
        data=summary_text.encode("utf-8"),
        file_name="questionnaire_heat_pump.txt",
        mime="text/plain",
    )

    st.info(
        "Μπορείτε να εκτυπώσετε τη σύνοψη ή να την αποθηκεύσετε στον φάκελο του πελάτη "
        "μαζί με την πρόταση αντλίας."
    )
else:
    st.info("Συμπληρώστε τα στοιχεία και πατήστε «Υποβολή ερωτηματολογίου».")
