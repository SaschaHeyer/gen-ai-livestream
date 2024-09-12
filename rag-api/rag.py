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

#import_files = rag.import_files(corpus_name=corpus_name, 
#                            paths=["./documents/company-policy.txt"], 
#                            chunk_size=50)
#print(import_files)

# add document to the corpus
rag_file = rag.upload_file(
   corpus_name=corpus_name,
   path="./documents/auraglow_manual.txt",
)

rag_file = rag.upload_file(
   corpus_name=corpus_name,
   path="./documents/nimbuscloud_manual.txt",
)

#rag_file = rag.upload_file(
#   corpus_name=corpus_name,
#   path="./documents/purebrew_manual.txt",
#)

#print(rag_file)

# get the corpus
corpus = rag.get_corpus(name=corpus_name)
print(corpus)

# retrieve documents
response = rag.retrieval_query(
        rag_resources=[
            rag.RagResource(
                rag_corpus=corpus_name,
            )
        ],
        text="How do I install the LED light strip?",
        similarity_top_k=10,  # Optional
        vector_distance_threshold=0.5,  # lower distance means the document as a high similarity to our query
    )
print(response)

