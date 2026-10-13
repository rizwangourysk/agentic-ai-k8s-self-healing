# Agentic AI Kubernetes Self-Healing

## 1. Project Overview

This project uses Agentic AI to investigate and recover from selected Kubernetes application failures.

The agent uses a Large Language Model (LLM), Kubernetes tools, and Retrieval-Augmented Generation (RAG) to investigate problems and select an appropriate action.

The project demonstrates how AI can help DevOps engineers troubleshoot Kubernetes workloads.

## 2. Project Objectives

* Detect Kubernetes pod problems.
* Collect information about pods, logs, and events.
* Search Kubernetes troubleshooting documentation using RAG.
* Diagnose selected application failures.
* Apply a controlled remediation when safety conditions are satisfied.
* Verify deployment recovery.
* Report investigation results in simple English.

## 3. Architecture

The project follows this workflow:

1. The AI agent receives a troubleshooting task.
2. The agent checks the Kubernetes cluster.
3. Kubernetes tools collect live cluster information.
4. The agent investigates the failure.
5. The RAG component searches relevant troubleshooting documents.
6. The agent selects an available remediation tool.
7. The healing tool checks its safety conditions.
8. The tool applies the approved change if the conditions are satisfied.
9. The verification tool checks the deployment rollout and pod status.
10. The agent reports the result.

## 4. Technologies Used

* Python
* Kubernetes
* kind
* kubectl
* Docker
* Ollama
* Qwen2.5-Coder
* LangChain
* Qdrant
* Retrieval-Augmented Generation (RAG)
* Git and GitHub
* pytest for automated testing

## 5. Project Structure

```text
agentic-ai-k8s-self-healing/
├── knowledge/
│   ├── image-pull-errors.md
│   └── kubernetes-self-healing.md
├── src/
│   ├── agent/
│   │   ├── k8s_agent.py
│   │   ├── llm_test.py
│   │   └── logging_config.py
│   ├── rag/
│   │   ├── ingest.py
│   │   ├── rag_tools.py
│   │   └── retriever.py
│   └── tools/
│       ├── healing_tools.py
│       └── kubernetes_tools.py
├── tests/
│   ├── agent-healing-demo.yaml
│   ├── test_healing_tools.py
│   ├── test_kubernetes_tools.py
│   └── test_rag_tool.py
├── .gitignore
├── README.md
└── requirements.txt
```

## 6. Prerequisites

Install or configure the following tools:

* Python 3
* Docker
* kubectl
* kind
* Ollama
* A supported local LLM
* Qdrant
* Git

The commands in this README should be adapted to your operating system and existing installation.

## 7. Python Environment

Clone the repository:

```bash
git clone https://github.com/rizwangourysk/agentic-ai-k8s-self-healing.git
cd agentic-ai-k8s-self-healing
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## 8. Ollama Configuration

Download the model used by the project:

```bash
ollama pull qwen2.5-coder:7b
```

Download the embedding model used for RAG:

```bash
ollama pull nomic-embed-text:latest
```

Confirm the models are available:

```bash
ollama list
```

The project currently uses the Ollama endpoint:

```text
http://localhost:11434
```

## 9. Kubernetes Configuration

Check whether the Kubernetes cluster is available:

```bash
kubectl get nodes
```

Check application pods:

```bash
kubectl get pods -n ai-devops
```

The existing demonstration environment uses a kind cluster and the `ai-devops` namespace.

Make sure the cluster and namespace exist before running Kubernetes tests.

## 10. Qdrant and RAG

Qdrant stores the vector representations of the project knowledge documents.

The RAG component uses an embedding model to find relevant troubleshooting information.

The project knowledge includes:

* Kubernetes image-pull errors
* ImagePullBackOff
* ErrImagePull
* Kubernetes self-healing procedures

The configured Qdrant endpoint is:

```text
http://localhost:6333
```

The configured collection is:

```text
k8s_agent_knowledge
```

The collection must be populated before running the RAG search tool. Follow the ingestion implementation in `src/rag/ingest.py` to initialize or update the collection.

## 11. Run the AI Agent

Activate the virtual environment:

```bash
source venv/bin/activate
```

Run the agent:

```bash
python -m src.agent.k8s_agent
```

The agent checks the cluster and uses its registered tools to investigate Kubernetes workloads.

The exact actions depend on the live cluster state and the agent's tool-selection logic.

## 12. Run the Existing Checks

Test the Kubernetes tools:

```bash
python -m tests.test_kubernetes_tools
```

Test the healing safety logic:

```bash
python -m tests.test_healing_tools
```

Test RAG retrieval:

```bash
python -m tests.test_rag_tool
```

These existing scripts are useful functional checks. They are not a substitute for a complete automated pytest suite.

## 13. Image-Pull Failure Demonstration

The project includes a controlled demonstration involving an invalid container image.

An invalid image can cause Kubernetes to report:

```text
ErrImagePull
ImagePullBackOff
```

The healing function checks the configured deployment image and the current failure reason before changing the image.

If the expected failure is not present, the function refuses to make the change.

When the safety conditions are satisfied, the demonstration can update the image to a valid configured image.

**Important:** Only perform this demonstration in a test cluster. Changing a deployment image affects the running workload.

After a healing attempt, check the deployment:

```bash
kubectl rollout status deployment/agent-healing-demo -n ai-devops
```

Check the pods:

```bash
kubectl get pods -n ai-devops
```

Confirm the actual deployment image:

```bash
kubectl get deployment agent-healing-demo -n ai-devops \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="app")].image}'
```

A successful rollout alone should not be treated as complete proof that every application-level requirement has been satisfied.

## 14. Troubleshooting

### Ollama is unavailable

Check the installed models:

```bash
ollama list
```

Check that the Ollama service is accessible:

```bash
curl http://localhost:11434/api/tags
```

### Kubernetes pods are unhealthy

Inspect the pods:

```bash
kubectl get pods -n ai-devops
```

Describe the affected pod:

```bash
kubectl describe pod <pod-name> -n ai-devops
```

Read the application logs:

```bash
kubectl logs <pod-name> -n ai-devops
```

### RAG search fails

Check whether Qdrant is running:

```bash
docker ps
```

Check the Qdrant endpoint:

```bash
curl http://localhost:6333/collections
```

Confirm that the required collection exists and contains the ingested knowledge.

### ImagePullBackOff occurs

Inspect the pod and its events:

```bash
kubectl describe pod <pod-name> -n ai-devops
```

Check the image configured in the deployment and confirm that the image exists in its registry.

## 15. Security and Safety

* Use a dedicated development Kubernetes cluster for experiments.
* Do not store access tokens, passwords, or cloud credentials in Git.
* Do not commit the virtual environment.
* Keep Kubernetes permissions as limited as practical.
* Validate the live failure state before remediation.
* Require appropriate approval before applying changes to production.
* Verify the workload after remediation.
* Report failures honestly instead of claiming that recovery succeeded without evidence.

## 16. Future Improvements

Potential improvements include:

* Automated unit tests with pytest.
* End-to-end agent workflow tests.
* More Kubernetes failure scenarios.
* Structured logs and execution reports.
* Human approval before remediation.
* Support for additional recovery tools.
* Monitoring and alert integration.

## 17. Author and Repository

GitHub repository:

https://github.com/rizwangourysk/agentic-ai-k8s-self-healing

This project is a learning demonstration of Agentic AI, RAG, and Kubernetes self-healing. Validate changes in a test environment before considering production use.

