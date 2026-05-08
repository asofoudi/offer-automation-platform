import streamlit as st

from utils.customer_form import render_customer_form

try:
    from utils.pdf_offer import (
        CompanyInfo,
        FinancingOption,
        GreekFontError,
        ProductLine,
        create_offer_pdf,
        format_eur,
        normalize_totals,
    )
except ModuleNotFoundError as exc:
    st.error("Λείπει η βιβλιοθήκη `reportlab`. Εκτελέστε `pip install -r requirements.txt`.")
    st.stop()


st.set_page_config(
    page_title="Demo PDF Προσφοράς",
    page_icon="📄",
    layout="wide",
)

st.title("Demo PDF Προσφοράς")
st.caption(
    "Δοκιμαστική σελίδα για τη δημιουργία ελληνικού PDF προσφοράς. "
    "Δεν αποθηκεύει στοιχεία και δεν στέλνει email."
)

st.info(
    "Η σελίδα χρησιμοποιεί ενδεικτικά προϊόντα μόνο για δοκιμή της υποδομής PDF. "
    "Δεν συνδέεται ακόμη με τις εμπορικές σελίδες της πλατφόρμας."
)

st.subheader("Στοιχεία εταιρείας")
company_col1, company_col2 = st.columns(2)
with company_col1:
    company_name = st.text_input("Επωνυμία", value="Η εταιρεία σας")
    company_address = st.text_input("Διεύθυνση", value="")
    company_phone = st.text_input("Τηλέφωνο εταιρείας", value="")
with company_col2:
    company_email = st.text_input("Email εταιρείας", value="")
    company_tax_id = st.text_input("ΑΦΜ", value="")
    company_tax_office = st.text_input("ΔΟΥ", value="")

logo_path = st.text_input(
    "Διαδρομή λογοτύπου (προαιρετικά)",
    value="",
    help="Αν μείνει κενό, χρησιμοποιείται αυτόματα το assets/logo.png.",
)

st.divider()
customer = render_customer_form(key_prefix="pdf_demo_customer")

st.divider()
st.subheader("Ενδεικτικά προϊόντα")
product_col1, product_col2, product_col3 = st.columns(3)
with product_col1:
    product_a_quantity = st.number_input("Ποσότητα προϊόντος Α", min_value=1, value=1, step=1)
    product_a_price = st.number_input("Τιμή μονάδας προϊόντος Α", min_value=0.0, value=1250.0, step=10.0)
with product_col2:
    product_b_quantity = st.number_input("Ποσότητα εργασίας", min_value=1, value=1, step=1)
    product_b_price = st.number_input("Τιμή εργασίας", min_value=0.0, value=350.0, step=10.0)
with product_col3:
    discount = st.number_input("Έκπτωση", min_value=0.0, value=0.0, step=10.0)
    vat_rate_percent = st.number_input("ΦΠΑ %", min_value=0.0, max_value=100.0, value=24.0, step=1.0)

products = [
    ProductLine(
        description="Ενδεικτικό προϊόν προσφοράς",
        quantity=float(product_a_quantity),
        unit="τεμ.",
        unit_price=float(product_a_price),
        notes="Γραμμή demo για έλεγχο πίνακα προϊόντων.",
    ),
    ProductLine(
        description="Ενδεικτική εργασία εγκατάστασης",
        quantity=float(product_b_quantity),
        unit="εργασία",
        unit_price=float(product_b_price),
        notes="Γραμμή demo για έλεγχο υπηρεσιών.",
    ),
]

totals = normalize_totals(
    totals=None,
    products=products,
    discount=float(discount),
    vat_rate=float(vat_rate_percent) / 100,
)

st.dataframe(
    [
        {
            "Περιγραφή": product.description,
            "Ποσότητα": product.quantity,
            "Μονάδα": product.unit,
            "Τιμή μονάδας": format_eur(product.unit_price),
            "Σύνολο": format_eur(product.line_total),
        }
        for product in products
    ],
    hide_index=True,
    use_container_width=True,
)

total_col1, total_col2, total_col3, total_col4 = st.columns(4)
total_col1.metric("Καθαρή αξία", format_eur(totals.subtotal))
total_col2.metric("Έκπτωση", format_eur(totals.discount))
total_col3.metric("ΦΠΑ", format_eur(totals.vat_amount))
total_col4.metric("Σύνολο", format_eur(totals.total))

st.divider()
st.subheader("Χρηματοδότηση και δόσεις")
installment_col1, installment_col2 = st.columns(2)
with installment_col1:
    installment_count = st.number_input("Αριθμός δόσεων", min_value=0, max_value=120, value=12, step=1)
with installment_col2:
    financing_note = st.text_input("Σημείωση χρηματοδότησης", value="Ενδεικτικός υπολογισμός demo.")

financing_options = []
if installment_count:
    financing_options.append(
        FinancingOption(
            name=f"{installment_count} δόσεις",
            installments=int(installment_count),
            monthly_amount=totals.total / int(installment_count),
            total_amount=totals.total,
            note=financing_note,
        )
    )

st.divider()
st.subheader("Δημιουργία PDF")
offer_col1, offer_col2 = st.columns(2)
with offer_col1:
    offer_number = st.text_input("Αριθμός προσφοράς", value="DEMO-001")
with offer_col2:
    offer_title = st.text_input("Τίτλος PDF", value="Ενδεικτική προσφορά")

company = CompanyInfo(
    name=company_name,
    address=company_address,
    phone=company_phone,
    email=company_email,
    tax_id=company_tax_id,
    tax_office=company_tax_office,
    logo_path=logo_path or None,
)

try:
    pdf_bytes = create_offer_pdf(
        customer=customer,
        products=products,
        company=company,
        offer_title=offer_title,
        offer_number=offer_number,
        totals=totals,
        financing_options=financing_options,
        disclaimer=(
            "Το παρόν PDF είναι δοκιμαστικό παράδειγμα της υποδομής προσφορών. "
            "Δεν αποτελεί εμπορική προσφορά μέχρι να συνδεθεί με τους πραγματικούς κανόνες της κάθε σελίδας."
        ),
    )
except GreekFontError as exc:
    st.error(str(exc))
else:
    st.download_button(
        "Λήψη δοκιμαστικής προσφοράς PDF",
        data=pdf_bytes,
        file_name="demo_prosfora.pdf",
        mime="application/pdf",
        type="primary",
    )
