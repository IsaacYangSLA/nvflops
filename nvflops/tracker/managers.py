import uuid
from datetime import datetime
from ..utils.cert_utils import SimpleCert
from . import db
from .models import (
    Certificate,
    Experiment,
    Participant,
    ParticipantRole,
    Plan,
    Project,
    Study,
    Submission,
    SubmissionCustomField,
    VitalSign,
    VitalSignCustomField,
)


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


def get_exp_by_key_tuple(exp_name, *key_tuple):
    _exp = (
        Experiment.query.join(Study)
        .join(Project)
        .filter(Project.name == key_tuple[0])
        .filter(Study.name == key_tuple[1])
        .filter(Experiment.name == exp_name)
        .first()
    )
    return _exp


def get_pct_by_key_tuple(*key_tuple):
    _pct = (
        Participant.query.join(Project)
        .filter(Project.name == key_tuple[0])
        .filter(Participant.name == key_tuple[2])
        .first()
    )
    return _pct


class SubmissionManager:
    @staticmethod
    def insert_entry(exp_name, *key_tuple, **kwargs):
        _exp = get_exp_by_key_tuple(exp_name, *key_tuple)
        if not _exp:
            return None
        _pct = get_pct_by_key_tuple(*key_tuple)
        if not _pct:
            return None
        id = str(uuid.uuid4())
        blob_id = str(uuid.uuid4())
        custom_field = kwargs.pop("custom_field", {})
        parent_id_list = kwargs.pop("parent_id_list", [])
        submission = Submission(id=id, blob_id=blob_id, state="registered", pct_id=_pct.id, exp_id=_exp.id)
        if parent_id_list:
            for parent_id in parent_id_list:
                submission.parents.append(Submission.query.get(parent_id))
        for k, v in custom_field.items():
            sub_cf = SubmissionCustomField(
                key_name=k, value_type=v.__class__.__name__, value_string=str(v), submission_id=id
            )
            db.session.add(sub_cf)
        db.session.add(submission)
        db.session.commit()
        return submission

    @staticmethod
    def update_state(blob_id, state):
        _sub = Submission.query.filter_by(blob_id=blob_id).first()
        if not _sub:
            return None
        _sub.state = state
        db.session.add(_sub)
        db.session.commit()
        return _sub

    @staticmethod
    def get_custom_field(sub_id):
        _custom_field = get_custom_field(Submission, sub_id)
        return _custom_field

    @staticmethod
    def get_all(exp, *key_tuple):
        _exp = Experiment.query.filter_by(name=exp, project=key_tuple[0], study=key_tuple[1]).first()
        _all = Submission.query.filter_by(experiment=_exp).all()
        return _all

    @staticmethod
    def get_parents(sub_id):
        _parent_list = Submission.query.get(sub_id).parents
        return _parent_list

    @staticmethod
    def get_children(sub_id):
        _child_list = Submission.query.get(sub_id).children
        return _child_list

    @staticmethod
    def get_root(exp_name, *key_tuple):
        _exp = get_exp_by_key_tuple(exp_name, *key_tuple)
        if not _exp:
            return None
        _root_sub = Submission.query.filter_by(exp_id=_exp.id).order_by(Submission.created_at).first()
        return _root_sub


class CertAdm:
    @staticmethod
    def store_new_entry(issuer, subject, **kwargs):
        if issuer is None:
            my_cert = SimpleCert(subject, ca=True)
        else:
            cert = CertManager.get_cert(subject=issuer)
            root = SimpleCert(subject, ca=True, s_crt=cert.s_crt, s_prv=cert.s_prv)
            my_cert = SimpleCert(subject)
            my_cert.set_issuer_simple_cert(root)
        my_cert.create_cert()
        my_cert.serialize()
        cert = Certificate(issuer=issuer, subject=subject, s_crt=my_cert.s_crt, s_prv=my_cert.s_prv)
        db.session.add(cert)
        db.session.commit()
        return cert

    @staticmethod
    def get_cert(subject):
        _cert = Certificate.query.filter_by(subject=subject).first()
        return _cert


class SystemManager:
    @staticmethod
    def init_backend():
        db.drop_all()
        db.create_all()
        return True


class StudyAdm:
    @staticmethod
    def insert_entry(study_name, *key_tuple, **kwargs):
        _prj = Project.query.filter_by(name=key_tuple[0]).first()
        if not _prj:
            return None
        _pct_name_list = kwargs.pop("participants")
        if not _pct_name_list:
            return None
        _study = Study(name=study_name, project_id=_prj.id)
        for name in _pct_name_list:
            _pct = Participant.query.filter_by(name=name).first()
            if not _pct:
                return None
            _study.participants.append(_pct)
        db.session.add(_study)
        db.session.commit()
        return _study


class PlanAdm:
    @staticmethod
    def insert_entry(plan_name, exp_name, study_name, project_name, **kwargs):
        adm_tuple = (project_name, study_name, "")
        _exp = get_exp_by_key_tuple(exp_name, *adm_tuple)
        _eff_time = datetime.fromisoformat(kwargs.get("effective_time"))
        _action = kwargs.get("action")
        plan = Plan(name=plan_name, effective_time=_eff_time, exp_id=_exp.id, action=_action)
        db.session.add(plan)
        db.session.commit()
        return plan

    @staticmethod
    def get_current_plan(exp_name, study_name, project_name):
        _exp = get_exp_by_key_tuple(exp_name, *(project_name, study_name, ""))
        if not _exp:
            return None
        plan = Plan.query.filter_by(exp_id=_exp.id).order_by(Plan.id.desc()).first()
        return plan


class ExpAdm:
    @staticmethod
    def insert_entry(exp_name, study_name, project_name, **kwargs):
        _study = Study.query.filter_by(name=study_name).join(Project).filter(Project.name == project_name).first()
        blob_id = str(uuid.uuid4())
        _exp = Experiment(name=exp_name, study_id=_study.id, blob_id=blob_id)
        db.session.add(_exp)
        db.session.flush()
        pct_name_role_dict = kwargs.get("participants")
        if not pct_name_role_dict:
            return None
        for k, v in pct_name_role_dict.items():
            _pct = Participant.query.filter_by(name=k).first()
            # TODO: risky query
            # join(Study).filter(Participant.name == k).filter(Study.name == study_name).first()
            if not _pct:
                return None
            _pct_role = ParticipantRole(role=v, exp_id=_exp.id, pct_id=_pct.id)
        _exp.participant_roles.append(_pct_role)
        db.session.add(_exp)
        db.session.commit()
        return _exp

    @staticmethod
    def get_current_exp(study, pct):
        _study = Study.query.filter_by(name=study).join(Participant).filter(Participant.name == pct).first()
        if not _study:
            return None
        _exp = Experiment.query.filter_by(study_id=_study.id).order_by(Experiment.id.asc()).first()
        return _exp


class VitalSignManager:
    @staticmethod
    def insert_entry(*key_tuple, **kwargs):
        _pct = get_pct_by_key_tuple(*key_tuple)
        if not _pct:
            return None
        _custom_field = kwargs.pop("vital_sign", {})
        _vital_sign = VitalSign(participant_id=_pct.id)
        db.session.add(_vital_sign)
        for k, v in _custom_field.items():
            _cf = VitalSignCustomField(
                key_name=k, value_type=v.__class__.__name__, value_string=str(v), vital_sign_id=_vital_sign.id
            )
            db.session.add(_cf)
        db.session.commit()
        return _vital_sign
