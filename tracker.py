from pprint import pprint
from datetime import datetime
import os
import uuid

from flask import jsonify, request, Flask, json
from flask.json import JSONEncoder

app = Flask(__name__)
app.config["APPLICATION_ROOT"] = "/api/v1"
from flask_sqlalchemy import SQLAlchemy

app.config.from_mapping(
    SECRET_KEY=os.environ.get("SECRET_KEY") or "dev_key",
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(os.getcwd(), "status.sqlite"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app)


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, db.Model):
                return obj.asdict()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


app.json_encoder = CustomJSONEncoder


class TimestampMixin(object):
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)


# class Test(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     parents = db.relationship('Test', secondary=test_table, lazy='subquery')

parents_table = db.Table(
    "parents_table",
    db.Column("parent_id", db.String(40), db.ForeignKey("submission.id"), primary_key=True),
    db.Column("child_id", db.String(40), db.ForeignKey("submission.id"), primary_key=True),
)


class CustomField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission = db.Column(db.String(40), db.ForeignKey("submission.id"), nullable=False)
    key_name = db.Column(db.String(40))
    value_type = db.Column(db.String(40))
    value_string = db.Column(db.String(40))

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Submission(TimestampMixin, db.Model):
    id = db.Column(db.String(40), primary_key=True)
    pangu = db.Column(db.Boolean, default=False)
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
    custom_field_list = db.relationship("CustomField", lazy=False)
    # parents = db.relationship('Submission', secondary=parents_table, primaryjoin=id == parents_table.c.child_id,
    # secondaryjoin=id == parents_table.c.parent_id,
    # backref=db.backref('children'), lazy='subquery')
    # parents = db.relationship('Submission', secondary=parent_table, lazy='subquery')

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return str(self.asdict())


@app.route("/api/v1/submission", methods=["POST"])
def submission():
    req = request.json
    id = str(uuid.uuid4())
    blob_id = str(uuid.uuid4())
    submission = Submission(id=id, blob_id=blob_id, state="registered")
    parent_id_list = req.get("parent_id_list")
    if parent_id_list:
        for parent_id in parent_id_list:
            submission.parents.append(Submission.query.get(parent_id))
    else:
        submission.parents.append(submission)
        submission.pangu = True
    custom_field = req.get("custom_field", {})
    for k, v in custom_field.items():
        submission.custom_field_list.append(CustomField(key_name=k, value_type=str(type(v)), value_string=str(v)))
    db.session.add(submission)
    db.session.commit()
    return jsonify({"blob_id": blob_id})


@app.route("/api/v1/list")
def list_all():
    return jsonify({"all": Submission.query.all()})


@app.route("/api/v1/<id>/parents")
def parents(id):
    parent_list = Submission.query.get(id).parents
    # return jsonify({"parents": [p.asdict() for p in parent_list]})
    return jsonify({"parents": parent_list})


@app.route("/api/v1/<id>/children")
def children(id):
    # child_id_list = [c.id for c in Submission.query.get(id).children]
    # return jsonify({"parents": [p.asdict() for p in parent_list]})
    return jsonify({"children": Submission.query.get(id).children})


@app.route("/api/v1/refresh")
def refresh():
    db.drop_all()
    db.create_all()
    return jsonify({"Status": "Success"})


@app.route("/api/v1/s3", methods=["POST"])
def s3_done():
    req = request.json
    # pprint(req)
    blob_id = req.get("Key").split("/")[1]
    submission = Submission.query.filter_by(blob_id=blob_id).limit(1).first()
    submission.state = "uploaded"
    db.session.add(submission)
    db.session.commit()
    return jsonify({"Status": "Success"})


if __name__ == "__main__":
    app.run()
