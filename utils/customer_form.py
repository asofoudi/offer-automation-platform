from __future__ import annotations

from dataclasses import asdict, dataclass

import streamlit as st


@dataclass(frozen=True)
class CustomerContact:
    full_name: str
    phone: str
    email: str
    area: str
    comments: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @property
    def is_empty(self) -> bool:
        return not any(self.to_dict().values())

    @property
    def has_contact_method(self) -> bool:
        return bool(self.phone or self.email)


def render_customer_form(
    key_prefix: str = "customer",
    title: str = "Στοιχεία πελάτη",
) -> CustomerContact:
    st.subheader(title)

    col1, col2 = st.columns(2)
    with col1:
        full_name = st.text_input(
            "Ονοματεπώνυμο",
            key=f"{key_prefix}_full_name",
        )
        email = st.text_input(
            "Email",
            key=f"{key_prefix}_email",
        )

    with col2:
        phone = st.text_input(
            "Τηλέφωνο",
            key=f"{key_prefix}_phone",
        )
        area = st.text_input(
            "Περιοχή",
            key=f"{key_prefix}_area",
        )

    comments = st.text_area(
        "Σχόλια",
        key=f"{key_prefix}_comments",
        height=120,
    )

    return CustomerContact(
        full_name=full_name.strip(),
        phone=phone.strip(),
        email=email.strip(),
        area=area.strip(),
        comments=comments.strip(),
    )
