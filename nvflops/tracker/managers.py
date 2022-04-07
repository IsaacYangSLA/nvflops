import uuid

from ..utils.cert_utils import SimpleCert
from . import db
from .models import (
    Certificate,
    Experiment,
    Participant,
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


class SubmissionManager:
    @staticmethod
    def store_new_entry(exp, *key_tuple, **kwargs):
        _exp = (
            Experiment.query.join(Study)
            .join(Project)
            .filter(Project.name == key_tuple[0])
            .filter(Study.name == key_tuple[1])
            .filter(Experiment.name == exp)
            .first()
        )
        _pct = (
            Participant.query.join(Project)
            .filter(Project.name == key_tuple[0])
            .filter(Participant.name == key_tuple[2])
            .first()
        )
        id = str(uuid.uuid4())
        blob_id = str(uuid.uuid4())
        custom_field = kwargs.pop("custom_field", {})
        parent_id_list = kwargs.pop("parent_id_list", [])
        print(f"submitted {parent_id_list=}")
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
    def get_all(exp, *key_tuple):
        _exp = Experiment.query.filter_by(name=exp, project=key_tuple[0], study=key_tuple[1]).first()
        _all = Submission.query.filter_by(experiment=_exp).all()
        return _all

    @staticmethod
    def get_parents(sub_id):
        parent_list = Submission.query.get(sub_id).parents
        return parent_list

    @staticmethod
    def get_children(sub_id):
        child_list = Submission.query.get(sub_id).children
        return child_list

    @staticmethod
    def get_root(**kwargs):
        tenant = "123"
        if tenant is None:
            return None
        q = Submission.query.filter_by(tenant=tenant)
        f = q.order_by(Submission.created_at.desc()).first()
        return f


class CertManager:
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


class StudyManager:
    @staticmethod
    def new_entry(project, **kwargs):
        _project = Project.query.filter_by(name=project).first()
        _participants = kwargs.pop("participants")
        _study = Study(project_id=_project.id, **kwargs)
        for item in _participants:
            _pct = Participant.query.get(item)
            _study.participants.append(_pct)
        db.session.add(_study)
        db.session.commit()
        return _study


class PlanManager:
    @staticmethod
    def store_new_entry(**kwargs):
        plan = Plan(**kwargs)
        db.session.add(plan)
        db.session.commit()
        return plan

    @staticmethod
    def get_last_plan(project, study):
        _project = Project.query.filter_by(name=project).first()
        if not _project:
            return None
        _study = Study.query.filter_by(name=study, project_id=_project.id).first()
        if not _study:
            return None
        plan = Plan.query.order_by(Plan.id.desc()).first()
        return plan


class SeedManager:
    @staticmethod
    def store_new_entry(project, study, participants):
        fake_cert = Certificate()
        db.session.add(fake_cert)
        db.session.commit()

        _project = Project(name=project)
        _project.certificate = fake_cert
        db.session.add(_project)
        db.session.commit()

        _study = Study(name=study, project_id=_project.id)
        _study.certificate = fake_cert
        db.session.add(_study)
        db.session.commit()
        _project.studies.append(_study)
        for pct in participants:
            p = Participant(name=pct, project_id=_project.id, cert_id=fake_cert.id)
            db.session.add(p)
            db.session.commit()
            _study.participants.append(p)
        db.session.add(_study)
        db.session.commit()
        return _project

    @staticmethod
    def get_last_plan(project, study):
        _project = Project.query.filter_by(name=project).first()
        if not _project:
            return None
        _study = Study.query.filter_by(name=study, project_id=_project.id).first()
        if not _study:
            return None
        plan = Plan.query.order_by(Plan.id.desc()).first()
        return plan


class ExpManager:
    @staticmethod
    def store_new_entry(**kwargs):
        _exp = Experiment(**kwargs)
        db.session.add(_exp)
        db.session.commit()
        return _exp

    @staticmethod
    def get_current_exp(study):
        _study = Study.query.filter_by(name=study).first()
        if not _study:
            return None
        _exp = Experiment.query.filter_by(study_id=_study.id).order_by(Experiment.id.asc()).first()
        return _exp


class VitalSignManager:
    @staticmethod
    def store_new_entry(project, study, participant, **kwargs):
        # TODO: need to check if user is in project/study
        _participant = Participant.query.filter_by(name=participant).first()
        _custom_field = kwargs.pop("vital_sign", {})
        _vital_sign = VitalSign(participant_id=_participant.id)
        db.session.add(_vital_sign)
        db.session.commit()
        for k, v in _custom_field.items():
            _cf = VitalSignCustomField(
                key_name=k, value_type=v.__class__.__name__, value_string=str(v), vital_sign_id=_vital_sign.id
            )
            db.session.add(_cf)
            db.session.commit()
        return _vital_sign
