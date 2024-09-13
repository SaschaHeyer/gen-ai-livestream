start_time = protobuf.timestamp_pb2.Timestamp()
start_time.GetCurrentTime()
end_time = protobuf.timestamp_pb2.Timestamp()
end_time.GetCurrentTime()

source = rag.SlackChannelsSource(
        channels = [
            SlackChannel("CHANNEL1", "api_key1"),
            SlackChannel("CHANNEL2", "api_key2", START_TIME, END_TIME)
        ],
    )

response = rag.import_files(
        corpus_name="projects/my-project/locations/us-central1/ragCorpora/my-corpus-1",
        source=source,
        chunk_size=512,
        chunk_overlap=100,
    )