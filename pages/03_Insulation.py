from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.insulation import (
    DISCLAIMER,
    InsulationOfferInput,
    build_insulation_offer,
    format_eur,
    generate_insulation_summary,
    offer_rows_for_display,
    offer_rows_to_csv,
)

try:
    from utils.pdf_offer import (
        GreekFontError,
        OfferTotals,
        ProductLine,
        create_offer_pdf,
    )
except ModuleNotFoundError as exc:
    GreekFontError = RuntimeError
    OfferTotals = None
    ProductLine = None
    create_offer_pdf = None
    PDF_IMPORT_ERROR = exc
else:
    PDF_IMPORT_ERROR = None


def build_insulation_offer_pdf(offer, customer: dict[str, str]) -> bytes:
    inputs = offer.inputs
    products = []

    for line in offer.bom_lines:
        notes = [
            f"Ανάγκη: {line.need}",
            f"Συσκευασία: {line.package}",
        ]
        if line.notes:
            notes.append(line.notes)
        if line.quantity is None:
            notes.append("Η ποσότητα εμφανίζεται κατά περίπτωση και δεν περιλαμβάνεται στο σύνολο.")
        if line.unit_price is None:
            notes.append("Δεν υπάρχει καταχωρημένη τιμή στο υπάρχον υλικό.")

        products.append(
            ProductLine(
                description=f"ERP: {line.code} - {line.material}",
                quantity=line.quantity if line.quantity is not None else 0,
                unit=line.unit,
                unit_price=line.unit_price if line.unit_price is not None else 0,
                total_price=line.total if line.total is not None else 0,
                notes="\n".join(notes),
            )
        )

    project_lines = [
        f"Επιφάνεια μόνωσης: {inputs.area_m2:,.0f} m²",
        f"Τύπος μόνωσης: {inputs.insulation_type}",
        f"Πάχος μόνωσης: {inputs.thickness_cm} cm",
        f"Σύνολο υλικών: {format_eur(offer.total)}",
    ]
    if customer.get("comments"):
        project_lines.extend(["", "Σχόλια υπαλλήλου:", customer["comments"]])
    if offer.warnings:
        project_lines.extend(["", "Προειδοποιήσεις:"])
        project_lines.extend(offer.warnings)

    disclaimer = "\n".join(
        [
            f"Σύστημα: {inputs.insulation_type} {inputs.thickness_cm} cm.",
            f"Επιφάνεια προκοστολόγησης: {inputs.area_m2:,.0f} m².",
            "Ο πίνακας BOM περιλαμβάνει ERP κωδικούς, ποσότητες αγοράς, τιμές μονάδας και σύνολα όπου υπάρχουν διαθέσιμα στοιχεία.",
            "Τα γωνιόκρανα και οι αφροί χαμηλής διόγκωσης εμφανίζονται ως παρελκόμενα και δεν περιλαμβάνονται στο σύνολο, επειδή στο υπάρχον υλικό ορίζονται κατά περίπτωση.",
            *offer.warnings,
            DISCLAIMER,
        ]
    )

    return create_offer_pdf(
        customer={
            "full_name": customer.get("name", ""),
            "phone": customer.get("phone", ""),
            "email": customer.get("email", ""),
            "area": customer.get("address", ""),
            "comments": "\n".join(project_lines),
        },
        products=products,
        offer_title="Προσφορά θερμομόνωσης",
        offer_number=f"INS-{datetime.now().strftime('%Y%m%d-%H%M')}",
        totals=OfferTotals(
            subtotal=offer.total,
            discount=0,
            vat_rate=0,
            vat_amount=0,
            total=offer.total,
        ),
        disclaimer=disclaimer,
    )


st.set_page_config(
    page_title="Προσφορά Θερμομόνωσης",
    page_icon="🏠",
    layout="wide",
)

st.title("Προσφορά Θερμομόνωσης")
st.caption("Υπολογισμός BOM, ERP κωδικών και προκοστολόγησης υλικών.")

st.info(
    "Οι ποσότητες και οι τιμές ακολουθούν τους υπάρχοντες κανόνες θερμομόνωσης. "
    "Η προσφορά είναι προκοστολόγηση και απαιτεί τεχνική επιβεβαίωση."
)

st.divider()

st.subheader("1. Στοιχεία πελάτη")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Ονοματεπώνυμο / Επωνυμία")
    phone = st.text_input("Τηλέφωνο")
with col2:
    email = st.text_input("Email")
    address = st.text_input("Τοποθεσία / διεύθυνση έργου")

comments = st.text_area("Σχόλια υπαλλήλου", height=90)

st.divider()

st.subheader("2. Στοιχεία θερμομόνωσης")
col3, col4, col5 = st.columns(3)
with col3:
    area_m2 = st.number_input(
        "m² μόνωσης",
        min_value=0.0,
        value=100.0,
        step=1.0,
    )
with col4:
    insulation_type = st.selectbox(
        "Τύπος μόνωσης",
        ["Γραφιτούχα", "Εξηλασμένη"],
    )
with col5:
    thickness_cm = st.selectbox(
        "Πάχος μόνωσης",
        [5, 7, 10],
        format_func=lambda value: f"{value} cm",
        index=1,
    )

calculate = st.button("Υπολογισμός BOM και τιμής", type="primary")

if calculate:
    if area_m2 <= 0:
        st.error("Συμπληρώστε m² μόνωσης μεγαλύτερα από 0.")
        st.stop()

    customer = {
        "name": name,
        "phone": phone,
        "email": email,
        "address": address,
        "comments": comments,
    }
    offer = build_insulation_offer(
        InsulationOfferInput(
            area_m2=area_m2,
            insulation_type=insulation_type,
            thickness_cm=thickness_cm,
        )
    )

    st.divider()
    st.subheader("3. Σύνοψη προκοστολόγησης")

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Επιφάνεια", f"{area_m2:,.0f} m²")
    metric2.metric("Σύστημα", f"{insulation_type} {thickness_cm} cm")
    metric3.metric("Σύνολο υλικών", format_eur(offer.total))

    for warning in offer.warnings:
        st.warning(warning)

    st.subheader("4. BOM υλικών")
    st.dataframe(
        offer_rows_for_display(offer),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("5. Παρατηρήσεις")
    st.write(DISCLAIMER)
    st.write(
        "Τα γωνιόκρανα και οι αφροί χαμηλής διόγκωσης εμφανίζονται ως παρελκόμενα "
        "και δεν περιλαμβάνονται στο σύνολο, επειδή στο υπάρχον υλικό ορίζονται κατά περίπτωση."
    )

    summary_text = generate_insulation_summary(offer, customer)
    bom_csv = offer_rows_to_csv(offer)

    st.subheader("6. Export")
    download_col1, download_col2, download_col3 = st.columns(3)
    with download_col1:
        st.download_button(
            "Κατέβασμα σύνοψης TXT",
            data=summary_text.encode("utf-8"),
            file_name="insulation_offer_summary.txt",
            mime="text/plain",
        )
    with download_col2:
        st.download_button(
            "Κατέβασμα BOM CSV",
            data=bom_csv.encode("utf-8-sig"),
            file_name="insulation_bom_priced.csv",
            mime="text/csv",
        )
    with download_col3:
        if PDF_IMPORT_ERROR is not None:
            st.error("Λείπει η βιβλιοθήκη `reportlab`. Εκτελέστε `pip install -r requirements.txt` για δημιουργία PDF.")
        else:
            try:
                pdf_bytes = build_insulation_offer_pdf(offer, customer)
            except GreekFontError as exc:
                st.error(str(exc))
            else:
                st.download_button(
                    "Κατέβασμα PDF προσφοράς",
                    data=pdf_bytes,
                    file_name="prosfora_thermomonosis.pdf",
                    mime="application/pdf",
                    type="primary",
                )
else:
    st.info("Συμπληρώστε τα στοιχεία έργου και πατήστε «Υπολογισμός BOM και τιμής».")
