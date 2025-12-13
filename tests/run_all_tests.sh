#!/bin/bash
# run_all_tests.sh
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RUNNER="$DIR/run_test_scenario.py"
REPORTER="$DIR/generate_suite_report.py"

echo "========================================"
echo "    GRIDCLASH NETWORK TEST SUITE"
echo "========================================"

# Function to run a scenario
run_test() {
    SCENARIO=$1
    echo ""
    echo ">>> Running Scenario: $SCENARIO"
    sudo python3 "$RUNNER" "$SCENARIO" --duration 60 --clients 4
}

# Run all scenarios
run_test "baseline"
run_test "loss_2"
run_test "loss_5"
run_test "delay_100ms"

echo ""
echo ">>> All Tests Complete. Generating Report..."
python3 "$REPORTER"

echo ""
echo "Done."
