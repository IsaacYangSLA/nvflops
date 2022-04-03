from datetime import datetime

from . import db

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
    cert_id = db.Column(db.Integer, db.ForeignKey("certificate.id"), nullable=False)
    certificate = db.relationship("Certificate", lazy=True, uselist=False)
    studies = db.relationship("Study", lazy=True, backref="project")
    participants = db.relationship("Participant", lazy="dynamic", backref=db.backref("project", uselist=False))

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Study(CommonMixin, db.Model):
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    participants = db.relationship(
        "Participant", secondary=study_participant_table, lazy="subquery", backref=db.backref("studies", lazy=False)
    )

    def asdict(self):
        base_dict = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        base_dict.update({"participants": self.participants})
        return base_dict


class Experiment(CommonMixin, db.Model):
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    plans = db.relationship("Plan", lazy=True, backref=db.backref("experiment"))


class Participant(CommonMixin, db.Model):
    cert_id = db.Column(db.Integer, db.ForeignKey("certificate.id"), nullable=False)
    certificate = db.relationship("Certificate", lazy=True, uselist=False)
    submissions = db.relationship("Submission", lazy=True, backref="participant")
    vital_signs = db.relationship("VitalSign", lazy=True, backref=db.backref("participant"))
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# Root CA does not change and must be pre-provisioned.
# Tracker cert has to be pre-provisioned before running.
# TODO: tools to generate such information to be inserted to DB.
class Certificate(CommonMixin, db.Model):
    fingerprint = db.Column(db.String(40), index=True)
    issuer = db.Column(db.String(25))
    subject = db.Column(db.String(25))
    s_crt = db.Column(db.String(2000))
    s_prv = db.Column(db.String(2000))
    role = db.Column(db.String(10))

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


class VitalSignCustomField(CustomFieldMixin, db.Model):
    vital_sign_id = db.Column(db.Integer, db.ForeignKey("vital_sign.id"), nullable=False)

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class VitalSign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    participant_id = db.Column(db.Integer, db.ForeignKey("participant.id"), nullable=False)
    custom_field_list = db.relationship("VitalSignCustomField", lazy=True, backref=db.backref("vital_sign"))

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
