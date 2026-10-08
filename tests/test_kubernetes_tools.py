from src.tools.kubernetes_tools import (
    get_pods,
    describe_pod,
    get_logs,
    get_events
)

print("========== PODS ==========")
print(get_pods())

print("========== BROKEN-APP DETAILS ==========")
print(describe_pod("broken-app"))

print("========== BROKEN-APP LOGS ==========")
print(get_logs("broken-app"))

print("========== KUBERNETES EVENTS ==========")
print(get_events())
