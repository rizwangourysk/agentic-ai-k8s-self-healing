from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.tools import tool


embeddings = OllamaEmbeddings(
    model="nomic-embed-text:latest"
)

vector_store = QdrantVectorStore.from_existing_collection(
    embedding=embeddings,
    collection_name="k8s_agent_knowledge",
    url="http://localhost:6333",
)


@tool
def search_kubernetes_knowledge(query: str) -> str:
    """
    Search the Kubernetes troubleshooting knowledge base
    for relevant troubleshooting and self-healing guidance.
    """

    results = vector_store.similarity_search(
        query,
        k=3,
    )

    if not results:
        return "No relevant Kubernetes knowledge found."

    output = []

    for index, doc in enumerate(results, start=1):
        source = doc.metadata.get("source", "unknown")

        output.append(
            f"RESULT {index}\n"
            f"SOURCE: {source}\n"
            f"{doc.page_content}"
        )

    return "\n\n".join(output)
