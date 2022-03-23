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


parents_table = db.Table(
    "parents_table",
    db.Column("parent_id", db.String(40), db.ForeignKey("submission.id"), primary_key=True),
    db.Column("child_id", db.String(40), db.ForeignKey("submission.id"), primary_key=True),
)

class CustomField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.String(40), db.ForeignKey("submission.id"), nullable=False)
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
    custom_field_list = db.relationship("CustomField", lazy=True, backref=db.backref("submission"))

    def asdict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return str(self.asdict())


@app.route("/api/v1/submission", methods=["GET", "POST"])
def submission():
    if request.method == "GET":
        return jsonify({"status":"success", "submission_list": Submission.query.all()})
    req = request.json
    id = str(uuid.uuid4())
    blob_id = str(uuid.uuid4())
    custom_field = req.get("custom_field", {})
    req.pop("custom_field", None)
    parent_id_list = req.get("parent_id_list",[])
    req.pop("parent_id_list", None)
    submission = Submission(id=id, blob_id=blob_id, state="registered", **req)
    if parent_id_list:
        for parent_id in parent_id_list:
            submission.parents.append(Submission.query.get(parent_id))
    else:
        submission.parents.append(submission)
        submission.pangu = True
    for k, v in custom_field.items():
        cf = CustomField(key_name=k, value_type=v.__class__.__name__, value_string=str(v), submission_id=id)
        db.session.add(cf)
    db.session.add(submission)
    db.session.commit()
    return jsonify({"status":"success", "submission": submission})



@app.route("/api/v1/submission/<s_id>/custom_field")
def get_custom_field(s_id):
    custom_field_list = Submission.query.get(s_id).custom_field_list
    custom_field = dict()
    for cf in custom_field_list:
        if cf.value_type == "bool":
            custom_field[cf.key_name] = True if cf.value_string=="True" else False
        elif cf.value_type == "int":
            custom_field[cf.key_name] = int(cf.value_string)
        elif cf.value_type == "float":
            custom_field[cf.key_name] = float(cf.value_string)
        else:
            custom_field[cf.key_name] = cf.value_string
    return jsonify({"status":"success", "custom_field": custom_field})

@app.route("/api/v1/submission/<s_id>/parents")
def parents(s_id):
    parent_list = Submission.query.get(s_id).parents
    # return jsonify({"parents": [p.asdict() for p in parent_list]})
    return jsonify({"status":"success", "parent_list": parent_list})


@app.route("/api/v1/submission/<s_id>/children")
def children(s_id):
    # child_id_list = [c.id for c in Submission.query.get(id).children]
    # return jsonify({"parents": [p.asdict() for p in parent_list]})
    return jsonify({"status":"success", "child_list": Submission.query.get(s_id).children})


@app.route("/api/v1/pangu")
def get_pangu():
    q = Submission.query
    f = q.filter_by(pangu=True).first()
    return jsonify({"status":"success", "id": f.id})

@app.route("/api/v1/refresh")
def refresh():
    db.drop_all()
    db.create_all()
    return jsonify({"status": "success"})


@app.route("/api/v1/s3", methods=["POST"])
def s3_done():
    req = request.json
    # pprint(req)
    blob_id = req.get("Key").split("/")[1]
    submission = Submission.query.filter_by(blob_id=blob_id).limit(1).first()
    submission.state = "uploaded"
    db.session.add(submission)
    db.session.commit()
    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run()
