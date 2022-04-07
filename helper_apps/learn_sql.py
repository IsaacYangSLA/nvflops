from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

app = Flask(__name__)
db = SQLAlchemy()
db.init_app(app)
app.app_context().push()


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


# from sqlalchemy_mixins import AllFeaturesMixin

######### Models #########
# class BaseModel(db.Model, AllFeaturesMixin):
#     __abstract__ = True
#     pass


parents_table = db.Table(
    "parents_table",
    db.Column("parent_id", db.String(40), db.ForeignKey("submission.id")),
    db.Column("child_id", db.String(40), db.ForeignKey("submission.id")),
)


study_participant_table = db.Table(
    "study_participant_table",
    db.Column("study_id", db.Integer, db.ForeignKey("study.id"), primary_key=True),
    db.Column("participant_id", db.Integer, db.ForeignKey("participant.id"), primary_key=True),
)


class CommonMixin(object):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25))
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)


class CustomFieldMixin(object):
    id = db.Column(db.Integer, primary_key=True)
    key_name = db.Column(db.String(25))
    value_type = db.Column(db.String(25))
    value_string = db.Column(db.String(25))

    def __repr__(self):
        return str(self.asdict())


"""
clients are any participants talking to tracker via tracker's api

Root CA -> tracker cert (role=server) + sub CA cert (role=subca)
sub CA -> client certs (role=client)

project := sub CA, participants := clients
study := subset of clients, one set of python codes
experiment := specific python codes (may reuse study code) and role for each participant
plan := a sequence of actions, occuring at specific time

submission := data generated by any client, including meta, defined in Submission,
such as participant, blob's state, parents, children and experiment,
and a blob, stored in blob storage

vital_sign := continuous information from clients to tracker.  Not suitable for
query, but good for monitoring/dashboard.

"""


class Submission(db.Model):
    id = db.Column(db.String(40), primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey("participant.id"), nullable=False)
    state = db.Column(db.String(10), nullable=False)
    blob_id = db.Column(db.String(40), index=True)
    parents = db.relationship(
        "Submission",
        secondary=parents_table,
        primaryjoin=id == parents_table.c.child_id,
        secondaryjoin=id == parents_table.c.parent_id,
        lazy=False,
        backref=db.backref("children"),
    )
    custom_field_list = db.relationship("SubmissionCustomField", lazy=True, backref=db.backref("submission"))
    exp_id = db.Column(db.Integer, db.ForeignKey("experiment.id"), nullable=False)

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SubmissionCustomField(CustomFieldMixin, db.Model):
    sub_id = db.Column(db.Integer, db.ForeignKey("submission.id"), nullable=False)

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# One project has one sub-ca cert
class Project(CommonMixin, db.Model):
    studies = db.relationship("Study", lazy=True, backref="project")
    participants = db.relationship("Participant", lazy="dynamic", backref=db.backref("project", uselist=False))

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Study(CommonMixin, db.Model):
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    participants = db.relationship(
        "Participant", secondary=study_participant_table, lazy="subquery", backref=db.backref("studies", lazy=False)
    )
    experiments = db.relationship("Experiment", lazy=True, backref=db.backref("study", uselist=False))

    def asdict(self):
        base_dict = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        base_dict.update({"participants": self.participants})
        return base_dict


class ParticipantRole(CommonMixin, db.Model):
    pct_id = db.Column(db.Integer, db.ForeignKey("participant.id"), nullable=False)
    role = db.Column(db.String(10))
    exp_id = db.Column(db.Integer, db.ForeignKey("experiment.id"), nullable=False)


class Experiment(CommonMixin, db.Model):
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    plans = db.relationship("Plan", lazy=True, backref=db.backref("experiment"))
    blob_id = db.Column(db.String(40))
    participant_roles = db.relationship("ParticipantRole", lazy=True, backref=db.backref("experiment"))


class Participant(CommonMixin, db.Model):
    submissions = db.relationship("Submission", lazy=True, backref="participant")
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# Plan basically is the action for one experiment,
# such as waiting, go, pause, resume, end
class Plan(CommonMixin, db.Model):
    action = db.Column(db.String(10))
    effective_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    exp_id = db.Column(db.Integer, db.ForeignKey("experiment.id"), nullable=False)

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SubmissionManager:
    @staticmethod
    def store_new_entry(exp, *key_tuple, **kwargs):
        _exp = Experiment.query.filter(
            Experiment.name == exp, Experiment.project.name == key_tuple[0], Experiment.study.name == key_tuple[1]
        ).first()
        id = str(uuid.uuid4())
        blob_id = str(uuid.uuid4())
        custom_field = kwargs.pop("custom_field", {})
        parent_id_list = kwargs.pop("parent_id_list", [])
        print(f"submitted {parent_id_list=}")
        submission = Submission(blob_id=blob_id, state="registered", **kwargs)
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


db.drop_all()
db.create_all()
key_tuple = ("proj1", "study1", "site1")

p1 = Project(name="proj1")
# db.session.add(p1)
# db.session.flush()
s1 = Study(name="study1")
p1.studies.append(s1)
db.session.add(p1)
db.session.commit()
print(p1)
print(s1)
