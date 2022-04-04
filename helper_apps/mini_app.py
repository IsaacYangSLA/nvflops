from nvflops.participant.agent import TrackerAgent

ta = TrackerAgent("http://localhost:8000/api/v1", "localhost:9000", "test", "p1", "aggregator")
ta.set_insecure_content(project="prj1", study="study1")
ta.prepare_connection()
ta.start_reporting_vital_signs()
