from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolarModel:
    brand: str
    capacity: int
    area: float
    kind: str
    price: float

    @property
    def kind_label(self) -> str:
        if self.kind:
            return self.kind
        return "2πλής ενέργειας"


DELTA_MODELS: list[SolarModel] = [
    SolarModel("Delta Solar", 120, 1.95, "2πλής", 888.00),
    SolarModel("Delta Solar", 120, 1.95, "3πλής", 950.00),
    SolarModel("Delta Solar", 150, 1.95, "2πλής", 906.00),
    SolarModel("Delta Solar", 150, 1.95, "3πλής", 968.00),
    SolarModel("Delta Solar", 150, 2.24, "2πλής", 933.00),
    SolarModel("Delta Solar", 150, 2.24, "3πλής", 995.00),
    SolarModel("Delta Solar", 170, 2.52, "2πλής", 995.00),
    SolarModel("Delta Solar", 170, 2.52, "3πλής", 1058.00),
    SolarModel("Delta Solar", 200, 3.10, "2πλής", 1151.00),
    SolarModel("Delta Solar", 200, 3.10, "3πλής", 1214.00),
    SolarModel("Delta Solar", 200, 4.00, "2πλής", 1240.00),
    SolarModel("Delta Solar", 200, 4.00, "3πλής", 1303.00),
    SolarModel("Delta Solar", 170, 2.58, "3πλής ΑΘ", 1196.00),
    SolarModel("Delta Solar", 200, 3.10, "3πλής ΑΘ", 1366.00),
]

CALPAK_MODELS: list[SolarModel] = [
    SolarModel("Calpak", 160, 2.13, "", 1380.00),
    SolarModel("Calpak", 200, 3.06, "", 1760.00),
]


@dataclass(frozen=True)
class SolarProposalInput:
    people: int
    mounting: str
    has_program: bool
    subsidy_rate: float
    wants_installments: bool
    bad_orientation: bool
    shading: bool
    triple_mode: str
    need_crane: str
    wants_install: bool
    replace_old: str
    has_hot_cold_stubs: str | None


@dataclass(frozen=True)
class SolarProposal:
    base_capacity: int
    delta_model: SolarModel
    calpak_model: SolarModel
    delta_product_price: float
    calpak_product_price: float
    install_cost: float
    delta_total: float
    calpak_total: float
    subsidy_rate: float
    delta_customer_share: float
    calpak_customer_share: float
    delta_monthly_payment: float
    calpak_monthly_payment: float
    shading: bool


def pick_capacity_from_people(people: int) -> int:
    if people <= 2:
        return 120
    if people <= 4:
        return 150
    if people == 5:
        return 170
    return 200


def pick_delta_model(base_capacity: int, triple_mode: str, bad_orientation: bool) -> SolarModel:
    """Pick the Delta Solar model using the rules from the original app."""
    if triple_mode == "hp":
        candidates = [model for model in DELTA_MODELS if model.kind == "3πλής ΑΘ"]
        suitable = [model for model in candidates if model.capacity >= base_capacity]
        if not suitable:
            suitable = candidates
        return sorted(suitable, key=lambda model: model.capacity)[0]

    wanted_kind = "3πλής" if triple_mode == "boiler" else "2πλής"
    candidates = [
        model
        for model in DELTA_MODELS
        if model.kind == wanted_kind and model.capacity == base_capacity
    ]

    if not candidates:
        candidates = [model for model in DELTA_MODELS if model.kind == wanted_kind]
        candidates = sorted(candidates, key=lambda model: abs(model.capacity - base_capacity))

    if len(candidates) > 1:
        return sorted(candidates, key=lambda model: model.area, reverse=bad_orientation)[0]

    return candidates[0]


def pick_calpak_model(people: int) -> SolarModel:
    capacity = 160 if people <= 4 else 200
    return [model for model in CALPAK_MODELS if model.capacity == capacity][0]


def apply_program_discount(price: float, has_program: bool) -> float:
    if has_program:
        return price
    return round(price * 0.95)


def calc_install_cost(
    mounting: str,
    wants_install: bool,
    replace_old: str,
    need_crane: str,
    has_hot_cold_stubs: str | None,
) -> float:
    if not wants_install:
        return 0.0

    cost = 250.0 if mounting == "Κεραμοσκεπή" else 200.0

    if replace_old == "Ναι":
        cost += 40.0
    if need_crane == "Ναι":
        cost += 80.0
    if has_hot_cold_stubs == "Όχι":
        cost += 80.0

    return cost


def calc_monthly_payment(principal: float, annual_rate: float = 0.13, months: int = 36) -> float:
    if principal <= 0 or months <= 0:
        return 0.0

    monthly_rate = annual_rate / 12.0
    if abs(monthly_rate) < 1e-9:
        return principal / months

    return principal * monthly_rate / (1 - (1 + monthly_rate) ** (-months))


def customer_share(total: float, subsidy_rate: float) -> float:
    return total * (1 - subsidy_rate)


def build_solar_proposal(inputs: SolarProposalInput) -> SolarProposal:
    base_capacity = pick_capacity_from_people(inputs.people)
    delta_model = pick_delta_model(
        base_capacity=base_capacity,
        triple_mode=inputs.triple_mode,
        bad_orientation=inputs.bad_orientation,
    )
    calpak_model = pick_calpak_model(inputs.people)

    delta_product_price = apply_program_discount(delta_model.price, inputs.has_program)
    calpak_product_price = apply_program_discount(calpak_model.price, inputs.has_program)

    if inputs.mounting == "Κεραμοσκεπή":
        delta_product_price += 40.0

    install_cost = calc_install_cost(
        mounting=inputs.mounting,
        wants_install=inputs.wants_install,
        replace_old=inputs.replace_old,
        need_crane=inputs.need_crane,
        has_hot_cold_stubs=inputs.has_hot_cold_stubs,
    )

    delta_total = delta_product_price + install_cost
    calpak_total = calpak_product_price + install_cost

    delta_customer_share = customer_share(delta_total, inputs.subsidy_rate)
    calpak_customer_share = customer_share(calpak_total, inputs.subsidy_rate)

    delta_monthly_payment = (
        calc_monthly_payment(delta_customer_share)
        if inputs.wants_installments
        else 0.0
    )
    calpak_monthly_payment = (
        calc_monthly_payment(calpak_customer_share)
        if inputs.wants_installments
        else 0.0
    )

    return SolarProposal(
        base_capacity=base_capacity,
        delta_model=delta_model,
        calpak_model=calpak_model,
        delta_product_price=delta_product_price,
        calpak_product_price=calpak_product_price,
        install_cost=install_cost,
        delta_total=delta_total,
        calpak_total=calpak_total,
        subsidy_rate=inputs.subsidy_rate,
        delta_customer_share=delta_customer_share,
        calpak_customer_share=calpak_customer_share,
        delta_monthly_payment=delta_monthly_payment,
        calpak_monthly_payment=calpak_monthly_payment,
        shading=inputs.shading,
    )


def format_eur(value: float) -> str:
    return f"{value:,.0f} €"
