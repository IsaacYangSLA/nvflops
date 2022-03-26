import argparse
import logging
import random
import threading
import time
from pprint import pprint
from typing import Any, Dict, Optional

from requests import Request, RequestException, Session, codes
from requests.adapters import HTTPAdapter

from nvflops.agent.agent import TrackerAgent


def setup_basic_info():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--study", type=str, default="fl_study", help="study name")
    parser.add_argument("-r", "--role", type=str, help="role in this study")
    parser.add_argument("-n", "--name", type=str, help="globally unique name")
    parser.add_argument(
        "-t", "--tracker_end_point", type=str, default="http://192.168.1.96:8000/api/v1", help="tracker_end_point"
    )
    parser.add_argument("-b", "--blob_end_point", type=str, default="192.168.1.96:9000", help="blob end point")
    parser.add_argument("-k", "--bucket_name", type=str, default="test", help="bucket name")

    args = parser.parse_args()

    tracker_agent = TrackerAgent(
        tracker_end_point=args.tracker_end_point,
        blob_end_point=args.blob_end_point,
        bucket_name=args.bucket_name,
        role=args.role,
        study=args.study,
        name=args.name,
        heartbeat_interval=5,
    )
    return tracker_agent


def simple_callback(agent):
    print(f"\nGot callback {agent.get_primary_sp()}")


def main():
    tracker_agent = setup_basic_info()
    tracker_agent.prepare()
    tracker_agent.start_heartbeat(simple_callback, conditional_cb=True)
    while not tracker_agent.go:
        time.sleep(4)
        print("Go action not signaled.")
    print(f"Go signal received, start study {tracker_agent._study}")
    tracker_agent.start_study()
    for i in range(10):
        if tracker_agent._asked_to_exit:
            print("exit signal received")
            break
        while True:
            submissions_to_work = tracker_agent.get_submission().get("child_list", [])
            if len(submissions_to_work) > 0:
                break
            print("Not enough submission to aggregate, sleep for 4 seconds.")
            time.sleep(4)
        blob_id_list = list()
        parent_id_list = list()
        for sub in submissions_to_work:
            sub_id = sub.get("id")
            blob_id = sub.get("blob_id")
            print(f"{sub_id=}, {blob_id=}")
            blob_id_list.append(tracker_agent.get_blob(blob_id))
            parent_id_list.append(sub_id)
        sleep = random.randint(1, 5)
        print(f"Sleep {sleep} sec to simulate aggregating")
        time.sleep(sleep)
        fake_blob_str = ":".join(parent_id_list) * random.randint(1, 10)
        fake_blob = fake_blob_str.encode("utf-8")
        tracker_agent.submit(parent_id_list=parent_id_list, meta={}, blob=fake_blob)


if __name__ == "__main__":
    main()
