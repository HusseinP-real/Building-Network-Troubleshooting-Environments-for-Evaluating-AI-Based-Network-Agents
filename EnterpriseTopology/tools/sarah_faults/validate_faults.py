import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lab import execute

FAULT_FILE = Path(__file__).with_name("fault_cases.json")
RESULT_DIR = Path(__file__).with_name("results")
RESULT_DIR.mkdir(exist_ok=True)


def interface_state(device, interface):
    success, output = execute(
        device,
        f"ip link show dev {interface}"
    )

    if not success:
        return None

    if "state UP" in output:
        return "UP"

    if "state DOWN" in output:
        return "DOWN"

    return "UNKNOWN"


def run_fault(fault):
    fault_id = fault["id"]
    device = fault["device"]
    interface = fault["interface"]

    print(f"\nTesting {fault_id}: {device} {interface}")

    result = {
        "fault_id": fault_id,
        "device": device,
        "interface": interface,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "baseline": False,
        "injection": False,
        "recovery": False,
        "status": "FAIL"
    }

    result["baseline"] = (
        interface_state(device, interface) == "UP"
    )

    if not result["baseline"]:
        print("FAIL: Interface is not UP before injection")
        return result

    print("PASS: Baseline")

    try:
        success, output = execute(device, fault["inject"])

        if not success:
            print(f"FAIL: Injection command: {output}")
        else:
            time.sleep(2)

            result["injection"] = (
                interface_state(device, interface) == "DOWN"
            )

            if result["injection"]:
                print("PASS: Fault injected")
            else:
                print("FAIL: Interface did not go DOWN")

    finally:
        print("Recovering interface...")

        success, output = execute(device, fault["repair"])

        if not success:
            print(f"WARNING: Recovery command failed: {output}")

        time.sleep(5)

        result["recovery"] = (
            interface_state(device, interface) == "UP"
        )

        if result["recovery"]:
            print("PASS: Interface recovered")
        else:
            print("FAIL: Interface recovery")

    if (
        result["baseline"]
        and result["injection"]
        and result["recovery"]
    ):
        result["status"] = "PASS"

    return result


def main():
    faults = json.loads(FAULT_FILE.read_text())

    # Initially validate only the first fault
    faults = faults[5:10]

    results = []

    for fault in faults:
        try:
            result = run_fault(fault)
        except Exception as exc:
            print(f"ERROR: {exc}")
            print("Stopping. Check the interface state manually.")
            break

        results.append(result)

        if result["baseline"] and not result["recovery"]:
            print("Stopping: Recovery failed")
            break

    output_file = RESULT_DIR / "validation_results.json"

    output_file.write_text(
        json.dumps(results, indent=2)
    )

    print(f"\nResults saved to {output_file}")

    passed = sum(
        result["status"] == "PASS"
        for result in results
    )

    print(f"{passed}/{len(results)} fault tests passed")


if __name__ == "__main__":
    main()
