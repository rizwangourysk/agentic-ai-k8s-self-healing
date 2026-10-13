from src.tools.healing_tools import (
    heal_image_pull_error,
    verify_deployment,
)


print("========== STARTING SELF-HEALING TEST ==========")

result = heal_image_pull_error()

print(result)


if result.startswith("HEALING_SUCCESS"):

    print()
    print("========== VERIFYING DEPLOYMENT ==========")

    verification = verify_deployment()

    print(verification)

else:

    print()
    print("========== VERIFICATION SKIPPED ==========")
    print("Healing was not performed because safety checks blocked it.")
