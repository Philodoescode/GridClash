import csv
import sys
import os
import time
import random
import threading
import struct
from collections import deque

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

from src.client_headless import GridClient, MessageType, unpack_packet
from src.protocol import get_current_timestamp_ms, UNCLAIMED_ID
from src.constants import GRID_WIDTH, GRID_HEIGHT

class InstrumentedClient(GridClient):
    def __init__(self, client_id, server_address, log_dir, seed, action_interval_range):
        super().__init__(client_id, server_address)
        self.log_dir = log_dir
        self.rng = random.Random(seed)
        self.action_min, self.action_max = action_interval_range
        
        # Logging
        os.makedirs(log_dir, exist_ok=True)
        self.metrics_file = open(os.path.join(log_dir, f'client_{client_id}_metrics.csv'), 'w', newline='')
        self.metrics_writer = csv.writer(self.metrics_file)
        self.metrics_writer.writerow([
            'client_id', 'snapshot_id', 'seq_num', 
            'server_timestamp_ms', 'recv_time_ms', 
            'latency_ms', 'jitter_ms', 'perceived_position_error', 
            'cpu_percent', 'bandwidth_per_client_kbps'
        ])
        
        self.pos_file = open(os.path.join(log_dir, f'client_{client_id}_positions.csv'), 'w', newline='')
        self.pos_writer = csv.writer(self.pos_file)
        # broadcast_timestamp_ms is the unified timestamp from server broadcasts
        # This matches the server's position log for exact-match error calculation
        self.pos_writer.writerow(['broadcast_timestamp_ms', 'client_id', 'x', 'y'])
        
        self.last_recv_ts = 0
        self.last_server_ts = 0
        self.jitter = 0.0
        
        self.start_time = time.time()
        self.bytes_received = 0
        
        # AI State
        self.target_path = deque() # Queue of (dx, dy) moves
        self.initialized = False
        self.waiting_restart = False

    def handle_server_hello(self, data):
        super().handle_server_hello(data)
        self.initialized = True
        self.target_path.clear()
        print(f"[INSTRUMENTED CLIENT {self.client_id}] Initialized at ({self.pos_x}, {self.pos_y})")

    def handle_game_state_update(self, data):
        """
        Handle incoming game state snapshot from server.
        
        SYNCHRONIZED SAMPLING: Position is logged using the server's broadcast
        timestamp (server_ts) as the unified sync key. This ensures both server
        and client use the exact same timestamp, enabling trivial error calculation.
        """
        # Measure size before unpacking
        self.bytes_received += len(data)
        recv_ts = get_current_timestamp_ms()
        
        # Capture client's current predicted position BEFORE processing server update
        # This is what the client was displaying at the moment of receiving the snapshot
        client_pos_x = self.pos_x
        client_pos_y = self.pos_y
        
        # Call super to process state (updates self.grid_state, self.target_players, etc)
        super().handle_game_state_update(data)
        
        try:
            pkt, payload = unpack_packet(data)
            if pkt.msg_type != MessageType.SNAPSHOT:
                return

            # server_ts is the broadcast timestamp - the unified sync key
            server_ts = pkt.server_timestamp
            latency = recv_ts - server_ts
            
            # Jitter calculation
            if self.last_recv_ts > 0:
                delta_recv = recv_ts - self.last_recv_ts
                delta_server = server_ts - self.last_server_ts
                inst_jitter = abs(delta_recv - delta_server)
                self.jitter = 0.875 * self.jitter + 0.125 * inst_jitter
            
            self.last_recv_ts = recv_ts
            self.last_server_ts = server_ts
            
            # SYNCHRONIZED POSITION LOGGING (20Hz, same rate as server broadcasts)
            # Use server_ts (broadcast timestamp) as the unified timestamp
            # This enables exact-match position error calculation with server logs
            self.pos_writer.writerow([server_ts, self.client_id, client_pos_x, client_pos_y])
            self.pos_file.flush()
            
            # We log the packet size in the 'bandwidth' column (to be aggregated later)
            self.metrics_writer.writerow([
                self.client_id, pkt.snapshot_id, pkt.seq_num,
                server_ts, recv_ts,
                latency, self.jitter,
                0, # error calc later
                0, # cpu calc later
                len(data)
            ])
            self.metrics_file.flush()
            
        except Exception:
            pass

    def bfs_find_nearest_unclaimed(self):
        """
        Uses BFS to find the shortest path to an unclaimed cell.
        Returns a deque of (dx, dy) moves relative to current position.
        """
        start_x, start_y = self.pos_x, self.pos_y
        
        # Directions: Up, Down, Left, Right
        # Note: Grid coordinates are usually (row, col) = (y, x). 
        # API expects request(row, col) => request(y, x).
        # Directions as (dx, dy)
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)] # Up, Down, Left, Right 
        
        queue = deque([(start_x, start_y)])
        visited = set([(start_x, start_y)])
        
        # Parent map to reconstruct path: (child_x, child_y) -> (parent_x, parent_y, direction)
        parent_map = {} 
        
        found_target = None
        
        while queue:
            curr_x, curr_y = queue.popleft()
            
            # Check if this cell is a valid target (Unclaimed)
            idx = curr_y * GRID_WIDTH + curr_x
            if self.grid_state[idx] == UNCLAIMED_ID:
                found_target = (curr_x, curr_y)
                break
            
            for dx, dy in directions:
                nx, ny = curr_x + dx, curr_y + dy
                
                # Check bounds
                if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                    continue
                
                if (nx, ny) in visited:
                    continue
                
                # Check passability: Can we move through this cell?
                # User rule: "treat already-claimed cells as passable" 
                # But physically we can only move through our own cells or unclaimed cells.
                # If we try to move into another player's cell, the server (and client check) will reject it.
                # So we must treat OTHER PLAYERS' cells as obstacles.
                n_idx = ny * GRID_WIDTH + nx
                owner = self.grid_state[n_idx]
                
                # Passable if Untaken OR Owned by Me
                if owner == UNCLAIMED_ID or owner == self.client_id:
                    visited.add((nx, ny))
                    parent_map[(nx, ny)] = (curr_x, curr_y, (dx, dy))
                    queue.append((nx, ny))
        
        if found_target:
            # Reconstruct path
            path = deque()
            curr = found_target
            while curr != (start_x, start_y):
                prev_x, prev_y, move = parent_map[curr]
                path.appendleft(move)
                curr = (prev_x, prev_y)
            return path
        
        return None

    def run_automated(self):
        # Headless setup
        self.send_hello()
        self.socket.setblocking(False)
        
        last_action_time = time.time()
        # Initial wait
        time.sleep(0.5)
        
        # print(f"[INSTRUMENTED CLIENT {self.client_id}] Started.")
        
        running = True
        try:
            while running:
                now = time.time()
                
                # Heartbeat
                if (now - self.last_heartbeat_time) >= self.heartbeat_interval:
                    self.send_heartbeat()
                    self.last_heartbeat_time = now
                
                # Network Recv
                state_updated = False
                try:
                    while True:
                        data, addr = self.socket.recvfrom(65535) 
                        if addr == self.server_address:
                            pkt, payload = unpack_packet(data)
                            if pkt.msg_type == MessageType.SERVER_INIT_RESPONSE:
                                self.handle_server_hello(data)
                            elif pkt.msg_type == MessageType.SNAPSHOT:
                                self.handle_game_state_update(data)
                                state_updated = True
                            elif pkt.msg_type == MessageType.GAME_OVER:
                                self.handle_game_over(data)
                                # Don't stop running, logic below handles restart
                            elif pkt.msg_type == MessageType.ACK or pkt.msg_type == MessageType.NACK:
                                self.handle_ack_nack(pkt, payload)
                            elif pkt.msg_type == MessageType.SERVER_FULL:
                                self.handle_server_full(data)
                                running = False
                except BlockingIOError:
                    pass
                except Exception as e:
                    pass

                # Game Over / Restart Handling
                if self.game_over:
                    if not self.waiting_restart:
                        print(f"[CLIENT {self.client_id}] Game Over. Requesting New Game...")
                        self.request_new_game()
                        # Manually reset some flags to match restart logic
                        self.waiting_restart = True
                        self.initialized = False 
                    
                    # Wait for server response (SERVER_INIT_RESPONSE or reset via packet)
                    # When server restarts, we receive SERVER_INIT or just new state? 
                    # Usually SERVER_INIT_RESPONSE if we sent NEW_GAME and re-registered?
                    # Or maybe just grid clears?
                    # Client handle_server_hello resets game state.
                    time.sleep(0.1)
                    continue

                if self.waiting_restart and self.initialized:
                     # We got init response
                     self.waiting_restart = False
                     self.game_over = False

                if self.connected and self.initialized and not self.game_over:
                    # Pathfinding Logic
                    # 1. If no path, find one
                    if not self.target_path:
                        # Only run BFS if we have latest state to avoid spamming
                        # But we can run it if we are idle
                        path = self.bfs_find_nearest_unclaimed()
                        if path:
                            self.target_path = path
                        else:
                            # No targets found?
                            pass

                    # 2. Execute Move
                    # Rate limiting: 50-100ms
                    # Use self.action_min / action_max (which was 50-200 in main)
                    # Let's use a tighter constraint as requested: 50-100ms
                    if now - last_action_time >= (random.uniform(0.05, 0.1)):
                        if self.target_path:
                            dx, dy = self.target_path.popleft()
                            
                            # Verify if move is still valid (e.g. not walking into wall)
                            # Actually, just send the request. If invalid, server NACKs or client checks.
                            # But we should check if our 'predicted' position is consistent
                            target_x = self.pos_x + dx
                            target_y = self.pos_y + dy
                            
                            # Send move
                            self.send_acquire_request(target_y, target_x)
                            last_action_time = now
                            
                            # Note: self.pos_x/y updates immediately in send_acquire_request (Optimistic)
                            # If NACKed, it resets.
                            # If we get NACKed, our path might be invalid. 
                            # We should probably clear path on NACK (not implemented here but safe assumption)

                
                # Update Visuals (not used in headless)
                dt = 0.016 
                self.update_visuals(dt)
                
                # Position logging is now handled in handle_game_state_update()
                # at 20Hz synchronized with server broadcasts using server_timestamp
                
                time.sleep(0.001)

        except KeyboardInterrupt:
            pass
        finally:
            self.metrics_file.close()
            self.pos_file.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, default=255)
    parser.add_argument("--log-dir", type=str, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--host", default="127.0.0.1")
    exit_args = parser.parse_args()
    
    # Random ID generation if 255
    rng_seed = exit_args.seed
    if exit_args.id != 255:
        rng_seed += exit_args.id
        
    c = InstrumentedClient(exit_args.id, (exit_args.host, 12000), exit_args.log_dir, rng_seed, (50, 200))
    c.headless_mode = True 
    c.run_automated()
