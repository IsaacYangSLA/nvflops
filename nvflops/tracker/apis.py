import uuid
from pprint import pprint

from flask import Blueprint, jsonify, request

from ..utils.cert_utils import SimpleCert
from . import db
from .models import Certificate, CustomField, Heartbeat, Plan, Submission, VitalSign

submission = Blueprint("submission", __name__, url_prefix="/api/v1/submission")
s3 = Blueprint("s3", __name__, url_prefix="/api/v1/s3")
admin = Blueprint("admin", __name__, url_prefix="/api/v1/admin")
routine = Blueprint("routine", __name__, url_prefix="/api/v1/routine")


@submission.route("", methods=["GET", "POST"])
def submit():
    if request.method == "GET":
        return jsonify({"status": "success", "submission_list": Submission.query.all()})
    req = request.json
    print(f"{req=}")
    id = str(uuid.uuid4())
    blob_id = str(uuid.uuid4())
    custom_field = req.get("custom_field", {})
    req.pop("custom_field", None)
    parent_id_list = req.get("parent_id_list", [])
    print(f"submitted {parent_id_list=}")
    req.pop("parent_id_list", None)
    submission = Submission(id=id, blob_id=blob_id, state="registered", **req)
    if parent_id_list:
        for parent_id in parent_id_list:
            submission.parents.append(Submission.query.get(parent_id))
    for k, v in custom_field.items():
        cf = CustomField(key_name=k, value_type=v.__class__.__name__, value_string=str(v), submission_id=id)
        db.session.add(cf)
    db.session.add(submission)
    db.session.commit()
    print(f"returned submission {submission=}")
    return jsonify({"status": "success", "submission": submission})


@submission.route("/<s_id>/custom_field")
def get_custom_field(s_id):
    custom_field_list = Submission.query.get(s_id).custom_field_list
    custom_field = dict()
    for cf in custom_field_list:
        if cf.value_type == "bool":
            custom_field[cf.key_name] = True if cf.value_string == "True" else False
        elif cf.value_type == "int":
            custom_field[cf.key_name] = int(cf.value_string)
        elif cf.value_type == "float":
            custom_field[cf.key_name] = float(cf.value_string)
        else:
            custom_field[cf.key_name] = cf.value_string
    return jsonify({"status": "success", "custom_field": custom_field})


@submission.route("/<s_id>/parent")
def parents(s_id):
    parent_list = Submission.query.get(s_id).parents
    # return jsonify({"parents": [p.asdict() for p in parent_list]})
    return jsonify({"status": "success", "parent_list": parent_list})


@submission.route("/<s_id>/child")
def children(s_id):
    # child_id_list = [c.id for c in Submission.query.get(id).children]
    # return jsonify({"parents": [p.asdict() for p in parent_list]})
    return jsonify({"status": "success", "child_list": Submission.query.get(s_id).children})


@submission.route("/root")
def get_root():
    req = request.json
    study = req.get("study", "")
    # q = Submission.query.filter_by(study=study).filter(~Submission.parents.any())
    # f = q.first()
    q = Submission.query.filter_by(study=study)
    f = q.order_by(Submission.created_at.desc()).first()
    print(f"root returns {f.id}")
    return jsonify({"status": "success", "id": f.id})


@admin.route("/provision", methods=["POST"])
def provision():
    req = request.json
    issuer = req.get("issuer")
    subject = req.get("subject")
    if issuer is None:
        issuer = subject
        my_cert = SimpleCert(subject, ca=True)
    else:
        _cert = Certificate.query.filter_by(subject=issuer).first()
        root = SimpleCert(subject, ca=True, s_crt=_cert.s_crt, s_prv=_cert.s_prv)
        my_cert = SimpleCert(subject)
        my_cert.set_issuer_simple_cert(root)
    my_cert.create_cert()
    my_cert.serialize()
    _cert = Certificate(issuer=issuer, subject=subject, s_crt=my_cert.s_crt, s_prv=my_cert.s_prv)
    db.session.add(_cert)
    db.session.commit()
    return jsonify(
        {
            "status": "success",
            "certificate": {"cert": my_cert.s_crt.decode("utf-8"), "key": my_cert.s_prv.decode("utf-8")},
        }
    )


@admin.route("/refresh")
def refresh():
    db.drop_all()
    db.create_all()
    return jsonify({"status": "success"})


@admin.route("/plan", methods=["POST"])
def add_plan():
    req = request.json
    plan = Plan(**req)
    db.session.add(plan)
    db.session.commit()
    return jsonify({"status": "success", "plan": plan})


@routine.route("/heartbeat", methods=["POST"])
def heartbeat():
    req = request.json
    custom_field = req.get("vital_sign", {})
    req.pop("vital_sign", None)
    hb = Heartbeat(**req)
    db.session.add(hb)
    db.session.commit()
    for k, v in custom_field.items():
        cf = VitalSign(key_name=k, value_type=v.__class__.__name__, value_string=str(v), heartbeat_id=hb.id)
        db.session.add(cf)
    db.session.commit()
    plan = Plan.query.order_by(Plan.id.desc()).first()
    print(plan)
    if plan:
        return jsonify({"status": "success", "action": plan.action, "study": plan.study})
    else:
        return jsonify({"status": "success"})


@s3.route("", methods=["POST"])
def s3_done():
    req = request.json
    # pprint(req)
    blob_id = req.get("Key").split("/")[1]
    submission = Submission.query.filter_by(blob_id=blob_id).limit(1).first()
    submission.state = "uploaded"
    db.session.add(submission)
    db.session.commit()
    return jsonify({"status": "success"})
