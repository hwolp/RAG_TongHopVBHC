def enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)

