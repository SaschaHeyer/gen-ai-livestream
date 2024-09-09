import vertexai
from vertexai.preview import rag

vertexai.init(project="sascha-playground-doit", location="us-central1")

# create a corpus
corpus_name = "DoiT company policies"
corpus = rag.create_corpus(display_name="Innovatech", 
                           description="Contains company information of a imaginary company called Innovatech")

print(corpus)
corpus_name = corpus.name
print(corpus_name)

paths = []

# Create a list with the file path repeated 25 times
paths.append("gs://doit-llm/rag-api/nimbuscloud_manual.txt")
paths.append("gs://doit-llm/rag-api/purebrew_manual.txt")
paths.append("gs://doit-llm/rag-api/auraglow_manual.txt")


rag.import_files(
            corpus_name,
            paths,
        )
