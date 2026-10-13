import json
import logging
import re

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

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

from src.rag.rag_tools import (
    search_kubernetes_knowledge as rag_search_tool,
)


# ==================================================
# CONFIGURATION
# ==================================================

NAMESPACE = "ai-devops"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ==================================================
# KUBERNETES TOOLS
# ==================================================

@tool
def kubernetes_get_pods(namespace: str = "ai-devops") -> str:
    """Get the current Kubernetes pods and their statuses."""

    if namespace != NAMESPACE:
        return f"ERROR: Only namespace '{NAMESPACE}' is allowed."

    return str(get_pods())


@tool
def kubernetes_describe_pod(
    pod_name: str,
    namespace: str = "ai-devops",
) -> str:
    """Describe a Kubernetes pod to investigate its condition."""

    if namespace != NAMESPACE:
        return f"ERROR: Only namespace '{NAMESPACE}' is allowed."

    if not pod_name:
        return "ERROR: A pod name is required."

    return str(describe_pod(pod_name))


@tool
def kubernetes_get_logs(
    pod_name: str,
    namespace: str = "ai-devops",
) -> str:
    """Get logs from a Kubernetes pod."""

    if namespace != NAMESPACE:
        return f"ERROR: Only namespace '{NAMESPACE}' is allowed."

    if not pod_name:
        return "ERROR: A pod name is required."

    return str(get_logs(pod_name))


@tool
def kubernetes_get_events(namespace: str = "ai-devops") -> str:
    """Get recent Kubernetes events."""

    if namespace != NAMESPACE:
        return f"ERROR: Only namespace '{NAMESPACE}' is allowed."

    return str(get_events())


# ==================================================
# SELF-HEALING TOOLS
# ==================================================

@tool
def self_heal_image_pull_error() -> str:
    """
    Attempt safety-checked recovery for the demonstration
    Kubernetes image-pull failure.
    """

    return str(heal_image_pull_error())


@tool
def verify_self_healing() -> str:
    """
    Verify deployment rollout, image, pod status,
    and container readiness.
    """

    return str(verify_deployment())


# ==================================================
# RAG TOOL
# ==================================================

@tool
def search_kubernetes_knowledge(query: str) -> str:
    """Search the Kubernetes troubleshooting knowledge base."""

    if not query.strip():
        return "ERROR: A search query is required."

    result = rag_search_tool.invoke({"query": query})

    return str(result)


# ==================================================
# REGISTER TOOLS
# ==================================================

tools = [
    kubernetes_get_pods,
    kubernetes_describe_pod,
    kubernetes_get_logs,
    kubernetes_get_events,
    search_kubernetes_knowledge,
    self_heal_image_pull_error,
    verify_self_healing,
]

tools_by_name = {
    registered_tool.name: registered_tool
    for registered_tool in tools
}


# ==================================================
# OLLAMA MODEL
# ==================================================

llm = ChatOllama(
    model="qwen2.5-coder:7b",
    temperature=0,
)

llm_with_tools = llm.bind_tools(tools)


# ==================================================
# TEXT TOOL-CALL PARSER
# ==================================================

def extract_text_tool_calls(content):
    """
    Extract tool calls from JSON, fenced JSON,
    or <tool_call> JSON returned as text.
    """

    if not isinstance(content, str):
        return []

    content = content.strip()

    if not content:
        return []

    tagged_matches = re.findall(
        r"<tool_call>\s*(.*?)\s*</tool_call>",
        content,
        flags=re.DOTALL,
    )

    parsed_calls = []

    if tagged_matches:
        for item in tagged_matches:
            try:
                parsed_calls.append(json.loads(item))
            except json.JSONDecodeError:
                logger.warning(
                    "Could not parse tagged tool-call JSON."
                )

    else:
        cleaned = re.sub(
            r"^\s*```(?:json)?\s*",
            "",
            content,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```\s*$",
            "",
            cleaned,
        ).strip()

        try:
            parsed = json.loads(cleaned)

        except json.JSONDecodeError:
            return []

        if isinstance(parsed, dict):
            parsed_calls.append(parsed)

        elif isinstance(parsed, list):
            parsed_calls.extend(parsed)

    extracted_calls = []

    for index, item in enumerate(parsed_calls):

        if not isinstance(item, dict):
            continue

        function_data = item.get("function", {})

        if not isinstance(function_data, dict):
            function_data = {}

        name = (
            item.get("name")
            or function_data.get("name")
        )

        arguments = (
            item.get("arguments")
            or item.get("args")
            or function_data.get("arguments")
            or function_data.get("args")
            or {}
        )

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)

            except json.JSONDecodeError:
                logger.warning(
                    "Invalid JSON arguments for tool '%s'.",
                    name,
                )
                continue

        if not isinstance(arguments, dict):
            continue

        if not name:
            continue

        extracted_calls.append(
            {
                "name": name,
                "args": arguments,
                "id": item.get("id") or f"text_call_{index}",
            }
        )

    return extracted_calls


# ==================================================
# TOOL EXECUTION
# ==================================================

def execute_tool(tool_name, tool_args):
    """
    Execute only registered tools.
    Return the actual tool result as a string.
    """

    selected_tool = tools_by_name.get(tool_name)

    if selected_tool is None:
        return (
            f"ERROR: Tool '{tool_name}' "
            "is not registered. No tool was executed."
        )

    try:
        logger.info(
            "Executing tool: %s | Arguments: %s",
            tool_name,
            tool_args,
        )

        result = selected_tool.invoke(tool_args)

        actual_result = str(result)

        logger.info(
            "Actual result from %s: %s",
            tool_name,
            actual_result,
        )

        return actual_result

    except Exception as exc:
        logger.exception(
            "Tool execution failed: %s",
            tool_name,
        )

        return (
            f"ERROR while executing {tool_name}: "
            f"{type(exc).__name__}: {exc}"
        )


# ==================================================
# NORMALIZE MODEL RESPONSE
# ==================================================

def get_response_text(response):
    """Convert the model response content into text."""

    content = response.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for part in content:

            if (
                isinstance(part, dict)
                and part.get("type") == "text"
            ):
                text_parts.append(
                    part.get("text", "")
                )

        return "\n".join(text_parts)

    return str(content)


# ==================================================
# MAIN AGENT
# ==================================================

def run_agent():

    system_prompt = """
You are an AI-powered Kubernetes troubleshooting agent.

Your Kubernetes namespace is ai-devops.

Follow these rules carefully:

1. Start by calling kubernetes_get_pods.

2. Investigate the actual current Kubernetes results.

3. Never assume an old example describes the current problem.

4. If a pod is unhealthy, investigate it using
   kubernetes_describe_pod and kubernetes_get_logs
   when appropriate.

5. Use kubernetes_get_events to investigate relevant events.

6. Use search_kubernetes_knowledge to find relevant
   troubleshooting information.

7. Do not call a healing tool unless current evidence
   indicates a relevant problem.

8. The healing tool has its own safety checks.
   Never bypass them.

9. After a healing attempt, call verify_self_healing.

10. If the pods are healthy, report their actual status
    without attempting to heal them.

11. Treat actual tool execution results as the source
    of truth.

12. Never invent tool results, pod names, events,
    image names, or verification outcomes.

13. Never claim that healing succeeded unless the actual
    tool result confirms success.

14. If a tool returns ERROR, report that error honestly.

15. Use simple English in your final answer.

16. Avoid repeatedly calling the same tool without reason.

17. Finish with a concise summary of status, evidence,
    and actions taken.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                "Investigate the live Kubernetes cluster "
                "in namespace ai-devops. Check the pods first. "
                "Investigate unhealthy pods using actual "
                "Kubernetes evidence. Use RAG when relevant. "
                "Only attempt healing when the current evidence "
                "and the healing tool's safety checks permit it."
            )
        ),
    ]

    print(
        "\n========== KUBERNETES SELF-HEALING AGENT ==========\n"
    )

    max_iterations = 10

    for iteration in range(max_iterations):

        logger.info(
            "Agent iteration %s",
            iteration + 1,
        )

        try:
            response = llm_with_tools.invoke(messages)

        except Exception as exc:
            logger.exception("Ollama request failed.")

            print(
                f"\nERROR: Ollama request failed: {exc}"
            )
            return

        # --------------------------------------------------
        # CASE 1: Native LangChain tool calls
        # --------------------------------------------------

        native_calls = (
            getattr(response, "tool_calls", None) or []
        )

        if native_calls:

            # Preserve the assistant message containing
            # the native tool calls.
            messages.append(response)

            for index, call in enumerate(native_calls):

                tool_name = call.get("name")
                tool_args = call.get("args") or {}
                tool_id = (
                    call.get("id")
                    or f"native_call_{iteration}_{index}"
                )

                result = execute_tool(
                    tool_name,
                    tool_args,
                )

                # Return the actual result to the model.
                messages.append(
                    ToolMessage(
                        content=result,
                        tool_call_id=tool_id,
                    )
                )

            continue

        # --------------------------------------------------
        # READ MODEL RESPONSE
        # --------------------------------------------------

        response_content = get_response_text(response)

        # --------------------------------------------------
        # CASE 2: Tool calls returned as text
        # --------------------------------------------------

        text_calls = extract_text_tool_calls(
            response_content
        )

        if text_calls:

            # Preserve the original assistant response.
            messages.append(response)

            for call in text_calls:

                tool_name = call["name"]
                tool_args = call["args"]

                result = execute_tool(
                    tool_name,
                    tool_args,
                )

                # Supply the actual result to the model.
                messages.append(
                    HumanMessage(
                        content=(
                            "The following is the actual result "
                            "returned by Python tool execution.\n"
                            f"Tool: {tool_name}\n"
                            f"Arguments: {json.dumps(tool_args)}\n"
                            f"Actual result: {result}\n\n"
                            "Use this result as the source of truth. "
                            "Do not invent or change the result. "
                            "Continue the investigation."
                        )
                    )
                )

            continue

        # --------------------------------------------------
        # CASE 3: Normal final answer
        # --------------------------------------------------

        print(
            "\n========== FINAL AGENT ANSWER ==========\n"
        )

        print(response_content)

        print(
            "\n========================================\n"
        )

        return

    print(
        "\nAgent stopped after reaching the maximum "
        "number of iterations. Review the logs for "
        "repeated tool calls or errors."
    )


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":
    run_agent()
