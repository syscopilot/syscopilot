from syscopilot.system_graph import SystemGraph

for path in ["rest_system.json", "kafka_stream_pipeline.json", "batch_etl.json"]:
    g = SystemGraph.model_validate_json(open("system_examples/" + path, "rb").read())
    print(path, "OK", len(g.nodes), "nodes", len(g.edges), "edges")