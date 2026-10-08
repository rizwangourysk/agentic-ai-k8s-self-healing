from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="qwen2.5-coder:7b",
    temperature=0
)

response = llm.invoke(
    "Explain in one simple sentence what Kubernetes ImagePullBackOff means."
)

print("========== QWEN RESPONSE ==========")
print(response.content)
