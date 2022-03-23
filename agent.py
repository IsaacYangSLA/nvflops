import threading
import logging
import logging
import threading
import time
from typing import Any, Dict, Optional
from requests import Request, RequestException, Session, codes
from requests.adapters import HTTPAdapter
import io

import minio


class TrackerAgent:
    def __init__(
        self,
        role,
        tracker_end_point,
        blob_end_point,
        bucket_name,
        study,
        name: str,
        heartbeat_interval=5,
    ):
        if role not in ["server", "client", "admin"]:
            raise ValueError(f'Expect role in ["server", "client", "admin"] but got {role}')
        self._role = role
        self._tracker_end_point = tracker_end_point
        self._blob_end_point = blob_end_point
        self._study = study
        self._name = name
        self._bucket_name = bucket_name
        self._session = None
        self._status_lock = threading.Lock()
        self._report_and_query = threading.Thread(target=self._rnq_worker, args=())
        self._flag = threading.Event()
        self._ca_path = None
        self._cert_path = None
        self._prv_key_path = None
        self._last_service_session_id = ""
        self._asked_to_exit = False
        self._logger = logging.getLogger(self.__class__.__name__)
        self._retry_delay = 4
        self._asked_to_stop_retrying = False
        self._overseer_info = {}
        self._update_callback = None
        self._conditional_cb = False
        self._heartbeat_interval = heartbeat_interval
        self.go = True
        self.stop = False
        self._last_submission_id = ""

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
        if update_callback:
            self._update_callback = update_callback
        self.get_pangu()
        # self._report_and_query.start()
        # self._flag.set()
        # self._blob_client = minio.Minio("127.0.0.1:9000", secure=False)

    def get_pangu(self):
        api_end_point = self._tracker_end_point + "/pangu"
        req = Request("GET", api_end_point, json=None, headers=None)
        prepared = self._session.prepare_request(req)
        resp = self._session.send(prepared)
        self._last_submission_id = resp.json().get("id")

    def submit(self, parent_id_list, meta, blob):
        resp = self.submit_meta(parent_id_list, meta)
        self._last_submission = resp.get("submission")
        blob_id = self._last_submission.get("blob_id")
        # print(list(client.list_objects("test")))
        self._blob_client.put_object(self._bucket_name, blob_id, io.BytesIO(blob), len(blob))

    def submit_meta(self, parent_id_list, meta, headers=None) -> Dict[str, Any]:
        custom_field = dict()
        payload = dict(parent_id_list=parent_id_list, creator=self._name, custom_field=custom_field)
        api_end_point = self._tracker_end_point + "/submission"
        req = Request("POST", api_end_point, json=payload, headers=headers)
        prepared = self._session.prepare_request(req)
        resp = self._session.send(prepared)
        return resp.json()

    def get_submission(self):
        api_end_point = self._tracker_end_point + f"/submission/{self._last_submission_id}/children"
        req = Request("GET", api_end_point, json=dict(), headers=None)
        prepared = self._session.prepare_request(req)
        resp = self._session.send(prepared)
        return resp.json()

    def get_blob(self, blob_id):
        return self._blob_client.get_object(self._bucket_name, blob_id)

    def pause(self):
        self._asked_to_stop_retrying = True
        self._flag.clear()

    def resume(self):
        self._asked_to_stop_retrying = False
        self._flag.set()

    def end(self):
        self._flag.set()
        self._asked_to_exit = True
        self._report_and_query.join()

    def _do_callback(self):
        if self._update_callback:
            self._update_callback(self)

    def _handle_ssid(self, ssid):
        if not self.conditional_cb or self._last_service_session_id != ssid:
            self._last_service_session_id = ssid
            self._do_callback()

    def _prepare_data(self):
        data = dict(role=self._role, project=self._project)
        return data

    def _rnq_worker(self):
        data = self._prepare_data()
        if self._role == "server":
            data["sp_end_point"] = self._sp_end_point
        api_point = self._overseer_end_point + "/heartbeat"
        while not self._asked_to_exit:
            self._flag.wait()
            self._rnq(api_point, headers=None, data=data)
            time.sleep(self._heartbeat_interval)
