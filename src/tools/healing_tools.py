import json
import subprocess


# ==================================================
# CONFIGURATION
# ==================================================

NAMESPACE = "ai-devops"
DEPLOYMENT = "agent-healing-demo"
CONTAINER = "app"

BAD_IMAGE = "nginx:this-image-does-not-exist"
FIXED_IMAGE = "nginx:latest"


# ==================================================
# RUN KUBERNETES COMMANDS
# ==================================================

def run_command(command):
    """Run a command and return its output or error."""

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=70,
        )

    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out."

    except OSError as exc:
        return f"ERROR: Could not execute command: {exc}"

    if result.returncode != 0:
        return f"ERROR:\n{result.stderr.strip()}"

    return result.stdout.strip()


# ==================================================
# GET CURRENT DEPLOYMENT IMAGE
# ==================================================

def get_current_image():
    """Get the image configured for the app container."""

    command = [
        "kubectl",
        "get",
        "deployment",
        DEPLOYMENT,
        "-n",
        NAMESPACE,
        "-o",
        "jsonpath={.spec.template.spec.containers[?(@.name=='app')].image}",
    ]

    return run_command(command)


# ==================================================
# GET CURRENT IMAGE-PULL FAILURE
# ==================================================

def get_current_failure_reason():
    """Read image-pull failure reasons from matching pods."""

    command = [
        "kubectl",
        "get",
        "pods",
        "-n",
        NAMESPACE,
        "-l",
        "app=agent-healing-demo",
        "-o",
        "jsonpath={range .items[*].status.containerStatuses[*]}{.state.waiting.reason}{' '}{end}",
    ]

    return run_command(command)


# ==================================================
# SELF-HEALING
# ==================================================

def heal_image_pull_error():
    """
    Fix the demonstration image-pull failure only when
    the expected broken image and failure reason are confirmed.
    """

    current_image = get_current_image()

    if current_image.startswith("ERROR:"):
        return f"HEALING_FAILED: Could not read deployment image. {current_image}"

    current_reason = get_current_failure_reason()

    if current_reason.startswith("ERROR:"):
        return f"HEALING_FAILED: Could not read pod failure reason. {current_reason}"

    print(f"Current image: {current_image}")
    print(f"Current failure reason: {current_reason}")

    # Safety check 1:
    # Only fix the specifically configured demonstration image.
    if current_image != BAD_IMAGE:
        return (
            "HEALING_NOT_ALLOWED: "
            f"Current image is '{current_image}'. "
            f"Expected broken image '{BAD_IMAGE}'. "
            "No Kubernetes change was made."
        )

    # Safety check 2:
    # Only proceed when Kubernetes reports an image-pull failure.
    allowed_reasons = {
        "ErrImagePull",
        "ImagePullBackOff",
    }

    reasons = set(current_reason.split())

    if not reasons.intersection(allowed_reasons):
        return (
            "HEALING_NOT_REQUIRED: "
            f"Current failure reason is '{current_reason}'. "
            "No Kubernetes change was made."
        )

    # Approved demonstration remediation.
    command = [
        "kubectl",
        "set",
        "image",
        f"deployment/{DEPLOYMENT}",
        f"{CONTAINER}={FIXED_IMAGE}",
        "-n",
        NAMESPACE,
    ]

    result = run_command(command)

    if result.startswith("ERROR:"):
        return f"HEALING_FAILED: {result}"

    return (
        "HEALING_SUCCESS: "
        f"Changed {DEPLOYMENT}/{CONTAINER} "
        f"from {BAD_IMAGE} to {FIXED_IMAGE}."
    )


# ==================================================
# VERIFY RECOVERY
# ==================================================

def verify_deployment():
    """
    Verify rollout, expected image, pod existence,
    pod Running state, and container readiness.
    """

    # Step 1: Check rollout.
    rollout_command = [
        "kubectl",
        "rollout",
        "status",
        f"deployment/{DEPLOYMENT}",
        "-n",
        NAMESPACE,
        "--timeout=60s",
    ]

    rollout_result = run_command(rollout_command)

    if rollout_result.startswith("ERROR:"):
        return f"VERIFICATION_FAILED: {rollout_result}"

    # Step 2: Check the actual deployment image.
    current_image = get_current_image()

    if current_image.startswith("ERROR:"):
        return (
            "VERIFICATION_FAILED: "
            f"Could not read deployment image: {current_image}"
        )

    if current_image != FIXED_IMAGE:
        return (
            "VERIFICATION_FAILED: "
            f"Expected image '{FIXED_IMAGE}', "
            f"but found '{current_image}'."
        )

    # Step 3: Get matching pods as JSON.
    pod_command = [
        "kubectl",
        "get",
        "pods",
        "-n",
        NAMESPACE,
        "-l",
        "app=agent-healing-demo",
        "-o",
        "json",
    ]

    pod_result = run_command(pod_command)

    if pod_result.startswith("ERROR:"):
        return (
            "VERIFICATION_FAILED: "
            f"Could not read pods: {pod_result}"
        )

    # Step 4: Parse Kubernetes JSON.
    try:
        pod_data = json.loads(pod_result)

    except (json.JSONDecodeError, TypeError):
        return (
            "VERIFICATION_FAILED: "
            "Kubernetes returned invalid pod JSON."
        )

    pods = pod_data.get("items", [])

    if not pods:
        return (
            "VERIFICATION_FAILED: "
            "No matching pods were found."
        )

    # Step 5: Check each pod and its containers.
    for pod in pods:
        pod_name = pod.get("metadata", {}).get("name", "unknown")

        phase = pod.get("status", {}).get("phase")

        if phase != "Running":
            return (
                "VERIFICATION_FAILED: "
                f"Pod '{pod_name}' is in phase '{phase}', "
                "not Running."
            )

        container_statuses = (
            pod.get("status", {}).get("containerStatuses", [])
        )

        if not container_statuses:
            return (
                "VERIFICATION_FAILED: "
                f"Pod '{pod_name}' has no container status information."
            )

        for container_status in container_statuses:
            if not container_status.get("ready", False):
                container_name = container_status.get("name", "unknown")

                return (
                    "VERIFICATION_FAILED: "
                    f"Container '{container_name}' in pod "
                    f"'{pod_name}' is not Ready."
                )

    # Step 6: Report success only after all checks pass.
    return (
        "VERIFICATION_SUCCESS\n"
        f"Image: {current_image}\n"
        f"Rollout: {rollout_result}\n"
        f"Ready pods: {len(pods)}\n"
        "All matching pods are Running and all their containers are Ready."
    )
