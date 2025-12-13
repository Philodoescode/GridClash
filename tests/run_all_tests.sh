#!/bin/bash
# run_all_tests.sh
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$DIR/.." && pwd )"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python3"
RUNNER="$DIR/run_test_scenario.py"
REPORTER="$DIR/generate_suite_report.py"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at $VENV_PYTHON"
    echo "Please create the virtual environment first (e.g., using 'uv sync' or 'python -m venv .venv')"
    exit 1
fi

echo "========================================"
echo "    GRIDCLASH NETWORK TEST SUITE"
echo "========================================"

# Function to run a scenario
run_test() {
    SCENARIO=$1
    echo ""
    echo ">>> Running Scenario: $SCENARIO"
    sudo "$VENV_PYTHON" "$RUNNER" "$SCENARIO" --duration 60 --clients 4
}

# Run all scenarios
run_test "baseline"
run_test "loss_2"
run_test "loss_5"
run_test "delay_100ms"

echo ""
echo ">>> All Tests Complete. Generating Report..."
"$VENV_PYTHON" "$REPORTER"

echo ""
echo "Done."
