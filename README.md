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

### Baseline Performance Test

The baseline test suite evaluates server performance under concurrent client load:

```bash
uv run tests/run_baseline.py
```

#### What the Test Does

- **Starts 1 server** listening on port 12000
- **Spawns 4 concurrent clients** that connect and receive game state updates
- **Runs for 30 seconds** collecting metrics
- **Monitors CPU usage** at 0.5-second intervals
- **Generates reports** in the `logs/` directory

#### Test Outputs

Generated files in `logs/`:

- `server.log` — Server output and debug messages
- `client_*.log` — Per-client connection logs and latency data
- `server_cpu_usage.csv` — Raw CPU utilization time series
- `final_summary_report.txt` — Consolidated metrics summary

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
  ├── protocol.py      # Defines packet format & checksum system
  ├── server.py        # Runs UDP broadcast loop
  ├── client.py        # Connects to server, measures latency
tests/
  └── run_baseline.py  # CPU & latency benchmark runner
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

