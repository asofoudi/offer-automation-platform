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
    download_col1, download_col2 = st.columns(2)
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
else:
    st.info("Συμπληρώστε τα στοιχεία έργου και πατήστε «Υπολογισμός BOM και τιμής».")
