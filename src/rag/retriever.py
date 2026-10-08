from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore


embeddings = OllamaEmbeddings(
    model="nomic-embed-text:latest"
)

vector_store = QdrantVectorStore.from_existing_collection(
    embedding=embeddings,
    collection_name="k8s_agent_knowledge",
    url="http://localhost:6333",
)


query = "What does ImagePullBackOff mean and how can I fix it?"

results = vector_store.similarity_search(
    query,
    k=2,
)


print("========== RAG RESULTS ==========")

for index, doc in enumerate(results, start=1):

    print(f"\n--- RESULT {index} ---")
    print(f"Source: {doc.metadata.get('source')}")
    print(doc.page_content)
