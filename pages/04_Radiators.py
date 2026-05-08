import streamlit as st

from utils.radiators import (
    WORK_DISCOUNT_NOTE,
    available_body_types,
    available_heights,
    available_lengths,
    find_radiator,
    format_eur,
    format_int,
    load_radiators,
    quote_radiator,
    rows_for_display,
)


st.set_page_config(
    page_title="Θερμαντικά Σώματα",
    page_icon="🌡️",
    layout="wide",
)

st.title("Τιμολόγηση Σωμάτων Καλοριφέρ")
st.caption("Επιλογή τύπου, ύψους και μήκους με αυτόματο υπολογισμό ισχύος και τιμής.")

st.info(
    "Οι τιμές διαβάζονται από το `data/radiators.csv`. Για ιδιώτη εφαρμόζεται +10% "
    "και στρογγυλοποίηση προς τα πάνω στο ευρώ. Για επαγγελματία εμφανίζεται η τιμή καταλόγου."
)

radiators = load_radiators()

st.divider()
st.subheader("1. Επιλογές σώματος")

col1, col2, col3, col4 = st.columns(4)

with col1:
    customer_type = st.selectbox(
        "Τύπος πελάτη",
        ["Ιδιώτης", "Επαγγελματίας"],
    )

with col2:
    body_type = st.selectbox(
        "Τύπος σώματος",
        available_body_types(radiators),
        format_func=lambda value: f"Τύπος {value}",
    )

with col3:
    height = st.selectbox(
        "Ύψος",
        available_heights(radiators, body_type),
        format_func=lambda value: f"{value} mm",
    )

with col4:
    length_mm = st.selectbox(
        "Μήκος",
        available_lengths(radiators, body_type, height),
        format_func=lambda value: f"{value} mm",
    )

radiator = find_radiator(
    rows=radiators,
    body_type=body_type,
    height=height,
    length_mm=length_mm,
)
quote = quote_radiator(radiator, customer_type)

st.divider()
st.subheader("2. Αποτέλεσμα")

metric1, metric2, metric3 = st.columns(3)
metric1.metric("Ισχύς σώματος", f"{format_int(radiator.power_kcal_h)} kcal/h")
metric1.caption(f"≈ {quote.power_kw:.2f} kW")
metric2.metric("Τιμή καταλόγου", format_eur(quote.catalog_price))
metric3.metric("Τελική τιμή", format_eur(quote.final_price))

st.write(quote.pricing_note)
st.info(WORK_DISCOUNT_NOTE)

st.subheader("3. Γραμμή τιμολόγησης")
st.dataframe(
    [
        {
            "Τύπος πελάτη": customer_type,
            "Τύπος σώματος": body_type,
            "Ύψος": f"{height} mm",
            "Μήκος": f"{length_mm} mm",
            "Ισχύς": f"{format_int(radiator.power_kcal_h)} kcal/h",
            "Τιμή καταλόγου": format_eur(quote.catalog_price),
            "Τελική τιμή": format_eur(quote.final_price),
        }
    ],
    hide_index=True,
    use_container_width=True,
)

with st.expander("Προβολή διαθέσιμου πίνακα σωμάτων"):
    st.dataframe(rows_for_display(radiators), hide_index=True, use_container_width=True)
