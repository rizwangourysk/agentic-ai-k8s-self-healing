# Kubernetes Self-Healing

A Kubernetes self-healing agent follows these steps:

1. Detect the failure.
2. Collect Kubernetes evidence.
3. Diagnose the root cause.
4. Select an approved remediation.
5. Apply the remediation.
6. Verify recovery.
7. Report the result.

The agent should investigate before taking action.

For ImagePullBackOff:

Detect:
The pod shows ErrImagePull or ImagePullBackOff.

Investigate:
Use kubectl describe pod and Kubernetes events.

Diagnose:
Check whether the configured image or tag is invalid.

Heal:
Update the deployment with a valid image.

Verify:
Use kubectl rollout status and kubectl get pods.

Safety:
Only use approved healing actions.
Do not give the agent unrestricted shell access.
