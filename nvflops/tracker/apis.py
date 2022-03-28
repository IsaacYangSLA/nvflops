from flask import Blueprint, jsonify, request

from .managers import SubmissionManager, CertManager, SystemManager, VitalSignManager, PlanManager

submission = Blueprint("submission", __name__, url_prefix="/api/v1/submission")
s3 = Blueprint("s3", __name__, url_prefix="/api/v1/s3")
admin = Blueprint("admin", __name__, url_prefix="/api/v1/admin")
routine = Blueprint("routine", __name__, url_prefix="/api/v1/routine")

@submission.route("", methods=["GET", "POST"])
def submit():
    if request.method == "GET":
        return jsonify({"status": "success", "list": SubmissionManager.get_all()})
    req = request.json
    print(f"{req=}")
    submission = SubmissionManager.store_new_entry(**req)
    print(f"returned submission {submission=}")
    return jsonify({"status": "success", "submission": submission})


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
    study = req.get("study", "")
    root_submission = SubmissionManager.get_root(study)
    if root_submission:
        return jsonify({"status": "success", "submission": root_submission})
    else:
        return jsonify({"status": "not found", "submission": None})


@admin.route("/provision", methods=["POST"])
def provision():
    req = request.json
    issuer = req.get("issuer")
    subject = req.get("subject")
    cert = CertManager.store_new_entry(issuer, subject)
    return jsonify(
        {
            "status": "success",
            "certificate": {"cert": cert.s_crt.decode("utf-8"), "key": cert.s_prv.decode("utf-8")},
        }
    )


@admin.route("/refresh")
def refresh():
    SystemManager.init_backend()
    return jsonify({"status": "success"})


@admin.route("/plan", methods=["POST"])
def add_plan():
    req = request.json
    plan = PlanManager.store_new_entry(**req)
    return jsonify({"status": "success", "plan": plan})


@routine.route("/vital_sign", methods=["POST"])
def vital_sign():
    req = request.json
    VitalSignManager.store_new_entry(**req)
    plan = PlanManager.get_last_plan()
    print(plan)
    if plan:
        return jsonify({"status": "success", "action": plan.action, "study": plan.study})
    else:
        return jsonify({"status": "success"})


@s3.route("", methods=["POST"])
def s3_done():
    req = request.json
    blob_id = req.get("Key").split("/")[1]
    SubmissionManager.update_state(blob_id, "uploaded")
    return jsonify({"status": "success"})
