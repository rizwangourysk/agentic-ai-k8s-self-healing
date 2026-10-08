import subprocess


NAMESPACE = "ai-devops"


def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return f"ERROR:\n{result.stderr}"

    return result.stdout


def get_pods():
    return run_command([
        "kubectl",
        "get",
        "pods",
        "-n",
        NAMESPACE
    ])


def describe_pod(pod_name):
    return run_command([
        "kubectl",
        "describe",
        "pod",
        pod_name,
        "-n",
        NAMESPACE
    ])


def get_logs(pod_name):
    return run_command([
        "kubectl",
        "logs",
        pod_name,
        "-n",
        NAMESPACE
    ])


def get_events():
    return run_command([
        "kubectl",
        "get",
        "events",
        "-n",
        NAMESPACE,
        "--sort-by=.lastTimestamp"
    ])
