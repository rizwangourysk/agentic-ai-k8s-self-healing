import subprocess


NAMESPACE = "ai-devops"
DEPLOYMENT = "agent-healing-demo"
CONTAINER = "app"

BAD_IMAGE = "nginx:this-image-does-not-exist"
FIXED_IMAGE = "nginx:latest"


def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return f"ERROR:\n{result.stderr.strip()}"

    return result.stdout.strip()


def get_current_image():
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


def get_current_failure_reason():
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


def heal_image_pull_error():
    current_image = get_current_image()
    current_reason = get_current_failure_reason()

    print(f"Current image: {current_image}")
    print(f"Current failure reason: {current_reason}")

    # Safety check 1:
    # Only heal the intentionally broken image.
    if current_image != BAD_IMAGE:
        return (
            "HEALING_NOT_ALLOWED: "
            f"Current image is '{current_image}'. "
            f"Expected broken image '{BAD_IMAGE}'. "
            "No Kubernetes change was made."
        )

    # Safety check 2:
    # Only heal real image-pull failures.
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

    # Approved healing action
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


def verify_deployment():
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

    current_image = get_current_image()

    pod_command = [
        "kubectl",
        "get",
        "pods",
        "-n",
        NAMESPACE,
        "-l",
        "app=agent-healing-demo",
    ]

    pod_result = run_command(pod_command)

    return (
        "VERIFICATION_SUCCESS\n"
        f"Image: {current_image}\n"
        f"Rollout: {rollout_result}\n"
        f"Pods:\n{pod_result}"
    )
