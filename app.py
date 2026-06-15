import os
from flask import Flask, render_template, request, jsonify
from config import load_config
from script_loader import load_all_scripts, get_script, render_script
from sanitizer import sanitize_params, ValidationError
from db import init_db, save_run, get_runs, get_run
import winrm_client

flask_app = Flask(__name__)
config = load_config()
init_db()


def _find_vm(name):
    return next((v for v in config.vms if v.name == name), None)


@flask_app.route("/")
def dashboard():
    vm_name = request.args.get("vm", config.vms[0].name if config.vms else None)
    selected_vm = _find_vm(vm_name)
    connected = False
    if selected_vm:
        connected = winrm_client.test_connection(
            selected_vm.ip, config.username, config.password, config.port, config.transport
        )
    return render_template(
        "dashboard.html", vms=config.vms, selected_vm=selected_vm, connected=connected
    )


@flask_app.route("/scripts")
def scripts():
    vm_name = request.args.get("vm")
    selected_vm = _find_vm(vm_name)
    os_tag = selected_vm.os_tag if selected_vm else None
    grouped = load_all_scripts(os_tag=os_tag)
    return render_template(
        "scripts.html", vms=config.vms, selected_vm=selected_vm, grouped=grouped
    )


@flask_app.route("/scripts/<category>/<script_name>/run", methods=["GET", "POST"])
def run_script(category, script_name):
    script = get_script(category, script_name)
    if script is None:
        return "Script not found", 404

    vm_name = request.args.get("vm") or request.form.get("vm")
    selected_vm = _find_vm(vm_name)
    output = None
    error_msg = None
    status = None

    if request.method == "POST" and selected_vm:
        try:
            params = sanitize_params(script.get("parameters", []), request.form)
            ps_script = render_script(script["script"], params)
            stdout, stderr, code = winrm_client.execute_script(
                selected_vm.ip, config.username, config.password, config.port, config.transport, ps_script
            )
            status = "success" if code == 0 else "failed"
            save_run(
                vm_name=selected_vm.name,
                vm_ip=selected_vm.ip,
                script_id=f"{category}/{script_name}",
                script_name=script["name"],
                parameters=request.form.to_dict(),
                status=status,
                stdout=stdout,
                stderr=stderr,
            )
            output = stdout
            if stderr:
                error_msg = stderr
        except ValidationError as e:
            error_msg = str(e)
        except Exception as e:
            error_msg = f"Execution failed: {e}"
            status = "failed"

    return render_template(
        "run_form.html",
        vms=config.vms,
        selected_vm=selected_vm,
        script=script,
        category=category,
        script_name=script_name,
        output=output,
        error_msg=error_msg,
        status=status,
    )


@flask_app.route("/history")
def history():
    vm_filter = request.args.get("vm")
    category_filter = request.args.get("category")
    runs = get_runs(vm_name=vm_filter, category=category_filter)
    categories = ["services", "iis", "processes", "network", "system",
                  "windows_update", "firewall", "scheduled_tasks", "registry"]
    return render_template(
        "history.html",
        vms=config.vms,
        selected_vm=_find_vm(vm_filter),
        runs=runs,
        vm_filter=vm_filter,
        category_filter=category_filter,
        categories=categories,
    )


@flask_app.route("/api/vm/<vm_name>/status")
def vm_status(vm_name):
    vm = _find_vm(vm_name)
    if vm is None:
        return jsonify({"connected": False, "error": "VM not found"}), 404
    connected = winrm_client.test_connection(
        vm.ip, config.username, config.password, config.port, config.transport
    )
    return jsonify({"connected": connected})


if __name__ == "__main__":
    flask_app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
