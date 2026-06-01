class ValidationError(Exception):
    pass


def sanitize_params(parameters: list, form_data: dict) -> dict:
    """
    Validate form values against parameter definitions and escape for PowerShell.

    Text values are wrapped in single quotes with internal single quotes doubled,
    producing a safe PS single-quoted string literal.
    Number values are validated and passed through as strings.
    """
    result = {}
    for param in parameters:
        name = param["name"]
        raw = form_data.get(name, "").strip()

        if not raw:
            if param.get("required", False):
                raise ValidationError(f"'{param['label']}' is required")
            raw = str(param.get("default", ""))

        param_type = param.get("type", "text")

        if param_type == "number":
            try:
                float(raw)
            except ValueError:
                raise ValidationError(f"'{param['label']}' must be a number, got: {raw!r}")
            result[name] = raw
        else:
            escaped = raw.replace("'", "''")
            result[name] = f"'{escaped}'"

    return result
