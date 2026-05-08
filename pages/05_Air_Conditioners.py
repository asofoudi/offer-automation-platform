from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.air_conditioners import (
    BUDGET_LABELS,
    FLOOR_LABELS,
    INSTALLATION_DIFFICULTY_LABELS,
    INSULATION_LABELS,
    MAIN_USE_LABELS,
    PRE_COSTING_DISCLAIMER,
    SPACE_TYPE_LABELS,
    SUN_EXPOSURE_LABELS,
    ACQuotationInput,
    build_ac_quotation,
    format_btu,
    format_eur,
    load_ac_products,
    products_for_btu,
    products_for_display,
)
from utils.customer_form import render_customer_form

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


def label_for(labels: dict[str, str], key: str) -> str:
    return labels.get(key, key)


def build_ac_offer_pdf(quotation, customer) -> bytes:
    inputs = quotation.inputs
    product = quotation.product

    product_notes = "\n".join(
        [
            f"Προτεινόμενη κατηγορία: {format_btu(quotation.recommended_btu)}",
            f"Εκτιμώμενη απαίτηση: {format_btu(quotation.estimated_btu)}",
            f"Χώρος: {label_for(SPACE_TYPE_LABELS, inputs.space_type)}",
            f"Τετραγωνικά: {inputs.square_meters:,.1f} m²",
            f"Όροφος: {label_for(FLOOR_LABELS, inputs.floor)}",
            f"Ηλιακή έκθεση: {label_for(SUN_EXPOSURE_LABELS, inputs.sun_exposure)}",
            f"Μόνωση: {label_for(INSULATION_LABELS, inputs.insulation)}",
            f"Κύρια χρήση: {label_for(MAIN_USE_LABELS, inputs.main_use)}",
            f"Budget: {label_for(BUDGET_LABELS, inputs.desired_budget)}",
            product.notes,
        ]
    )

    products = [
        ProductLine(
            description=product.product_name,
            quantity=1,
            unit="τεμ.",
            unit_price=product.unit_price,
            total_price=product.unit_price,
            notes=product_notes,
        )
    ]

    if inputs.installation_needed:
        products.append(
            ProductLine(
                description="Εγκατάσταση κλιματιστικού",
                quantity=1,
                unit="εργασία",
                unit_price=quotation.installation_cost,
                total_price=quotation.installation_cost,
                notes=(
                    "Ενδεικτικό placeholder κόστος για "
                    f"{label_for(INSTALLATION_DIFFICULTY_LABELS, inputs.installation_difficulty).lower()}."
                ),
            )
        )

    customer_notes = [
        f"Χώρος: {label_for(SPACE_TYPE_LABELS, inputs.space_type)}",
        f"Τετραγωνικά: {inputs.square_meters:,.1f} m²",
        f"Προτεινόμενη κατηγορία: {format_btu(quotation.recommended_btu)}",
        f"Εγκατάσταση: {'Ναι' if inputs.installation_needed else 'Όχι'}",
        f"Σύνολο προσφοράς: {format_eur(quotation.total)}",
    ]
    if customer.comments:
        customer_notes.extend(["", "Σχόλια πελάτη:", customer.comments])
    if quotation.warnings:
        customer_notes.extend(["", "Προειδοποιήσεις:"])
        customer_notes.extend(quotation.warnings)

    disclaimer = "\n".join(
        [
            PRE_COSTING_DISCLAIMER,
            "Οι τιμές προϊόντων και εγκατάστασης είναι placeholder και πρέπει να αντικατασταθούν με τον τελικό εμπορικό τιμοκατάλογο.",
            *quotation.warnings,
        ]
    )

    return create_offer_pdf(
        customer={
            "full_name": customer.full_name,
            "phone": customer.phone,
            "email": customer.email,
            "area": customer.area,
            "comments": "\n".join(customer_notes),
        },
        products=products,
        offer_title="Προσφορά κλιματιστικού",
        offer_number=f"AC-{datetime.now().strftime('%Y%m%d-%H%M')}",
        totals=OfferTotals(
            subtotal=quotation.total,
            discount=0,
            vat_rate=0,
            vat_amount=0,
            total=quotation.total,
        ),
        disclaimer=disclaimer,
    )


st.set_page_config(
    page_title="Κλιματιστικά",
    page_icon="❄️",
    layout="wide",
)

products = load_ac_products()

st.title("Προσφορά Κλιματιστικού")
st.caption("Ενδεικτική επιλογή BTU, προϊόντος και κόστους εγκατάστασης.")

st.info(
    "Η λογική BTU και οι τιμές είναι αρχική προκοστολόγηση για τη νέα ενότητα κλιματιστικών. "
    "Οι τιμές διαβάζονται από το `data/ac_prices.csv`."
)

st.divider()
customer = render_customer_form(
    key_prefix="ac_customer",
    title="1. Στοιχεία πελάτη",
)

st.divider()
st.subheader("2. Στοιχεία χώρου")

col1, col2, col3 = st.columns(3)
with col1:
    space_type = st.selectbox(
        "Τύπος χώρου",
        list(SPACE_TYPE_LABELS.keys()),
        format_func=lambda key: SPACE_TYPE_LABELS[key],
    )
with col2:
    square_meters = st.number_input(
        "Τετραγωνικά μέτρα",
        min_value=0.0,
        value=20.0,
        step=1.0,
    )
with col3:
    floor = st.selectbox(
        "Όροφος",
        list(FLOOR_LABELS.keys()),
        format_func=lambda key: FLOOR_LABELS[key],
        index=1,
    )

col4, col5, col6 = st.columns(3)
with col4:
    sun_exposure = st.selectbox(
        "Προσανατολισμός / ηλιακή έκθεση",
        list(SUN_EXPOSURE_LABELS.keys()),
        format_func=lambda key: SUN_EXPOSURE_LABELS[key],
        index=1,
    )
with col5:
    insulation = st.selectbox(
        "Μόνωση",
        list(INSULATION_LABELS.keys()),
        format_func=lambda key: INSULATION_LABELS[key],
        index=1,
    )
with col6:
    main_use = st.selectbox(
        "Κύρια χρήση",
        list(MAIN_USE_LABELS.keys()),
        format_func=lambda key: MAIN_USE_LABELS[key],
        index=2,
    )

st.divider()
st.subheader("3. Εγκατάσταση και budget")

col7, col8, col9 = st.columns(3)
with col7:
    installation_choice = st.radio(
        "Χρειάζεται εγκατάσταση;",
        ["Ναι", "Όχι"],
        horizontal=True,
    )
with col8:
    installation_difficulty = st.selectbox(
        "Δυσκολία εγκατάστασης",
        list(INSTALLATION_DIFFICULTY_LABELS.keys()),
        format_func=lambda key: INSTALLATION_DIFFICULTY_LABELS[key],
        disabled=installation_choice == "Όχι",
    )
with col9:
    desired_budget = st.selectbox(
        "Επιθυμητό budget",
        list(BUDGET_LABELS.keys()),
        format_func=lambda key: BUDGET_LABELS[key],
        index=1,
    )

calculate = st.button("Υπολογισμός προσφοράς κλιματιστικού", type="primary")

if calculate:
    if square_meters <= 0:
        st.error("Συμπληρώστε τετραγωνικά μέτρα μεγαλύτερα από 0.")
        st.stop()

    quotation_input = ACQuotationInput(
        space_type=space_type,
        square_meters=square_meters,
        floor=floor,
        sun_exposure=sun_exposure,
        insulation=insulation,
        main_use=main_use,
        installation_needed=installation_choice == "Ναι",
        installation_difficulty=installation_difficulty,
        desired_budget=desired_budget,
    )
    quotation = build_ac_quotation(quotation_input, products=products)

    st.divider()
    st.subheader("4. Πρόταση")

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Εκτιμώμενη απαίτηση", format_btu(quotation.estimated_btu))
    metric2.metric("Προτεινόμενη κατηγορία", format_btu(quotation.recommended_btu))
    metric3.metric("Τιμή προϊόντος", format_eur(quotation.product.unit_price))
    metric4.metric("Σύνολο", format_eur(quotation.total))

    if quotation.installation_cost:
        st.metric("Ενδεικτικό κόστος εγκατάστασης", format_eur(quotation.installation_cost))
    else:
        st.write("Δεν έχει υπολογιστεί κόστος εγκατάστασης.")

    for warning in quotation.warnings:
        st.warning(warning)

    st.write(f"**Προτεινόμενο προϊόν:** {quotation.product.product_name}")
    st.write(
        f"**Χρήση:** {label_for(MAIN_USE_LABELS, main_use)} | "
        f"**Budget:** {label_for(BUDGET_LABELS, desired_budget)} | "
        f"**Εγκατάσταση:** {installation_choice}"
    )

    st.subheader("5. Εναλλακτικές ίδιας κατηγορίας BTU")
    st.dataframe(
        products_for_display(products_for_btu(products, quotation.recommended_btu)),
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("6. Παρατηρήσεις")
    st.write(PRE_COSTING_DISCLAIMER)
    st.write(
        "Οι τιμές προϊόντων και εγκατάστασης είναι placeholder και πρέπει να αντικατασταθούν "
        "με τον τελικό εμπορικό τιμοκατάλογο."
    )

    st.subheader("7. PDF προσφοράς")
    if PDF_IMPORT_ERROR is not None:
        st.error("Λείπει η βιβλιοθήκη `reportlab`. Εκτελέστε `pip install -r requirements.txt` για δημιουργία PDF.")
    else:
        try:
            pdf_bytes = build_ac_offer_pdf(quotation, customer)
        except GreekFontError as exc:
            st.error(str(exc))
        else:
            st.download_button(
                "Κατέβασμα PDF προσφοράς",
                data=pdf_bytes,
                file_name="prosfora_klimatistikou.pdf",
                mime="application/pdf",
                type="primary",
            )
else:
    st.info("Συμπληρώστε τα στοιχεία και πατήστε «Υπολογισμός προσφοράς κλιματιστικού».")

with st.expander("Προβολή placeholder πίνακα προϊόντων και τιμών"):
    st.dataframe(products_for_display(products), hide_index=True, use_container_width=True)
