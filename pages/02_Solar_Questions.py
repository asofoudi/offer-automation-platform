from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.solar_questions import (
    SolarProposalInput,
    build_solar_proposal,
    format_eur,
    pick_capacity_from_people,
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

SOLAR_DISCLAIMER = (
    "Η παρούσα προσφορά είναι προκοστολόγηση βάσει των στοιχείων που δηλώθηκαν. "
    "Η τελική τιμή επιβεβαιώνεται μετά από αυτοψία, έλεγχο πρόσβασης, σωληνώσεων, "
    "στέγης/ταράτσας, σκίασης, προσανατολισμού και συνθηκών εγκατάστασης. "
    "Οι επιδοτήσεις και οι δόσεις είναι ενδεικτικές και απαιτούν τελική έγκριση."
)


def model_label(model) -> str:
    return (
        f"{model.brand} {model.capacity} lt, "
        f"συλλέκτης {model.area:.2f} m², {model.kind_label}"
    )


def amount_label(value: float) -> str:
    return format_eur(value)


def option_notes(
    *,
    product_price: float,
    install_cost: float,
    total: float,
    customer_share: float,
    monthly_payment: float,
    has_program: bool,
    subsidy_rate: float,
    wants_install: bool,
) -> str:
    lines = [f"Τιμή προϊόντος με ΦΠΑ: {amount_label(product_price)}"]
    if wants_install:
        lines.append(f"Εγκατάσταση: {amount_label(install_cost)}")
    else:
        lines.append("Δεν έχει υπολογιστεί εγκατάσταση. Η πρόταση αφορά μόνο αγορά προϊόντος.")
    lines.append(f"Σύνολο πακέτου: {amount_label(total)}")
    if has_program:
        lines.append(
            f"Εκτιμώμενη ίδια συμμετοχή με επιδότηση {int(subsidy_rate * 100)}%: "
            f"{amount_label(customer_share)}"
        )
    else:
        lines.append("Δεν υπάρχει πρόγραμμα. Έχει εφαρμοστεί έκπτωση 5% στην τιμή προϊόντος.")
        lines.append(f"Ενδεικτικό ποσό πληρωμής: {amount_label(customer_share)}")
    if monthly_payment > 0:
        lines.append(f"Ενδεικτική δόση 36 μηνών: {amount_label(monthly_payment)} / μήνα")
    return "\n".join(lines)


def build_solar_notes(
    *,
    people: int,
    mounting: str,
    bad_orientation: bool,
    shading: bool,
    triple_mode: str,
    need_crane: str,
    wants_install: bool,
    replace_old: str,
    floor_install: str,
    has_hot_cold_stubs: str | None,
    has_boiler_lines: str | None,
    monthly_pref: str | None,
) -> str:
    notes = [
        f"Άτομα χρήσης: {people}",
        f"Τρόπος τοποθέτησης: {mounting}",
    ]
    if bad_orientation:
        notes.append("Μη ιδανικός προσανατολισμός/κλίση: επιλέχθηκε μεγαλύτερη επιφάνεια συλλέκτη όπου εφαρμόζεται.")
    if shading:
        notes.append("Υπάρχει σκίαση και πρέπει να ληφθεί υπόψη στην τελική πρόταση.")
    if triple_mode in ("boiler", "hp"):
        notes.append("Η τριπλή ενέργεια δεν προτείνεται γενικά, εκτός από ειδικές περιπτώσεις.")
        if has_boiler_lines == NO:
            notes.append("Δεν υπάρχουν γραμμές λέβητα/ΑΘ μέχρι τον ηλιακό, άρα μπορεί να απαιτηθούν πρόσθετες εργασίες.")
    if wants_install:
        if replace_old == YES:
            notes.append("Περιλαμβάνεται αποξήλωση παλιού ηλιακού, χωρίς ανακύκλωση παλιάς συσκευής.")
        if floor_install:
            notes.append(f"Δηλωμένος όροφος εγκατάστασης: {floor_install}.")
        if has_hot_cold_stubs == NO:
            notes.append("Δεν υπάρχουν αναμονές ζεστού/κρύου στο σημείο εγκατάστασης.")
        if need_crane == YES:
            notes.append("Έχει δηλωθεί ανάγκη χρήσης γερανού.")
    if monthly_pref:
        notes.append(f"Προτίμηση μηνιαίας δόσης πελάτη: {monthly_pref}.")
    notes.append(SOLAR_DISCLAIMER)
    return "\n".join(notes)


def build_solar_offer_pdf(
    *,
    proposal,
    name: str,
    phone: str,
    email: str,
    address: str,
    people: int,
    mounting: str,
    has_program: bool,
    subsidy_rate: float,
    wants_install: bool,
    bad_orientation: bool,
    shading: bool,
    triple_mode: str,
    need_crane: str,
    replace_old: str,
    floor_install: str,
    has_hot_cold_stubs: str | None,
    has_boiler_lines: str | None,
    monthly_pref: str | None,
) -> bytes:
    shared_notes = build_solar_notes(
        people=people,
        mounting=mounting,
        bad_orientation=bad_orientation,
        shading=shading,
        triple_mode=triple_mode,
        need_crane=need_crane,
        wants_install=wants_install,
        replace_old=replace_old,
        floor_install=floor_install,
        has_hot_cold_stubs=has_hot_cold_stubs,
        has_boiler_lines=has_boiler_lines,
        monthly_pref=monthly_pref,
    )

    delta_subsidy = proposal.delta_total - proposal.delta_customer_share

    products = [
        ProductLine(
            description=f"Κύρια πρόταση - {model_label(proposal.delta_model)}",
            quantity=1,
            unit="πακέτο",
            unit_price=proposal.delta_total,
            notes=option_notes(
                product_price=proposal.delta_product_price,
                install_cost=proposal.install_cost,
                total=proposal.delta_total,
                customer_share=proposal.delta_customer_share,
                monthly_payment=proposal.delta_monthly_payment,
                has_program=has_program,
                subsidy_rate=subsidy_rate,
                wants_install=wants_install,
            ),
        ),
        ProductLine(
            description=f"Εναλλακτική πρόταση - {model_label(proposal.calpak_model)}",
            quantity=1,
            unit="πακέτο",
            unit_price=proposal.calpak_total,
            notes=option_notes(
                product_price=proposal.calpak_product_price,
                install_cost=proposal.install_cost,
                total=proposal.calpak_total,
                customer_share=proposal.calpak_customer_share,
                monthly_payment=proposal.calpak_monthly_payment,
                has_program=has_program,
                subsidy_rate=subsidy_rate,
                wants_install=wants_install,
            ),
        ),
    ]

    financing_options = []
    if proposal.delta_monthly_payment > 0:
        financing_options.append(
            FinancingOption(
                name="Delta Solar - 36 δόσεις",
                installments=36,
                monthly_amount=proposal.delta_monthly_payment,
                total_amount=proposal.delta_monthly_payment * 36,
                note="Ενδεικτική δόση βάσει του υπάρχοντος υπολογισμού.",
            )
        )
    if proposal.calpak_monthly_payment > 0:
        financing_options.append(
            FinancingOption(
                name="Calpak - 36 δόσεις",
                installments=36,
                monthly_amount=proposal.calpak_monthly_payment,
                total_amount=proposal.calpak_monthly_payment * 36,
                note="Ενδεικτική δόση βάσει του υπάρχοντος υπολογισμού.",
            )
        )

    customer = {
        "full_name": name,
        "phone": phone,
        "email": email,
        "area": address,
        "comments": shared_notes,
    }

    disclaimer = (
        f"{shared_notes}\n\n"
        "Στα σύνολα εμφανίζεται η κύρια πρόταση Delta Solar. "
        "Η Calpak εμφανίζεται ως εναλλακτική πρόταση στον πίνακα προϊόντων."
    )

    return create_offer_pdf(
        customer=customer,
        products=products,
        offer_title="Προσφορά ηλιακού θερμοσίφωνα",
        offer_number=f"SOLAR-{datetime.now().strftime('%Y%m%d-%H%M')}",
        totals=OfferTotals(
            subtotal=proposal.delta_total,
            discount=delta_subsidy,
            vat_rate=0,
            vat_amount=0,
            total=proposal.delta_customer_share,
        ),
        financing_options=financing_options,
        disclaimer=disclaimer,
    )


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

    st.divider()
    st.subheader("PDF προσφοράς")
    if PDF_IMPORT_ERROR is not None:
        st.error("Λείπει η βιβλιοθήκη `reportlab`. Εκτελέστε `pip install -r requirements.txt` για δημιουργία PDF.")
    else:
        try:
            pdf_bytes = build_solar_offer_pdf(
                proposal=proposal,
                name=name,
                phone=phone,
                email=email,
                address=address,
                people=people,
                mounting=mounting,
                has_program=has_program,
                subsidy_rate=subsidy_rate,
                wants_install=wants_install,
                bad_orientation=bad_orientation,
                shading=proposal.shading,
                triple_mode=triple_mode,
                need_crane=need_crane,
                replace_old=replace_old,
                floor_install=floor_install,
                has_hot_cold_stubs=has_hot_cold_stubs,
                has_boiler_lines=has_boiler_lines,
                monthly_pref=monthly_pref,
            )
        except GreekFontError as exc:
            st.error(str(exc))
        else:
            st.download_button(
                "Λήψη PDF προσφοράς",
                data=pdf_bytes,
                file_name="prosfora_iliakou_thermosifona.pdf",
                mime="application/pdf",
                type="primary",
            )
else:
    st.info("Συμπληρώστε τα στοιχεία και πατήστε «Υπολογισμός πρότασης ηλιακού».")
