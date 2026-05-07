import streamlit as st

from utils.solar_questions import (
    SolarProposalInput,
    build_solar_proposal,
    format_eur,
    pick_capacity_from_people,
)


YES = "Ναι"
NO = "Όχι"


st.set_page_config(
    page_title="Ερωτηματολόγιο Ηλιακού Θερμοσίφωνα",
    page_icon="☀️",
    layout="wide",
)

st.title("Ερωτηματολόγιο Ηλιακού Θερμοσίφωνα")
st.markdown(
    "Συμπληρώστε τις παρακάτω πληροφορίες ώστε να προταθεί κατάλληλος ηλιακός "
    "θερμοσίφωνας και ενδεικτικό κόστος εγκατάστασης."
)

st.divider()

st.subheader("1. Βασικά στοιχεία χρήσης & αγοράς")
people = st.number_input(
    "Πόσα άτομα θα χρησιμοποιούν τον ηλιακό;",
    min_value=1,
    step=1,
    value=3,
)

mounting = st.radio(
    "Πού θα τοποθετηθεί ο ηλιακός;",
    ["Πλάκα (ταράτσα)", "Κεραμοσκεπή", "Έδαφος"],
)

purchase_mode = st.radio(
    "Η αγορά θα γίνει:",
    ["Με πρόγραμμα επιδότησης", "Με ίδια συμμετοχή"],
)
has_program = purchase_mode == "Με πρόγραμμα επιδότησης"

subsidy_rate = 0.0
subsidy_choice = "-"
if has_program:
    subsidy_choice = st.radio(
        "Τι ποσοστό επιδότησης έχετε;",
        ["50%", "60%", "Δεν γνωρίζω / δεν έχει οριστεί"],
        horizontal=True,
    )
    subsidy_rate = 0.60 if subsidy_choice == "60%" else 0.50

wants_installments = st.radio(
    "Σας ενδιαφέρει να γίνουν δόσεις;",
    [NO, YES],
    horizontal=True,
)

monthly_pref = None
if wants_installments == YES:
    monthly_pref = st.radio(
        "Πόσο περίπου θέλετε να είναι η μηνιαία δόση;",
        ["10-50 €", "50-100 €", "100-150 €"],
        horizontal=True,
    )

st.divider()

st.subheader("2. Πληροφορίες στέγης & προσανατολισμός")
if mounting == "Κεραμοσκεπή":
    orientation_answer = st.radio(
        "Ο προσανατολισμός της σκεπής είναι περίπου νότιος;",
        ["Ναι, είναι περίπου νότιος/καλός", "Όχι, δεν είναι ιδανικός"],
    )
else:
    orientation_answer = "Ναι, είναι περίπου νότιος/καλός"

bad_orientation = orientation_answer == "Όχι, δεν είναι ιδανικός"

shading = st.radio(
    "Υπάρχει σκίαση στον ηλιακό κατά τη διάρκεια της ημέρας;",
    [NO, YES],
    horizontal=True,
)

st.divider()

st.subheader("3. Τύπος σύνδεσης & εγκατάσταση")
connection_choice = st.radio(
    "Θέλουμε ο ηλιακός να συνδεθεί με λέβητα ή αντλία θερμότητας (3πλής ενέργειας);",
    ["Όχι, μόνο ηλιακός", "Ναι, με λέβητα", "Ναι, με αντλία θερμότητας"],
)
st.caption(
    "Δεν προτείνεται σύνδεση 3πλής ενέργειας εκτός από ειδικές περιπτώσεις. "
    "Θα αξιολογηθεί μαζί με τον πελάτη."
)

if connection_choice == "Όχι, μόνο ηλιακός":
    triple_mode = "none"
elif connection_choice == "Ναι, με λέβητα":
    triple_mode = "boiler"
else:
    triple_mode = "hp"

need_crane = st.radio(
    "Θα απαιτηθεί χρήση γερανού για την εγκατάσταση;",
    [NO, YES],
    horizontal=True,
)

install_interest = st.radio(
    "Σας ενδιαφέρει η εγκατάσταση ή μόνο η αγορά του προϊόντος;",
    ["Μόνο αγορά προϊόντος", "Προϊόν + εγκατάσταση"],
)
wants_install = install_interest == "Προϊόν + εγκατάσταση"

replace_old = NO
floor_install = ""
has_hot_cold_stubs = None
has_boiler_lines = None

if wants_install:
    st.markdown("##### Πληροφορίες για την εγκατάσταση")
    replace_old = st.radio(
        "Υπάρχει ήδη ηλιακός που θα χρειαστεί αντικατάσταση/αποξήλωση;",
        [NO, YES],
        horizontal=True,
    )
    floor_install = st.text_input(
        "Σε ποιον όροφο θα γίνει η εγκατάσταση; (π.χ. 3ος, δώμα)",
        value="",
    )
    has_hot_cold_stubs = st.radio(
        "Αν δεν υπάρχει ήδη ηλιακός, υπάρχουν αναμονές ζεστού/κρύου πάνω στην ταράτσα/στέγη;",
        [YES, NO],
        horizontal=True,
    )
    if triple_mode in ("boiler", "hp"):
        has_boiler_lines = st.radio(
            "Για ηλιακό τριπλής ενέργειας, υπάρχουν ήδη γραμμές λέβητα/ΑΘ μέχρι τον ηλιακό;",
            [YES, NO],
            horizontal=True,
        )

st.divider()

st.subheader("4. Στοιχεία επικοινωνίας (προαιρετικά)")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Ονοματεπώνυμο", value="")
    phone = st.text_input("Τηλέφωνο", value="")
with col2:
    email = st.text_input("Email", value="")
    address = st.text_input("Διεύθυνση ακινήτου (πόλη / περιοχή)", value="")

submitted = st.button("Υπολογισμός πρότασης ηλιακού", type="primary")

if submitted:
    inputs = SolarProposalInput(
        people=people,
        mounting=mounting,
        has_program=has_program,
        subsidy_rate=subsidy_rate,
        wants_installments=wants_installments == YES,
        bad_orientation=bad_orientation,
        shading=shading == YES,
        triple_mode=triple_mode,
        need_crane=need_crane,
        wants_install=wants_install,
        replace_old=replace_old,
        has_hot_cold_stubs=has_hot_cold_stubs,
    )
    proposal = build_solar_proposal(inputs)

    st.divider()
    st.subheader("Προτεινόμενη χωρητικότητα")
    st.write(
        f"Με βάση τα **{people} άτομα**, η βασική προτεινόμενη χωρητικότητα είναι "
        f"περίπου **{pick_capacity_from_people(people)} lt**."
    )

    delta_col, calpak_col = st.columns(2)

    with delta_col:
        st.markdown("## Πρόταση οικονομικής σειράς - Delta Solar")
        st.write(
            f"**Μοντέλο:** Delta Solar {proposal.delta_model.capacity} lt, "
            f"συλλέκτης {proposal.delta_model.area:.2f} m², "
            f"{proposal.delta_model.kind_label}"
        )
        if mounting == "Κεραμοσκεπή":
            st.caption("Η κεραμοσκεπή προσθέτει +40 € λόγω βάσεων/κιτ στήριξης για Delta Solar.")
        if bad_orientation:
            st.caption("Επιλέχθηκε μεγαλύτερη επιφάνεια συλλέκτη λόγω μη ιδανικού προσανατολισμού/κλίσης.")
        if proposal.shading:
            st.caption("Υπάρχει σκίαση. Θα ληφθεί υπόψη στην τελική πρόταση.")

        st.metric("Τιμή προϊόντος με ΦΠΑ", format_eur(proposal.delta_product_price))
        if wants_install:
            st.metric("Εγκατάσταση", format_eur(proposal.install_cost))
            st.metric("Σύνολο πακέτου", format_eur(proposal.delta_total))
        else:
            st.write("Δεν έχει υπολογιστεί εγκατάσταση. Η πρόταση αφορά μόνο αγορά προϊόντος.")

        if has_program:
            st.metric(
                f"Εκτιμώμενη ίδια συμμετοχή με επιδότηση {int(subsidy_rate * 100)}%",
                format_eur(proposal.delta_customer_share),
            )
        else:
            st.write("Δεν υπάρχει πρόγραμμα. Έχει εφαρμοστεί έκπτωση 5% στην τιμή προϊόντος.")
            st.metric("Ενδεικτικό ποσό πληρωμής", format_eur(proposal.delta_customer_share))

        if proposal.delta_monthly_payment > 0:
            st.metric("Ενδεικτική δόση 36 μηνών", f"{format_eur(proposal.delta_monthly_payment)} / μήνα")

    with calpak_col:
        st.markdown("## Εναλλακτική πρόταση - Calpak")
        st.write(
            f"**Μοντέλο:** Calpak {proposal.calpak_model.capacity} lt, "
            f"συλλέκτης {proposal.calpak_model.area:.2f} m² "
            "(σειρά 2πλής ενέργειας)"
        )
        st.caption("Στην Calpak δεν υπάρχει επιβάρυνση για κεραμοσκεπή.")

        st.metric("Τιμή προϊόντος με ΦΠΑ", format_eur(proposal.calpak_product_price))
        if wants_install:
            st.metric("Εγκατάσταση", format_eur(proposal.install_cost))
            st.metric("Σύνολο πακέτου", format_eur(proposal.calpak_total))
        else:
            st.write("Δεν έχει υπολογιστεί εγκατάσταση. Η πρόταση αφορά μόνο αγορά προϊόντος.")

        if has_program:
            st.metric(
                f"Εκτιμώμενη ίδια συμμετοχή με επιδότηση {int(subsidy_rate * 100)}%",
                format_eur(proposal.calpak_customer_share),
            )
        else:
            st.write("Δεν υπάρχει πρόγραμμα. Έχει εφαρμοστεί έκπτωση 5% στην τιμή προϊόντος.")
            st.metric("Ενδεικτικό ποσό πληρωμής", format_eur(proposal.calpak_customer_share))

        if proposal.calpak_monthly_payment > 0:
            st.metric("Ενδεικτική δόση 36 μηνών", f"{format_eur(proposal.calpak_monthly_payment)} / μήνα")

    st.divider()
    st.subheader("Σημαντικές παρατηρήσεις")
    if replace_old == YES:
        st.write("- Θα γίνει αποξήλωση παλιού ηλιακού. Δεν παρέχεται ανακύκλωση της παλιάς συσκευής.")

    if triple_mode in ("boiler", "hp"):
        st.write(
            "- Η επιλογή ηλιακού τριπλής ενέργειας δεν προτείνεται γενικά, "
            "εκτός από ειδικές περιπτώσεις."
        )
        if has_boiler_lines == NO:
            st.write(
                "- Για τριπλής ενέργειας δεν υπάρχουν γραμμές λέβητα/ΑΘ. "
                "Πιθανόν να χρειαστούν πρόσθετες εργασίες."
            )

    if floor_install:
        st.write(f"- Δηλωμένος όροφος εγκατάστασης: {floor_install}.")
    if monthly_pref:
        st.write(f"- Προτίμηση μηνιαίας δόσης πελάτη: {monthly_pref}.")

    st.write(
        "Η παραπάνω κοστολόγηση είναι προκοστολόγηση. Για τελικό κόστος απαιτείται "
        "αυτοψία στον χώρο, έλεγχος σωληνώσεων, στέγης/ταράτσας και συνθηκών εγκατάστασης."
    )

    contact_lines = [line for line in [name, phone, email, address] if line]
    if contact_lines:
        st.caption("Στοιχεία πελάτη: " + " | ".join(contact_lines))
else:
    st.info("Συμπληρώστε τα στοιχεία και πατήστε «Υπολογισμός πρότασης ηλιακού».")
