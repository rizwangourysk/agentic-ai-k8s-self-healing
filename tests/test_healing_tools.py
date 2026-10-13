from unittest.mock import call

from src.tools import healing_tools


def test_healthy_image_blocks_healing(monkeypatch):
    """Do not change a deployment that is already using the healthy image."""

    mock_run = lambda command: (
        "nginx:latest"
        if "deployment" in command
        else ""
    )

    monkeypatch.setattr(
        healing_tools,
        "run_command",
        mock_run,
    )

    result = healing_tools.heal_image_pull_error()

    assert result.startswith("HEALING_NOT_ALLOWED")
    assert "No Kubernetes change was made" in result


def test_invalid_image_without_failure_blocks_healing(monkeypatch):
    """Do not heal when the expected image-pull failure is absent."""

    responses = [
        healing_tools.BAD_IMAGE,
        "",
    ]

    def mock_run(command):
        return responses.pop(0)

    monkeypatch.setattr(
        healing_tools,
        "run_command",
        mock_run,
    )

    result = healing_tools.heal_image_pull_error()

    assert result.startswith("HEALING_NOT_REQUIRED")
    assert "No Kubernetes change was made" in result


def test_confirmed_image_pull_failure_allows_healing(monkeypatch):
    """Heal only when the broken image and failure reason are confirmed."""

    responses = [
        healing_tools.BAD_IMAGE,
        "ImagePullBackOff",
        "deployment successfully updated",
    ]

    commands = []

    def mock_run(command):
        commands.append(command)
        return responses.pop(0)

    monkeypatch.setattr(
        healing_tools,
        "run_command",
        mock_run,
    )

    result = healing_tools.heal_image_pull_error()

    assert result.startswith("HEALING_SUCCESS")
    assert healing_tools.FIXED_IMAGE in result

    assert commands[2] == [
        "kubectl",
        "set",
        "image",
        f"deployment/{healing_tools.DEPLOYMENT}",
        f"{healing_tools.CONTAINER}={healing_tools.FIXED_IMAGE}",
        "-n",
        healing_tools.NAMESPACE,
    ]


def test_healing_command_failure_is_reported(monkeypatch):
    """Report an error when Kubernetes cannot update the deployment."""

    responses = [
        healing_tools.BAD_IMAGE,
        "ErrImagePull",
        "ERROR:\nForbidden",
    ]

    def mock_run(command):
        return responses.pop(0)

    monkeypatch.setattr(
        healing_tools,
        "run_command",
        mock_run,
    )

    result = healing_tools.heal_image_pull_error()

    assert result.startswith("HEALING_FAILED")
    assert "Forbidden" in result


def test_rollout_failure_is_reported(monkeypatch):
    """Do not report successful verification when rollout fails."""

    commands = []

    def mock_run(command):
        commands.append(command)
        return "ERROR:\nrollout exceeded its deadline"

    monkeypatch.setattr(
        healing_tools,
        "run_command",
        mock_run,
    )

    result = healing_tools.verify_deployment()

    assert result.startswith("VERIFICATION_FAILED")
    assert "rollout exceeded its deadline" in result

    # Verification should stop when the rollout fails.
    assert len(commands) == 1


def test_verification_success(monkeypatch):
    """Verify a healthy deployment and ready pod."""
    import json

    pod_data = {
        "items": [
            {
                "metadata": {"name": "agent-healing-demo-abc123"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [
                        {"name": "app", "ready": True}
                    ],
                },
            }
        ]
    }

    responses = [
        'deployment "agent-healing-demo" successfully rolled out',
        healing_tools.FIXED_IMAGE,
        json.dumps(pod_data),
    ]

    def mock_run(command):
        return responses.pop(0)

    monkeypatch.setattr(healing_tools, "run_command", mock_run)

    result = healing_tools.verify_deployment()

    assert result.startswith("VERIFICATION_SUCCESS")
    assert "Image: nginx:latest" in result
    assert "Ready pods: 1" in result


def test_verification_rejects_wrong_image(monkeypatch):
    """Verification must fail if the deployment uses the wrong image."""
    responses = [
        'deployment "agent-healing-demo" successfully rolled out',
        healing_tools.BAD_IMAGE,
    ]

    def mock_run(command):
        return responses.pop(0)

    monkeypatch.setattr(healing_tools, "run_command", mock_run)

    result = healing_tools.verify_deployment()

    assert result.startswith("VERIFICATION_FAILED")
    assert "Expected image" in result


def test_verification_rejects_unready_pod(monkeypatch):
    """Verification must fail when the pod is not ready."""
    import json

    pod_data = {
        "items": [
            {
                "metadata": {"name": "agent-healing-demo-abc123"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [
                        {"name": "app", "ready": False}
                    ],
                },
            }
        ]
    }

    responses = [
        'deployment "agent-healing-demo" successfully rolled out',
        healing_tools.FIXED_IMAGE,
        json.dumps(pod_data),
    ]

    def mock_run(command):
        return responses.pop(0)

    monkeypatch.setattr(healing_tools, "run_command", mock_run)

    result = healing_tools.verify_deployment()

    assert result.startswith("VERIFICATION_FAILED")
    assert "not Ready" in result
