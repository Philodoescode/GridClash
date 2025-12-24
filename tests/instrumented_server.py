import csv
import os
import sys
import time

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

from src.server import GridServer
from src.protocol import get_current_timestamp_ms

class InstrumentedServer(GridServer):
    def __init__(self, port, grid_size, log_dir):
        super().__init__(port, grid_size)
        self.log_dir = log_dir
        
        # Ensure log dir exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Server Position Log - uses broadcast_timestamp as the sync key
        self.pos_log_path = os.path.join(log_dir, 'server_positions.csv')
        self.pos_log_file = open(self.pos_log_path, 'w', newline='')
        self.pos_writer = csv.writer(self.pos_log_file)
        # broadcast_timestamp is the unified timestamp for both server and client logging
        self.pos_writer.writerow(['broadcast_timestamp_ms', 'client_id', 'x', 'y'])
        
        # CPU Log (if we want self-reporting, but psutil external monitor is better)
        
        print(f"[INSTRUMENTED SERVER] Logging to {self.log_dir}")

    def state_broadcast(self):
        """
        Log positions and broadcast state.
        The broadcast_timestamp is used as the unified sync key for both
        server and client position logs, enabling exact-match error calculation.
        """
        # Get the broadcast timestamp - this will be sent to clients and used
        # as the unified sampling timestamp for both server and client logs
        broadcast_ts = get_current_timestamp_ms()
        
        # Log server's authoritative positions with the broadcast timestamp
        for client_addr, client_data in self.clients.items():
            pid = client_data['player_id']
            # pos is (x, y) = (col, row)
            pos = client_data.get('pos', (0,0))
            self.pos_writer.writerow([broadcast_ts, pid, pos[0], pos[1]])
        
        self.pos_log_file.flush()
        
        # Call parent's state_broadcast which will use the same timestamp
        # (it calls get_current_timestamp_ms internally, which will be very close)
        super().state_broadcast()

    def run(self):
        try:
            super().run()
        finally:
            self.pos_log_file.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--log-dir", type=str, required=True)
    args = parser.parse_args()
    
    server = InstrumentedServer(args.port, 20, args.log_dir)
    server.run()
