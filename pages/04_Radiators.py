from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.customer_form import render_customer_form
from utils.radiators import (
    WORK_DISCOUNT_NOTE,
    available_body_types,
    available_heights,
    available_lengths,
    build_radiator_quotation,
    find_radiator,
    format_eur,
    format_int,
    format_kw,
    load_radiators,
    quote_lines_for_display,
    quote_radiator,
    quote_radiator_line,
    rows_for_display,
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


QUOTE_ITEMS_KEY = "radiator_quote_items"


def ensure_quote_items() -> None:
    if QUOTE_ITEMS_KEY not in st.session_state:
        st.session_state[QUOTE_ITEMS_KEY] = []


def current_quote_lines(radiators, customer_type: str):
    lines = []
    for item in st.session_state[QUOTE_ITEMS_KEY]:
        radiator = find_radiator(
            rows=radiators,
            body_type=item["body_type"],
            height=item["height"],
            length_mm=item["length_mm"],
        )
        lines.append(
            quote_radiator_line(
                radiator=radiator,
                customer_type=customer_type,
                quantity=item["quantity"],
                notes=item.get("notes", ""),
            )
        )
    return lines


def build_radiator_offer_pdf(quotation, customer) -> bytes:
    products = []

    for line in quotation.lines:
        radiator = line.quote.radiator
        notes = [
            f"Τύπος σώματος: {radiator.body_type}",
            f"Διαστάσεις: ύψος {radiator.height} mm, μήκος {radiator.length_mm} mm",
            f"Ισχύς ανά σώμα: {format_int(radiator.power_kcal_h)} kcal/h ({format_kw(line.quote.power_kw)})",
            f"Συνολική ισχύς γραμμής: {format_int(line.total_power_kcal_h)} kcal/h ({format_kw(line.total_power_kw)})",
            f"Τιμή καταλόγου ανά τεμάχιο: {format_eur(line.quote.catalog_price)}",
            line.quote.pricing_note,
        ]
        if line.notes:
            notes.append(f"Σημείωση γραμμής: {line.notes}")

        products.append(
            ProductLine(
                description=f"Σώμα καλοριφέρ τύπου {radiator.body_type} - {radiator.height}x{radiator.length_mm} mm",
                quantity=line.quantity,
                unit="τεμ.",
                unit_price=line.unit_price,
                total_price=line.line_total,
                notes="\n".join(notes),
            )
        )

    customer_notes = [
        f"Τύπος τιμολόγησης: {quotation.customer_type}",
        f"Σύνολο σωμάτων: {quotation.total_quantity}",
        f"Συνολική ισχύς: {format_int(quotation.total_power_kcal_h)} kcal/h ({format_kw(quotation.total_power_kw)})",
        f"Σύνολο προσφοράς: {format_eur(quotation.total)}",
    ]
    if customer.comments:
        customer_notes.extend(["", "Σχόλια πελάτη:", customer.comments])

    disclaimer = "\n".join(
        [
            "Η παρούσα προσφορά είναι προκοστολόγηση για σώματα καλοριφέρ βάσει του διαθέσιμου πίνακα τιμών.",
            "Οι τελικές ποσότητες, διαστάσεις, ισχύς και συμβατότητα με την εγκατάσταση πρέπει να επιβεβαιωθούν πριν την παραγγελία.",
            "Η τιμολόγηση ανά τεμάχιο ακολουθεί τους υπάρχοντες κανόνες της εφαρμογής.",
            WORK_DISCOUNT_NOTE,
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
        offer_title="Προσφορά σωμάτων καλοριφέρ",
        offer_number=f"RAD-{datetime.now().strftime('%Y%m%d-%H%M')}",
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
    page_title="Θερμαντικά Σώματα",
    page_icon="🌡️",
    layout="wide",
)

ensure_quote_items()
radiators = load_radiators()

st.title("Προσφορά Σωμάτων Καλοριφέρ")
st.caption("Πλήρης ροή προσφοράς με επιλογή σωμάτων, ποσότητες, σύνολα και PDF.")

st.info(
    "Οι τιμές διαβάζονται από το `data/radiators.csv`. Για ιδιώτη εφαρμόζεται +10% "
    "και στρογγυλοποίηση προς τα πάνω στο ευρώ. Για επαγγελματία εμφανίζεται η τιμή καταλόγου."
)

st.divider()
customer = render_customer_form(
    key_prefix="radiator_customer",
    title="1. Στοιχεία πελάτη",
)

st.divider()
st.subheader("2. Επιλογή σώματος")

selection_col1, selection_col2, selection_col3, selection_col4, selection_col5 = st.columns(5)

with selection_col1:
    customer_type = st.selectbox(
        "Τύπος πελάτη",
        ["Ιδιώτης", "Επαγγελματίας"],
        key="radiator_customer_type",
    )

with selection_col2:
    body_type = st.selectbox(
        "Τύπος σώματος",
        available_body_types(radiators),
        format_func=lambda value: f"Τύπος {value}",
        key="radiator_body_type",
    )

with selection_col3:
    height = st.selectbox(
        "Ύψος",
        available_heights(radiators, body_type),
        format_func=lambda value: f"{value} mm",
        key="radiator_height",
    )

with selection_col4:
    length_mm = st.selectbox(
        "Μήκος",
        available_lengths(radiators, body_type, height),
        format_func=lambda value: f"{value} mm",
        key="radiator_length",
    )

with selection_col5:
    quantity = st.number_input(
        "Ποσότητα",
        min_value=1,
        value=1,
        step=1,
        key="radiator_quantity",
    )

selected_radiator = find_radiator(
    rows=radiators,
    body_type=body_type,
    height=height,
    length_mm=length_mm,
)
selected_quote = quote_radiator(selected_radiator, customer_type)

preview1, preview2, preview3, preview4 = st.columns(4)
preview1.metric("Ισχύς/τεμ.", f"{format_int(selected_radiator.power_kcal_h)} kcal/h")
preview1.caption(format_kw(selected_quote.power_kw))
preview2.metric("Τιμή καταλόγου", format_eur(selected_quote.catalog_price))
preview3.metric("Τιμή/τεμ.", format_eur(selected_quote.final_price))
preview4.metric("Σύνολο γραμμής", format_eur(selected_quote.final_price * quantity))

line_notes = st.text_input(
    "Σημείωση γραμμής",
    placeholder="π.χ. Υπνοδωμάτιο, σαλόνι, αντικατάσταση παλιού σώματος",
    key="radiator_line_notes",
)

add_col, remove_col, clear_col = st.columns([2, 1, 1])
with add_col:
    if st.button("Προσθήκη σώματος στην προσφορά", type="primary"):
        st.session_state[QUOTE_ITEMS_KEY].append(
            {
                "body_type": body_type,
                "height": height,
                "length_mm": length_mm,
                "quantity": int(quantity),
                "notes": line_notes.strip(),
            }
        )
        st.success("Το σώμα προστέθηκε στην προσφορά.")

with remove_col:
    if st.button("Αφαίρεση τελευταίας γραμμής", disabled=not st.session_state[QUOTE_ITEMS_KEY]):
        st.session_state[QUOTE_ITEMS_KEY].pop()
        st.rerun()

with clear_col:
    if st.button("Καθαρισμός προσφοράς", disabled=not st.session_state[QUOTE_ITEMS_KEY]):
        st.session_state[QUOTE_ITEMS_KEY] = []
        st.rerun()

st.write(selected_quote.pricing_note)
st.info(WORK_DISCOUNT_NOTE)

quote_lines = current_quote_lines(radiators, customer_type)

st.divider()
st.subheader("3. Πίνακας προσφοράς")

if not quote_lines:
    st.info("Προσθέστε ένα ή περισσότερα σώματα για να δημιουργηθεί προσφορά.")
else:
    quotation = build_radiator_quotation(
        lines=quote_lines,
        customer_type=customer_type,
    )

    total_col1, total_col2, total_col3 = st.columns(3)
    total_col1.metric("Σύνολο σωμάτων", str(quotation.total_quantity))
    total_col2.metric(
        "Συνολική ισχύς",
        f"{format_int(quotation.total_power_kcal_h)} kcal/h",
    )
    total_col2.caption(format_kw(quotation.total_power_kw))
    total_col3.metric("Σύνολο προσφοράς", format_eur(quotation.total))

    st.dataframe(
        quote_lines_for_display(quote_lines),
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("4. PDF προσφοράς")
    if PDF_IMPORT_ERROR is not None:
        st.error("Λείπει η βιβλιοθήκη `reportlab`. Εκτελέστε `pip install -r requirements.txt` για δημιουργία PDF.")
    else:
        try:
            pdf_bytes = build_radiator_offer_pdf(quotation, customer)
        except GreekFontError as exc:
            st.error(str(exc))
        else:
            st.download_button(
                "Κατέβασμα PDF προσφοράς",
                data=pdf_bytes,
                file_name="prosfora_somaton_kalorifer.pdf",
                mime="application/pdf",
                type="primary",
            )

with st.expander("Προβολή διαθέσιμου πίνακα σωμάτων"):
    st.dataframe(rows_for_display(radiators), hide_index=True, use_container_width=True)
