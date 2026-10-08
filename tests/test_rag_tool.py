from src.rag.rag_tools import search_kubernetes_knowledge


query = "How do I troubleshoot ImagePullBackOff?"

result = search_kubernetes_knowledge.invoke(
    {"query": query}
)

print("========== RAG TOOL RESULT ==========")
print(result)
