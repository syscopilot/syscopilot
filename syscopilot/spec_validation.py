from collections import Counter

from .models import SystemSpec


def _duplicate_id_warnings(ids: list[str], label: str) -> list[str]:
    counts = Counter(ids)
    return [f"duplicate {label} id: {item_id}" for item_id, count in counts.items() if count > 1]


def validate_spec_semantics(spec: SystemSpec) -> list[str]:
    warnings: list[str] = []

    component_ids = [component.id for component in spec.components]
    link_ids = [link.id for link in spec.links]
    store_ids = [store.id for store in spec.data_stores]
    contract_ids = [contract.id for contract in spec.contracts]

    warnings.extend(_duplicate_id_warnings(component_ids, "component"))
    warnings.extend(_duplicate_id_warnings(link_ids, "link"))
    warnings.extend(_duplicate_id_warnings(store_ids, "data_store"))
    warnings.extend(_duplicate_id_warnings(contract_ids, "contract"))

    component_id_set = set(component_ids)
    for link in spec.links:
        if link.from_id not in component_id_set:
            warnings.append(f"dangling link.from_id: {link.id} -> {link.from_id}")
        if link.to_id not in component_id_set:
            warnings.append(f"dangling link.to_id: {link.id} -> {link.to_id}")

    for contract in spec.contracts:
        if contract.owner_component_id not in component_id_set:
            warnings.append(
                f"dangling contract.owner_component_id: {contract.id} -> {contract.owner_component_id}"
            )

    return warnings
