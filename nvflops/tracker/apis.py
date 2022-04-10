from flask import Blueprint, jsonify, request

from .managers import (
    CertAdm,
    PlanAdm,
    StudyAdm,
    ExpAdm,
    SubmissionManager,
    SystemManager,
    VitalSignManager,
)

submission = Blueprint("submission", __name__, url_prefix="/api/v1/submission")
s3 = Blueprint("s3", __name__, url_prefix="/api/v1/s3")
admin = Blueprint("admin", __name__, url_prefix="/api/v1/admin")
routine = Blueprint("routine", __name__, url_prefix="/api/v1/routine")


def get_mandatory_headers(headers):
    project = headers.get("X-Project")
    if not project:
        return None
    study = headers.get("X-Study")
    if not study:
        return None
    pct = headers.get("X-Pct")
    if not pct:
        return None
    return (project, study, pct)


@submission.route("", methods=["GET", "POST"])
def submit():
    key_tuple = get_mandatory_headers(request.header)
    if not key_tuple:
        return jsonify({"status": "error"})
    if request.method == "GET":
        return jsonify({"status": "success", "submission_list": SubmissionManager.get_all(*key_tuple)})
    req = request.json
    result = SubmissionManager.store_new_entry(*key_tuple, **req)
    if result is None:
        return jsonify({"status": "error"})
    return jsonify({"status": "success", "submission": result})


@submission.route("/<sub_id>/custom_field")
def get_custom_field(sub_id):
    custom_field = SubmissionManager.get_custom_field(sub_id)
    return jsonify({"status": "success", "custom_field": custom_field})


@submission.route("/<sub_id>/parent")
def parents(sub_id):
    parent_list = SubmissionManager.get_parents(sub_id)
    return jsonify({"status": "success", "parent_list": parent_list})


@submission.route("/<sub_id>/child")
def children(sub_id):
    child_list = SubmissionManager.get_children(sub_id)
    return jsonify({"status": "success", "child_list": child_list})


@submission.route("/root")
def get_root():
    req = request.json
    result = SubmissionManager.get_root(**req)
    if result is None:
        return jsonify({"status": "error"})
    return jsonify({"status": "success", "submission": result})


@admin.route("/provision", methods=["POST"])
def provision():
    req = request.json
    issuer = req.pop("issuer", None)
    subject = req.pop("subject", "")
    result = CertManager.store_new_entry(issuer, subject, **req)
    if result is None:
        return jsonify({"status": "error"})
    return jsonify(
        {
            "status": "success",
            "certificate": {"cert": result.s_crt.decode("utf-8"), "key": result.s_prv.decode("utf-8")},
        }
    )


@admin.route("/refresh")
def refresh():
    SystemManager.init_backend()
    return jsonify({"status": "success"})


@admin.route("/plan", methods=["POST"])
def add_plan():
    req = request.json
    result = PlanManager.store_new_entry(**req)
    if result is None:
        return jsonify({"status": "error"})
    return jsonify({"status": "success", "plan": result})


@admin.route("/seed", methods=["POST"])
def seed():
    req = request.json
    project = req.get("project")
    study = req.get("study")
    participants = req.get("participants")
    result = SeedManager.store_new_entry(project=project, study=study, participants=participants)
    if result is None:
        return jsonify({"status": "error"})
    return jsonify({"status": "success", "project": result})


@admin.route("/study", methods=["POST"])
def add_study():
    headers = request.headers
    project = headers.get("X-Project")
    if not project:
        return jsonify({"status": "error"})
    req = request.json
    result = StudyManager.new_entry(project=project, **req)
    if result is None:
        return jsonify({"status": "error"})
    return jsonify({"status": "success", "study": result})


@routine.route("/vital_sign", methods=["POST"])
def vital_sign():
    headers = request.headers
    project = headers.get("X-Project")
    if not project:
        return jsonify({"status": "error"})
    study = headers.get("X-Study")
    if not study:
        return jsonify({"status": "error"})
    pct = headers.get("X-Pct")
    if not pct:
        return jsonify({"status": "error"})
    req = request.json
    key_tuple = (
        project,
        study,
        pct,
    )
    result = VitalSignManager.insert_entry(*key_tuple, **req)
    if result is None:
        return jsonify({"status": "error"})
    exp = ExpAdm.get_current_exp(study, pct)
    result = PlanAdm.get_current_plan(exp.name, study_name=study, project_name=project)
    if result is None:
        return jsonify({"status": "error", "plan": None})
    return jsonify({"status": "success", "plan": result})


@s3.route("", methods=["POST"])
def s3_done():
    req = request.json
    blob_id = req.get("Key").split("/")[1]
    SubmissionManager.update_state(blob_id, "uploaded")
    return jsonify({"status": "success"})
