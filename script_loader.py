from pathlib import Path
from jinja2 import Environment, BaseLoader
import yaml

DEFAULT_SCRIPTS_DIR = Path(__file__).parent / "scripts"


def load_all_scripts(os_tag=None, scripts_dir=None):
    """Load all scripts grouped by category, filtered by os_tag."""
    base = Path(scripts_dir) if scripts_dir else DEFAULT_SCRIPTS_DIR
    result = {}
    for category_dir in sorted(base.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        scripts = []
        for yml_file in sorted(category_dir.glob("*.yml")):
            script = _load_yaml(yml_file)
            if script and _matches_os(script.get("os_target", "all"), os_tag):
                script["id"] = yml_file.stem
                script["category"] = category
                scripts.append(script)
        if scripts:
            result[category] = scripts
    return result


def get_script(category, script_name, scripts_dir=None):
    """Load a single script by category and filename stem."""
    base = Path(scripts_dir) if scripts_dir else DEFAULT_SCRIPTS_DIR
    path = base / category / f"{script_name}.yml"
    if not path.exists():
        return None
    script = _load_yaml(path)
    if script:
        script["id"] = script_name
        script["category"] = category
    return script


def render_script(script_body, params):
    """Render the PS script Jinja2 template with sanitized parameter values."""
    env = Environment(loader=BaseLoader())
    template = env.from_string(script_body)
    return template.render(**params)


def _load_yaml(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _matches_os(os_target, os_tag):
    if os_target == "all" or os_tag is None:
        return True
    return os_target == os_tag
