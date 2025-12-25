"""
Play GridClash against bot players.

This script starts the server, your UI client, and then spawns bot players
that compete against you. Adjust the difficulty by changing how fast the bots
claim cells.

Usage:
    uv run play_vs_bots.py                          # Default: 3 bots, medium difficulty
    uv run play_vs_bots.py --bots 2                 # 2 bots
    uv run play_vs_bots.py --difficulty easy        # Easy bots (slow)
    uv run play_vs_bots.py --difficulty hard        # Hard bots (fast)
    uv run play_vs_bots.py --bots 3 --difficulty medium
"""

import argparse
import os
import subprocess
import sys
import time
import signal
import atexit

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------
# Difficulty Settings
# ---------------------------
# Difficulty controls how fast bots claim cells (move interval in milliseconds)
DIFFICULTY_SETTINGS = {
    'easy': (300, 500),      # Slow: 300-500ms between moves
    'medium': (100, 200),    # Medium: 100-200ms between moves
    'hard': (50, 100),       # Fast: 50-100ms between moves
    'extreme': (20, 50),     # Very fast: 20-50ms between moves
}

# Store all spawned processes for cleanup
processes = []


def cleanup():
    """Terminate all spawned processes on exit."""
    print("\n[CLEANUP] Terminating all processes...")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    # Wait a bit then force kill if needed
    time.sleep(0.5)
    for p in processes:
        try:
            p.kill()
        except Exception:
            pass
    print("[CLEANUP] Done.")


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    cleanup()
    sys.exit(0)


def get_uv_run_cmd():
    """Get the base command for running Python scripts via uv."""
    return ['uv', 'run']


def start_server(port=12000):
    """Start the GridClash server."""
    server_script = os.path.join(PROJECT_ROOT, 'src', 'server.py')
    
    print(f"[START] Starting server on port {port}...")
    
    cmd = get_uv_run_cmd() + [server_script]
    proc = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    processes.append(proc)
    return proc


def start_ui_client(host='127.0.0.1', port=12000):
    """Start the UI client for the human player."""
    client_script = os.path.join(PROJECT_ROOT, 'src', 'client.py')
    
    print(f"[START] Starting YOUR client...")
    
    cmd = get_uv_run_cmd() + [client_script, '--host', host, '--port', str(port)]
    proc = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    processes.append(proc)
    return proc


def start_bot_client(bot_id, host='127.0.0.1', port=12000, difficulty='medium', seed=None):
    """
    Start a bot client using the instrumented client.
    
    The bot uses the InstrumentedClient which has BFS pathfinding AI to compete.
    """
    bot_script = os.path.join(PROJECT_ROOT, 'tests', 'instrumented_client.py')
    
    # Create a temp log dir for bots
    log_dir = os.path.join(PROJECT_ROOT, 'logs', 'bot_session')
    os.makedirs(log_dir, exist_ok=True)
    
    # Use seed for reproducibility (different seed per bot)
    actual_seed = seed if seed is not None else (42 + bot_id)
    
    print(f"[START] Starting Bot {bot_id} (difficulty: {difficulty})...")
    
    cmd = get_uv_run_cmd() + [
        bot_script,
        '--id', str(bot_id),
        '--host', host,
        '--log-dir', log_dir,
        '--seed', str(actual_seed)
    ]
    
    proc = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    processes.append(proc)
    return proc


def patch_bot_move_speed(difficulty):
    """
    Dynamically patch the bot move speed based on difficulty.
    We do this by modifying the action interval in the bot's run loop.
    
    Since we can't easily inject this at runtime, we create a wrapper script.
    """
    # The instrumented_client has hardcoded move timing at line 271:
    # if now - last_action_time >= (random.uniform(0.05, 0.1)):
    # We'll create a modified version that respects our difficulty setting
    
    min_interval, max_interval = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS['medium'])
    return min_interval / 1000.0, max_interval / 1000.0  # Convert to seconds


def create_bot_wrapper_script(difficulty):
    """
    Create a temporary bot script that respects the difficulty setting.
    This wraps the instrumented client with our custom move interval.
    """
    min_interval, max_interval = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS['medium'])
    
    wrapper_script = os.path.join(PROJECT_ROOT, 'logs', 'bot_wrapper.py')
    os.makedirs(os.path.dirname(wrapper_script), exist_ok=True)
    
    wrapper_code = f'''"""Auto-generated bot wrapper with difficulty: {difficulty}"""
import csv
import sys
import os
import time
import random
import struct
from collections import deque

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

from src.client_headless import GridClient, MessageType, unpack_packet
from src.protocol import get_current_timestamp_ms, UNCLAIMED_ID
from src.constants import GRID_WIDTH, GRID_HEIGHT

# Difficulty settings (in seconds)
ACTION_MIN = {min_interval / 1000.0}
ACTION_MAX = {max_interval / 1000.0}

class BotClient(GridClient):
    def __init__(self, client_id, server_address, seed):
        super().__init__(client_id, server_address)
        self.rng = random.Random(seed)
        self.target_path = deque()
        self.initialized = False
        self.waiting_restart = False
    
    def handle_server_hello(self, data):
        super().handle_server_hello(data)
        self.initialized = True
        self.target_path.clear()
        print(f"[BOT {{self.client_id}}] Initialized at ({{self.pos_x}}, {{self.pos_y}})")
    
    def handle_game_state_update(self, data):
        super().handle_game_state_update(data)
    
    def bfs_find_nearest_unclaimed(self):
        start_x, start_y = self.pos_x, self.pos_y
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        queue = deque([(start_x, start_y)])
        visited = set([(start_x, start_y)])
        parent_map = {{}}
        found_target = None
        
        while queue:
            curr_x, curr_y = queue.popleft()
            idx = curr_y * GRID_WIDTH + curr_x
            if self.grid_state[idx] == UNCLAIMED_ID:
                found_target = (curr_x, curr_y)
                break
            
            for dx, dy in directions:
                nx, ny = curr_x + dx, curr_y + dy
                if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                    continue
                if (nx, ny) in visited:
                    continue
                n_idx = ny * GRID_WIDTH + nx
                owner = self.grid_state[n_idx]
                if owner == UNCLAIMED_ID or owner == self.client_id:
                    visited.add((nx, ny))
                    parent_map[(nx, ny)] = (curr_x, curr_y, (dx, dy))
                    queue.append((nx, ny))
        
        if found_target:
            path = deque()
            curr = found_target
            while curr != (start_x, start_y):
                prev_x, prev_y, move = parent_map[curr]
                path.appendleft(move)
                curr = (prev_x, prev_y)
            return path
        return None
    
    def run_automated(self):
        self.send_hello()
        self.socket.setblocking(False)
        last_action_time = time.time()
        time.sleep(0.5)
        running = True
        
        try:
            while running:
                now = time.time()
                
                # Heartbeat
                if (now - self.last_heartbeat_time) >= self.heartbeat_interval:
                    self.send_heartbeat()
                    self.last_heartbeat_time = now
                
                # Network receive
                try:
                    while True:
                        data, addr = self.socket.recvfrom(65535)
                        if addr == self.server_address:
                            pkt, payload = unpack_packet(data)
                            if pkt.msg_type == MessageType.SERVER_INIT_RESPONSE:
                                self.handle_server_hello(data)
                            elif pkt.msg_type == MessageType.SNAPSHOT:
                                self.handle_game_state_update(data)
                            elif pkt.msg_type == MessageType.GAME_OVER:
                                self.handle_game_over(data)
                            elif pkt.msg_type == MessageType.ACK or pkt.msg_type == MessageType.NACK:
                                self.handle_ack_nack(pkt, payload)
                            elif pkt.msg_type == MessageType.SERVER_FULL:
                                self.handle_server_full(data)
                                running = False
                except BlockingIOError:
                    pass
                except Exception:
                    pass
                
                # Game over handling - bots wait for human to start new game
                if self.game_over:
                    if not self.waiting_restart:
                        print(f"[BOT {{self.client_id}}] Game Over. Waiting for new game...")
                        self.waiting_restart = True
                        self.initialized = False
                    time.sleep(0.1)
                    continue
                
                if self.waiting_restart and self.initialized:
                    self.waiting_restart = False
                    self.game_over = False
                
                if self.connected and self.initialized and not self.game_over:
                    # Pathfinding
                    if not self.target_path:
                        path = self.bfs_find_nearest_unclaimed()
                        if path:
                            self.target_path = path
                    
                    # Execute move with difficulty-controlled timing
                    if now - last_action_time >= random.uniform(ACTION_MIN, ACTION_MAX):
                        if self.target_path:
                            dx, dy = self.target_path.popleft()
                            target_x = self.pos_x + dx
                            target_y = self.pos_y + dy
                            self.send_acquire_request(target_y, target_x)
                            last_action_time = now
                
                self.update_visuals(0.016)
                time.sleep(0.001)
        
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, default=255)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)
    args = parser.parse_args()
    
    seed = args.seed
    if args.id != 255:
        seed += args.id
    
    c = BotClient(args.id, (args.host, args.port), seed)
    c.headless_mode = True
    c.run_automated()
'''
    
    with open(wrapper_script, 'w') as f:
        f.write(wrapper_code)
    
    return wrapper_script


def start_bot_with_difficulty(bot_id, difficulty, host='127.0.0.1', port=12000, seed=None):
    """Start a bot with the specified difficulty."""
    # Create the wrapper script with the difficulty baked in
    wrapper_script = create_bot_wrapper_script(difficulty)
    
    actual_seed = seed if seed is not None else (42 + bot_id)
    
    min_ms, max_ms = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS['medium'])
    print(f"[START] Starting Bot {bot_id + 1} (difficulty: {difficulty}, {min_ms}-{max_ms}ms moves)...")
    
    cmd = get_uv_run_cmd() + [
        wrapper_script,
        '--id', str(bot_id),
        '--host', host,
        '--port', str(port),
        '--seed', str(actual_seed)
    ]
    
    proc = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    processes.append(proc)
    return proc


def main():
    parser = argparse.ArgumentParser(
        description="Play GridClash against bot players",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Difficulty levels:
  easy     - Bots move slowly (300-500ms between moves)
  medium   - Bots move at moderate speed (100-200ms) [default]
  hard     - Bots move quickly (50-100ms)
  extreme  - Bots move very fast (20-50ms)
        """
    )
    parser.add_argument(
        '--bots', '-b',
        type=int,
        default=3,
        choices=[1, 2, 3],
        help='Number of bot players (1-3, default: 3)'
    )
    parser.add_argument(
        '--difficulty', '-d',
        type=str,
        default='medium',
        choices=['easy', 'medium', 'hard', 'extreme'],
        help='Bot difficulty level (default: medium)'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=12000,
        help='Server port (default: 12000)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay before starting bots (default: 2 seconds)'
    )
    
    args = parser.parse_args()
    
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("   GRIDCLASH - Play vs Bots")
    print("=" * 60)
    print(f"   Bots: {args.bots}")
    print(f"   Difficulty: {args.difficulty}")
    min_ms, max_ms = DIFFICULTY_SETTINGS[args.difficulty]
    print(f"   Bot move speed: {min_ms}-{max_ms}ms")
    print("=" * 60)
    print()
    
    # Step 1: Start the server
    server_proc = start_server(args.port)
    time.sleep(2)  # Give server time to start
    
    # Check if server started successfully (give it a moment to bind the port)
    if server_proc.poll() is not None:
        print("[ERROR] Server failed to start! Port may be in use.")
        print(f"        Try: netstat -ano | findstr :{args.port}")
        cleanup()
        sys.exit(1)
    
    # Step 2: Start YOUR UI client
    ui_client_proc = start_ui_client(port=args.port)
    
    # Step 3: Wait, then start bots
    print(f"\n[INFO] Waiting {args.delay} seconds before starting bots...")
    time.sleep(args.delay)
    
    # Start bot clients (they get IDs 1, 2, 3 since you get ID 0)
    bot_procs = []
    for i in range(args.bots):
        bot_id = i + 1  # Your client gets ID 0, bots get 1, 2, 3
        bot_proc = start_bot_with_difficulty(
            bot_id=bot_id,
            difficulty=args.difficulty,
            port=args.port 
        )
        bot_procs.append(bot_proc)
        time.sleep(0.3)  # Small delay between bot starts
    
    print()
    print("=" * 60)
    print("   Game is running! Close the game window to exit.")
    print("   Press Ctrl+C to stop all processes.")
    print("=" * 60)
    
    # Wait for the UI client to exit (blocking)
    try:
        ui_client_proc.wait()
    except KeyboardInterrupt:
        pass
    
    # Cleanup
    cleanup()
    print("\n[INFO] Game session ended.")


if __name__ == "__main__":
    main()
