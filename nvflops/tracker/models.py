from datetime import datetime

from . import db


class TimestampMixin(object):
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class CustomFieldMixin(object):
    id = db.Column(db.Integer, primary_key=True)
    key_name = db.Column(db.String(40))
    value_type = db.Column(db.String(40))
    value_string = db.Column(db.String(40))

parents_table = db.Table(
    "parents_table",
    db.Column("parent_id", db.String(40), db.ForeignKey("submission.id")),
    db.Column("child_id", db.String(40), db.ForeignKey("submission.id")),
)

class SubmissionCustomField(CustomFieldMixin, db.Model):
    submission_id = db.Column(db.String(40), db.ForeignKey("submission.id"), nullable=False)

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Certificate(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issuer = db.Column(db.String(40))
    subject = db.Column(db.String(40))
    s_crt = db.Column(db.String(2000))
    s_prv = db.Column(db.String(2000))


class Submission(TimestampMixin, db.Model):
    id = db.Column(db.String(40), primary_key=True)
    study = db.Column(db.String(40))
    description = db.Column(db.String(400))
    creator = db.Column(db.String(40))
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

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return str(self.asdict())


class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(10))
    project = db.Column(db.String(40))
    study = db.Column(db.String(40))
    experiment = db.Column(db.String(40))

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class VitalSignCustomField(CustomFieldMixin, db.Model):
    vital_sign_id = db.Column(db.Integer, db.ForeignKey("vital_sign.id"), nullable=False)

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class VitalSign(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project = db.Column(db.String(40))
    study = db.Column(db.String(40))
    experiment = db.Column(db.String(40))
    subject = db.Column(db.String(40))
    custom_field_list = db.relationship("VitalSignCustomField", lazy=True, backref=db.backref("vital_sign"))

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return str(self.asdict())
