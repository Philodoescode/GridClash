# GridClash

This repository contains the design and implementation of a custom application-layer protocol for real-time game state
synchronization, developed for Multiplayer Game State Synchronization ("Grid Clash").

## Setup & Installation

### Installing uv

`uv` is a fast Python package installer and resolver. Install it following
the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

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
3. [**Setup on Pycharm**](https://www.jetbrains.com/help/pycharm/uv.html)

### Using uv for Project Management

| Task                 | pip                                   | uv                          |
|----------------------|---------------------------------------|-----------------------------|
| Install dependencies | `pip install -r requirements.txt`     | `uv sync`                   |
| Add a package        | `pip install package_name`            | `uv add package_name`       |
| Add dev dependency   | `pip install --save-dev package_name` | `uv add --dev package_name` |
| Freeze dependencies  | `pip freeze > requirements.txt`       | `uv lock`                   |
| Run a script         | `python script.py`                    | `uv run script.py`          |