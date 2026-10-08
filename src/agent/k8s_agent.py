import json
import re

from langchain_ollama import ChatOllama
from langchain.tools import tool
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from src.tools.kubernetes_tools import (
    get_pods,
    describe_pod,
    get_logs,
    get_events,
)

from src.tools.healing_tools import (
    heal_image_pull_error,
    verify_deployment,
)

from src.rag.rag_tools import search_kubernetes_knowledge

from src.agent.logging_config import logger


# ============================================================
# Kubernetes investigation tools
# ============================================================

@tool
def kubernetes_get_pods() -> str:
    """Get current Kubernetes pods in the ai-devops namespace."""
    return get_pods()


@tool
def kubernetes_describe_pod(pod_name: str) -> str:
    """Get detailed information about a Kubernetes pod."""
    return describe_pod(pod_name)


@tool
def kubernetes_get_logs(pod_name: str) -> str:
    """Get logs from a Kubernetes pod."""
    return get_logs(pod_name)


@tool
def kubernetes_get_events() -> str:
    """Get Kubernetes events in the ai-devops namespace."""
    return get_events()


# ============================================================
# Self-healing tools
# ============================================================

@tool
def self_heal_image_pull_error() -> str:
    """
    Repair the controlled agent-healing-demo image pull failure.
    """
    return heal_image_pull_error()


@tool
def verify_self_healing() -> str:
    """
    Verify that the controlled deployment successfully rolled out.
    """
    return verify_deployment()


# ============================================================
# All tools available to the Agent
# ============================================================

tools = [
    kubernetes_get_pods,
    kubernetes_describe_pod,
    kubernetes_get_logs,
    kubernetes_get_events,
    search_kubernetes_knowledge,
    self_heal_image_pull_error,
    verify_self_healing,
]


tool_map = {
    selected_tool.name: selected_tool
    for selected_tool in tools
}


# ============================================================
# LLM
# ============================================================

llm = ChatOllama(
    model="qwen2.5-coder:7b",
    temperature=0,
)

llm_with_tools = llm.bind_tools(tools)

logger.info("Agent started")


# ============================================================
# Fallback parser
#
# Some Ollama/Qwen responses may return tool calls as JSON
# text instead of response.tool_calls.
# ============================================================

def extract_text_tool_calls(content: str):
    calls = []

    matches = re.findall(
        r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
        content,
        re.DOTALL,
    )

    if not matches:
        matches = re.findall(
            r'\{"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{.*?\}\}',
            content,
            re.DOTALL,
        )

    for match in matches:
        try:
            data = json.loads(match)

            calls.append(
                {
                    "name": data["name"],
                    "args": data.get("arguments", {}),
                    "id": f"call_{len(calls) + 1}",
                }
            )

        except json.JSONDecodeError:
            logger.error(
                "Failed to parse tool call JSON: %s",
                match,
            )

    return calls


# ============================================================
# Agent conversation
# ============================================================

messages = [
    SystemMessage(
        content=(
            "You are an Agentic AI Kubernetes self-healing agent.\n\n"

            "Your workflow is:\n"
            "1. Detect the Kubernetes problem.\n"
            "2. Investigate using Kubernetes tools.\n"
            "3. Search the Kubernetes knowledge base when useful.\n"
            "4. Diagnose the root cause.\n"
            "5. Apply an approved healing action when appropriate.\n"
            "6. Verify recovery.\n"
            "7. Explain the final result.\n\n"

            "Rules:\n"
            "- Investigate before healing.\n"
            "- Use real Kubernetes evidence.\n"
            "- Use search_kubernetes_knowledge for troubleshooting guidance.\n"
            "- Only use self_heal_image_pull_error for the controlled "
            "agent-healing-demo image-pull failure.\n"
            "- After healing, always use verify_self_healing.\n"
            "- Do not perform unrelated destructive actions.\n"
            "- Do not claim a pod is Pending unless the Kubernetes evidence "
            "actually shows Pending.\n"
            "- Distinguish ErrImagePull and ImagePullBackOff from Pending.\n"
        )
    ),

    HumanMessage(
        content=(
            "Investigate the Kubernetes deployment "
            "agent-healing-demo in namespace ai-devops.\n\n"

            "Determine whether it has an image pull problem. "
            "Use Kubernetes evidence and retrieve relevant troubleshooting "
            "knowledge from the RAG knowledge base.\n\n"

            "If the deployment has an image pull failure, perform the "
            "approved self-healing action and verify recovery.\n\n"

            "At the end, explain:\n"
            "1. What failed.\n"
            "2. The root cause.\n"
            "3. What knowledge was used.\n"
            "4. What healing action was performed.\n"
            "5. Whether the deployment recovered."
        )
    ),
]


# ============================================================
# Agent loop
# ============================================================

for step in range(10):

    logger.info("Starting agent step %s", step + 1)

    response = llm_with_tools.invoke(messages)

    messages.append(response)

    print(f"\n========== AGENT STEP {step + 1} ==========")

    tool_calls = []

    # --------------------------------------------------------
    # Native LangChain tool calls
    # --------------------------------------------------------

    if response.tool_calls:

        for call in response.tool_calls:
            tool_calls.append(
                {
                    "name": call["name"],
                    "args": call["args"],
                    "id": call["id"],
                }
            )

    # --------------------------------------------------------
    # Fallback text-based tool calls
    # --------------------------------------------------------

    if not tool_calls and isinstance(response.content, str):

        tool_calls = extract_text_tool_calls(
            response.content
        )

    # --------------------------------------------------------
    # Execute tools
    # --------------------------------------------------------

    if tool_calls:

        print("Tools selected by Qwen:")

        for call in tool_calls:

            tool_name = call["name"]
            tool_args = call["args"]

            print(f"- {tool_name}")
            print(f"  arguments: {tool_args}")

            logger.info(
                "Tool selected: %s | arguments=%s",
                tool_name,
                tool_args,
            )

            # ------------------------------------------------
            # Safety check: only execute registered tools
            # ------------------------------------------------

            if tool_name not in tool_map:

                print(
                    f"ERROR: Unknown tool: {tool_name}"
                )

                logger.error(
                    "Unknown tool requested: %s",
                    tool_name,
                )

                continue

            selected_tool = tool_map[tool_name]

            try:

                result = selected_tool.invoke(
                    tool_args
                )

                print(
                    "  Tool executed successfully"
                )

                logger.info(
                    "Tool executed successfully: %s",
                    tool_name,
                )

                messages.append(
                    ToolMessage(
                        content=result,
                        tool_call_id=call["id"],
                    )
                )

            except Exception as error:

                print(
                    f"  Tool execution failed: {error}"
                )

                logger.error(
                    "Tool execution failed: %s | error=%s",
                    tool_name,
                    error,
                )

                messages.append(
                    ToolMessage(
                        content=f"Tool execution failed: {error}",
                        tool_call_id=call["id"],
                    )
                )

    # --------------------------------------------------------
    # Final answer
    # --------------------------------------------------------

    else:

        logger.info("Agent completed")

        print(
            "\n========== FINAL AGENT ANSWER =========="
        )

        print(response.content)

        break


logger.info("Agent run finished")
