from pathlib import Path

from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore


KNOWLEDGE_DIR = Path("knowledge")

documents = []

for file_path in KNOWLEDGE_DIR.glob("*.md"):
    text = file_path.read_text(encoding="utf-8")

    documents.append(
        Document(
            page_content=text,
            metadata={
                "source": file_path.name
            }
        )
    )

print(f"Loaded {len(documents)} knowledge documents.")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=700,
    chunk_overlap=100,
)

chunks = splitter.split_documents(documents)

print(f"Created {len(chunks)} chunks.")

embeddings = OllamaEmbeddings(
    model="nomic-embed-text:latest"
)

QdrantVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    url="http://localhost:6333",
    collection_name="k8s_agent_knowledge",
    force_recreate=True,
)

print("Knowledge successfully stored in Qdrant.")
