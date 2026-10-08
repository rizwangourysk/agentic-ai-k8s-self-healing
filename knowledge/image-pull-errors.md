# Kubernetes Image Pull Errors

## ImagePullBackOff

ImagePullBackOff means Kubernetes cannot pull the container image successfully.

Common causes:

- Incorrect image name
- Incorrect image tag
- Image does not exist in the registry
- Registry authentication problem
- Network problem

## ErrImagePull

ErrImagePull means Kubernetes tried to pull the container image but the image pull failed.

Example:

nginx:this-image-does-not-exist

This usually means the image or tag does not exist.

## Investigation

Check the pod:

kubectl describe pod <pod-name> -n <namespace>

Check events:

kubectl get events -n <namespace> --sort-by=.lastTimestamp

Look for:

ErrImagePull

ImagePullBackOff

Failed to pull image

## Recovery

Identify the incorrect image.

Update the deployment with a valid image.

Example:

kubectl set image deployment/<deployment> app=nginx:latest -n <namespace>

Verify:

kubectl rollout status deployment/<deployment> -n <namespace>

Then:

kubectl get pods -n <namespace>
