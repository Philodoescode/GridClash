# GridClash

<div align="center">


**GridClash is a lightweight, real-time multiplayer simulation system built with a custom UDP-based synchronization
protocol.
It enables efficient state updates between a central server and multiple connected clients while maintaining low latency
and minimal CPU load.**

</div>

## 🚀 Setup & Installation

### Prerequisites

- **Python**: 3.13 or higher
- **uv**: Fast Python package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Philodoescode/GridClash.git
   cd GridClash
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```
3. **Verify Installation**
   ```bash
   uv run main.py
   ```

### Development Setup (PyCharm)

Follow the official [PyCharm uv integration guide](https://www.jetbrains.com/help/pycharm/uv.html) to configure your
IDE.

### Using uv for Project Management

| Task                 | pip                                   | uv                          |
|----------------------|---------------------------------------|-----------------------------|
| Install dependencies | `pip install -r requirements.txt`     | `uv sync`                   |
| Add a package        | `pip install package_name`            | `uv add package_name`       |
| Add dev dependency   | `pip install --save-dev package_name` | `uv add --dev package_name` |
| Freeze dependencies  | `pip freeze > requirements.txt`       | `uv lock`                   |
| Run a script         | `python script.py`                    | `uv run script.py`          |

## 📝 Running Tests

### Network Test Suite (Linux/WSL Required)

The network test suite evaluates server performance under various network conditions using `tc` (traffic control) for network simulation.

> **Note**: These tests require Linux or WSL (Windows Subsystem for Linux) as they use `tc` and `tcpdump` which are Linux-specific tools.

#### Prerequisites

```bash
# Install required tools (Ubuntu/Debian)
sudo apt install iproute2 tcpdump
```

#### Running All Tests

```bash
# Navigate to project directory
cd ~/projects/gridclash

# Install dependencies
uv sync

# Run the full test suite (requires sudo for tc/tcpdump)
uv run bash tests/run_all_tests.sh
```

#### Running a Single Scenario

```bash
# Run a specific test scenario
uv run tests/run_test_scenario.py <scenario> --duration 60 --clients 4
```

Available scenarios:
| Scenario | Description |
|----------|-------------|
| `baseline` | Clean network, no impairment |
| `loss_2` | 2% packet loss |
| `loss_5` | 5% packet loss |
| `delay_100ms` | 100ms network delay |

#### Test Outputs

Results are saved in `tests/results/<timestamp>/`:

| File | Description |
|------|-------------|
| `server_positions.csv` | Server's authoritative player positions |
| `client_*_positions.csv` | Client's perceived positions |
| `client_*_metrics.csv` | Latency, jitter, and packet data |
| `detailed_metrics.csv` | Combined analysis with position error |
| `summary.json` | Aggregated statistics |
| `suite_report_latest.csv` | Cross-scenario comparison |

#### Sample Test Report

```
====================================================================================================
GRIDCLASH TEST SUITE REPORT
====================================================================================================
Scenario        | Lat(Avg)   | Jit(Avg)   | Err(Avg)   | Err(95%)   | CPU%   | Status
----------------------------------------------------------------------------------------------------
Baseline        | 4.02       | 2.10       | 0.0078     | 0.0000     | 4.1    | PASS
Loss 2%         | 4.00       | 1.95       | 0.0385     | 0.0000     | 4.0    | PASS
Loss 5%         | 6.04       | 4.10       | 0.2481     | 3.1623     | 3.1    | PASS
Delay 100ms     | 102.00     | 1.20       | 0.5020     | 2.0000     | 2.9    | PASS
----------------------------------------------------------------------------------------------------
```

#### Troubleshooting: Windows Line Endings

If you encounter errors like `$'\r': command not found` when running shell scripts on Linux/WSL, the files have Windows line endings (CRLF). Fix with:

```bash
# Fix line endings for all test files
sed -i 's/\r$//' tests/*.sh tests/*.py src/*.py
```


## 🛠️ Design Mechanisms

### Protocol Design

#### Header Structure (28 bytes)

| Field        | Type   | Size (bytes) | Description                       |
|--------------|--------|--------------|-----------------------------------|
| protocol_id  | 4s     | 4            | Identifier `"GCUP"`               |
| version      | uint8  | 1            | Protocol version                  |
| msg_type     | uint8  | 1            | Defines packet category           |
| snapshot_id  | uint32 | 4            | Update sequence id                |
| seq_num      | uint32 | 4            | Client or server sequence counter |
| server_ts_ms | uint64 | 8            | Millisecond-precision timestamp   |
| payload_len  | uint16 | 2            | Length of payload in bytes        |
| checksum     | uint32 | 4            | CRC32 integrity check             |

#### Message Types

| Type                   | Direction       | Purpose                       |
|------------------------|-----------------|-------------------------------|
| `SNAPSHOT`             | Server → Client | Periodic game state broadcast |
| `HEARTBEAT`            | Client → Server | Keep-alive signal             |
| `CLIENT_INIT`          | Client → Server | Registration request          |
| `SERVER_INIT_RESPONSE` | Server → Client | Registration confirmation     |

## 📁 Project Structure

```
src/
  ├── __init__.py
  ├── protocol.py         # Defines packet format & checksum system
  ├── server.py           # Runs UDP broadcast loop
  ├── client.py           # GUI client with pygame
  ├── client_headless.py  # Headless client for automated testing
  ├── constants.py        # Game configuration constants
tests/
  ├── run_all_tests.sh          # Runs full test suite
  ├── run_test_scenario.py      # Single scenario test runner
  ├── instrumented_server.py    # Server with position logging
  ├── instrumented_client.py    # Client with synchronized logging
  ├── generate_suite_report.py  # Aggregates results across scenarios
  └── results/                  # Test output directory
main.py                # Simple entry point
pyproject.toml         # Project metadata & dependencies
README.md              # Documentation
```

## 👥 Authors

- Yousif Abdulhafiz - [@ysif9](https://github.com/ysif9)
- Philopater Guirgis - [@Philodoescode](https://github.com/Philodoescode)
- Hams Hassan - [@Hams2305](https://github.com/Hams2305)
- Ahmed Lotfy - [@dark-hunter0](https://github.com/dark-hunter0)
- Noha Elsayed - [@Nohaelsayedd](https://github.com/Nohaelsayedd)
- Adham Kandil - [@Kandil122](https://github.com/Kandil122)

## 📞 Support

For issues, questions, or contributions:

- Open an issue on GitHub
- Contact the development team
- Check existing documentation

