import datetime
import io
import random
import uuid
import minio

from typing import Any, Dict, Optional

from requests import Request, Session
from requests.adapters import HTTPAdapter

api_base_end_point = "http://192.168.1.96:8000/api/v1"
api_end_point = api_base_end_point + "/submission"


def submit_meta(
    api_end_point, headers: Optional[Dict[str, Any]] = None, payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    _session = Session()
    adapter = HTTPAdapter(max_retries=1)
    _session.mount("http://", adapter)
    _session.mount("https://", adapter)
    req = Request("POST", api_end_point, json=payload, headers=headers)
    prepared = _session.prepare_request(req)
    resp = _session.send(prepared)
    return resp.json()


def get_all(api_end_point):
    _session = Session()
    adapter = HTTPAdapter(max_retries=1)
    _session.mount("http://", adapter)
    _session.mount("https://", adapter)
    req = Request("GET", api_end_point)
    prepared = _session.prepare_request(req)
    resp = _session.send(prepared)
    return resp.json()

random_keys = ["foo", "bar", "abc", "xyz"]
random_values = [1, 1.0, "value", True]
for i in range(30):
    all_submission = get_all("http://tinylaptop:8000/api/v1/list").get("submission_list")
    all_id = [sub["id"] for sub in all_submission]
    all_id_len = len(all_id)
    samples = random.randint(0, all_id_len)
    custom_field = dict()
    for j in random.sample(random_keys, random.randint(0, 4)):
        custom_field[j] = random_values[random.randint(0, 3)]
    payload = dict(parent_id_list=random.sample(all_id, samples), custom_field=custom_field, creator=["foo", "bar"][random.randint(0, 1)])
    response = submit_meta(api_end_point, payload=payload)
    my_submission = response.get("submission")
    my_submission_id = my_submission.get("id")
    my_submission_blob_id = my_submission.get("blob_id")

    client = minio.Minio("127.0.0.1:9000", secure=False)
    # print(list(client.list_objects("test")))
    bblob_id = ":".join([my_submission_blob_id] * random.randint(1, 100)).encode("utf-8")
    client.put_object("test", my_submission_blob_id, io.BytesIO(bblob_id), len(bblob_id))

    # print(list(client.list_objects("test")))
