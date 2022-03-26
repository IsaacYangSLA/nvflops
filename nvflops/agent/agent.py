import io
import logging
import threading
import time
from typing import Any, Dict, Optional

import minio
import psutil
from requests import Request, RequestException, Session, codes
from requests.adapters import HTTPAdapter


class TrackerAgent:
    def __init__(
        self,
        tracker_end_point,
        blob_end_point,
        bucket_name,
        name: str,
        project = "prj1",
        study = "study1",
        experiment = "exp1",
        heartbeat_interval=5,
    ):
        self._project = project
        self._study = study
        self._experiment = experiment
        self._tracker_end_point = tracker_end_point
        self._blob_end_point = blob_end_point
        self._study = study
        self._name = name
        self._bucket_name = bucket_name
        self._session = None
        self._report_and_query = threading.Thread(target=self._rnq_worker, args=())
        self._status_lock = threading.Lock()
        self._flag = threading.Event()
        self._ca_path = None
        self._cert_path = None
        self._prv_key_path = None
        self._asked_to_exit = False
        self._logger = logging.getLogger(self.__class__.__name__)
        self._retry_delay = 4
        self._asked_to_stop_retrying = False
        self._heartbeat_interval = heartbeat_interval
        self.go = False
        self.stop = False
        self._last_submission_id = ""
        self._tracker_plan = None

    def _send(
        self, api_point, headers: Optional[Dict[str, Any]] = None, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try_count = 0
        while not self._asked_to_stop_retrying:
            try:
                req = Request("POST", api_point, json=payload, headers=headers)
                prepared = self._session.prepare_request(req)
                resp = self._session.send(prepared)
                return resp
            except RequestException as e:
                try_count += 1
                # self._logger.info(f"tried: {try_count} with exception: {e}")
                time.sleep(self._retry_delay)

    def set_secure_context(self, ca_path: str, cert_path: str = "", prv_key_path: str = ""):
        self._ca_path = ca_path
        self._cert_path = cert_path
        self._prv_key_path = prv_key_path

    def start(self, update_callback=None, conditional_cb=False):
        self._session = Session()
        adapter = HTTPAdapter(max_retries=1)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        if self._ca_path:
            self._session.verify = self._ca_path
            self._session.cert = (self._cert_path, self._prv_key_path)
        self.conditional_cb = conditional_cb
        self._blob_client = minio.Minio(self._blob_end_point, secure=False)
        self._report_and_query.start()
        self._flag.set()
        if update_callback:
            self._update_callback = update_callback
        self.get_root()

    def get_root(self):
        api_end_point = self._tracker_end_point + "/submission/root"
        req = Request("GET", api_end_point, json=None, headers=None)
        prepared = self._session.prepare_request(req)
        resp = self._session.send(prepared)
        self._last_submission_id = resp.json().get("id")

    def submit(self, parent_id_list, meta, blob):
        resp = self.submit_meta(parent_id_list, meta)
        self._last_submission = resp.get("submission")
        blob_id = self._last_submission.get("blob_id")
        self._blob_client.put_object(self._bucket_name, blob_id, io.BytesIO(blob), len(blob))
        self._last_submission_id = self._last_submission.get("id")

    def submit_meta(self, parent_id_list, meta, headers=None) -> Dict[str, Any]:
        custom_field = dict()
        payload = dict(parent_id_list=parent_id_list, creator=self._name, custom_field=custom_field)
        api_end_point = self._tracker_end_point + "/submission"
        req = Request("POST", api_end_point, json=payload, headers=headers)
        prepared = self._session.prepare_request(req)
        resp = self._session.send(prepared)
        return resp.json()

    def get_submission(self):
        api_end_point = self._tracker_end_point + f"/submission/{self._last_submission_id}/child"
        req = Request("GET", api_end_point, json=dict(), headers=None)
        prepared = self._session.prepare_request(req)
        resp = self._session.send(prepared)
        return resp.json()

    def get_blob(self, blob_id):
        return self._blob_client.get_object(self._bucket_name, blob_id)

    def _prepare_data(self):
        data = dict(project=self._project, study=self._study, experiment=self._experiment, reporter=self._name)
        return data

    def _rnq_worker(self):
        data = self._prepare_data()
        api_point = self._tracker_end_point + "/routine/heartbeat"
        while not self._asked_to_exit:
            self._flag.wait()
            mem = psutil.virtual_memory()
            data["vital_sign"] = {"cpu": psutil.cpu_percent(), "used_mem": mem.used, "free_mem": mem.free}
            self._rnq(api_point, headers=None, data=data)
            time.sleep(self._heartbeat_interval)

    def _rnq(self, api_point, headers, data):
        resp = self._send(api_point, headers=headers, payload=data)
        if resp is None:
            return
        if resp.status_code != codes.ok:
            return
        self._tracker_plan = resp.json()
        action = self._tracker_plan.get("action")
        if action == "go":
            self.go=True
        elif action == "exit":
            self._asked_to_exit = True
