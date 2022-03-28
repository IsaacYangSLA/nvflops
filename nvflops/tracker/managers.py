import uuid

from ..utils.cert_utils import SimpleCert
from . import db
from .models import Certificate, SubmissionCustomField, Plan, Submission, VitalSign, VitalSignCustomField

def get_custom_field(model, id):
    cf_list = model.query.get(id).custom_field_list
    custom_field = dict()
    for cf in cf_list:
        if cf.value_type == "bool":
            custom_field[cf.key_name] = True if cf.value_string == "True" else False
        elif cf.value_type == "int":
            custom_field[cf.key_name] = int(cf.value_string)
        elif cf.value_type == "float":
            custom_field[cf.key_name] = float(cf.value_string)
        else:
            custom_field[cf.key_name] = cf.value_string
    return custom_field

class SubmissionManager():
    @staticmethod
    def store_new_entry(**kwargs):
        id = str(uuid.uuid4())
        blob_id = str(uuid.uuid4())
        custom_field = kwargs.get("custom_field", {})
        kwargs.pop("custom_field", None)
        parent_id_list = kwargs.get("parent_id_list", [])
        print(f"submitted {parent_id_list=}")
        kwargs.pop("parent_id_list", None)
        submission = Submission(id=id, blob_id=blob_id, state="registered", **kwargs)
        if parent_id_list:
            for parent_id in parent_id_list:
                submission.parents.append(Submission.query.get(parent_id))
        for k, v in custom_field.items():
            sub_cf = SubmissionCustomField(key_name=k, value_type=v.__class__.__name__, value_string=str(v), submission_id=id)
            db.session.add(sub_cf)
        db.session.add(submission)
        db.session.commit()
        return submission

    @staticmethod
    def update_state(blob_id, state):
        submission = Submission.query.filter_by(blob_id=blob_id).limit(1).first()
        submission.state = state
        db.session.add(submission)
        db.session.commit()
        return submission

    @staticmethod
    def get_custom_field(sub_id):
        custom_field = get_custom_field(Submission, sub_id)
        return custom_field

    @staticmethod
    def get_all():
        all = Submission.query.all()
        return all

    @staticmethod
    def get_parents(sub_id):
        parent_list = Submission.query.get(sub_id).parents
        return parent_list

    @staticmethod
    def get_children(sub_id):
        child_list = Submission.query.get(sub_id).children
        return child_list

    @staticmethod
    def get_root(study):
        q = Submission.query.filter_by(study=study)
        f = q.order_by(Submission.created_at.desc()).first()
        return f

class CertManager():
    @staticmethod
    def store_new_entry(issuer, subject):
        if issuer is None:
            my_cert = SimpleCert(subject, ca=True)
        else:
            _cert = CertManager.get_cert(subject=issuer)
            root = SimpleCert(subject, ca=True, s_crt=_cert.s_crt, s_prv=_cert.s_prv)
            my_cert = SimpleCert(subject)
            my_cert.set_issuer_simple_cert(root)
        my_cert.create_cert()
        my_cert.serialize()
        _cert = Certificate(issuer=issuer, subject=subject, s_crt=my_cert.s_crt, s_prv=my_cert.s_prv)
        db.session.add(_cert)
        db.session.commit()
        return _cert

    @staticmethod
    def get_cert(subject):
        _cert = Certificate.query.filter_by(subject=subject).first()
        return _cert
        
    
class SystemManager():
    @staticmethod
    def init_backend(self):
        db.drop_all()
        db.create_all()
        return True

class PlanManager():
    @staticmethod
    def store_new_entry(**kwargs):
        plan = Plan(**kwargs)
        db.session.add(plan)
        db.session.commit()
        return plan
    
    @staticmethod
    def get_last_plan():
        plan = Plan.query.order_by(Plan.id.desc()).first()
        return plan

class VitalSignManager():
    @staticmethod
    def store_new_entry(**kwargs):
        custom_field = kwargs.get("vital_sign", {})
        kwargs.pop("vital_sign", None)
        vital_sign = VitalSign(**kwargs)
        db.session.add(vital_sign)
        db.session.commit()
        for k, v in custom_field.items():
            cf = VitalSignCustomField(key_name=k, value_type=v.__class__.__name__, value_string=str(v), vital_sign_id=vital_sign.id)
            db.session.add(cf)
        db.session.commit()
        return vital_sign
