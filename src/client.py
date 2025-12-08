"""Client for GridClash game."""
import argparse
import os
import socket
import struct
import sys
import time

# Pygame Import (Phase 1)
import pygame

# import from parent directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.protocol import unpack_packet, get_current_timestamp_ms, pack_packet, MessageType
from src.server import MAX_PACKET_SIZE

# --- Visualization Constants (Phase 1) ---
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
GRID_SIZE = 20  # 20x20 Grid
CELL_SIZE = SCREEN_WIDTH // GRID_SIZE

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRID_COLOR = (200, 200, 200)

PLAYER_COLORS = {
    0: (255, 0, 0),      # Red
    1: (0, 0, 255),      # Blue
    2: (0, 255, 0),      # Green
    3: (255, 255, 0),    # Yellow
    'default': (100, 100, 100) # Gray for unknown IDs
}

class GridClient:
    """
    GridClient class for managing the client-side of the game.
    """

    def __init__(self, client_id=0, server_address=('127.0.0.1', 12000)):
        """Initialize client."""
        self.client_id = client_id
        self.server_address = server_address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.socket.bind(('127.0.0.1', 12001)) # bind to a specific port for testing
        self.last_heartbeat_time = time.time()
        self.heartbeat_interval = 1.0
        self.packet_count = 0
        self.latencies = []

        # State Management (Phase 2)
        self.target_players = {}   # {player_id: (target_x, target_y)} -> Authoritative from server
        self.visual_players = {}   # {player_id: (curr_x, curr_y)}     -> Smoothed for rendering

        # Snapshot/sequence tracking to detect stale/duplicate packets
        self.last_snapshot_id = -1
        self.last_seq_num = -1

        # Graphics context
        self.screen = None
        self.clock = None

    def send_hello(self):
        """Send hello message to server."""
        payload = struct.pack('!B', self.client_id)
        packet = pack_packet(MessageType.CLIENT_INIT, 0, 0, get_current_timestamp_ms(), payload)
        self.socket.sendto(packet, self.server_address)
        print(f"[CLIENT {self.client_id}] Sent HELLO")

    def send_heartbeat(self):
        """Send heartbeat to server."""
        payload = struct.pack('!B', self.client_id)
        packet = pack_packet(MessageType.HEARTBEAT, 0, 0, get_current_timestamp_ms(), payload)
        self.socket.sendto(packet, self.server_address)
        # print(f"[CLIENT {self.client_id}] Sent HEARTBEAT")

    def handle_server_hello(self, data):
        """Process SERVER_HELLO response."""
        try:
            pkt, payload = unpack_packet(data)
            if pkt.msg_type == MessageType.SERVER_INIT_RESPONSE and len(payload) >= 1:
                assigned_id = struct.unpack('!B', payload[:1])[0]
                print(f"[CLIENT {self.client_id}] Server assigned ID: {assigned_id}")
                self.client_id = assigned_id

                # Update window title if graphics are initialized
                if self.screen:
                    pygame.display.set_caption(f"GridClash - Player {self.client_id}")
        except ValueError as e:
            print(f"[ERROR] Invalid SERVER_HELLO: {e}")

    def handle_game_state_update(self, data):
        """Process game state update (snapshots)."""
        recv_ts_ms = get_current_timestamp_ms()  # used for latency calculation

        try:
            packet, payload = unpack_packet(data)

            # Only process snapshots
            if packet.msg_type != MessageType.SNAPSHOT:
                return

            # Stale/duplicate checks:
            # - If snapshot_id < last_snapshot_id => older snapshot
            # - If same snapshot_id but seq_num <= last_seq_num => duplicate/old
            if packet.snapshot_id < self.last_snapshot_id:
                return
            if packet.snapshot_id == self.last_snapshot_id and packet.seq_num <= self.last_seq_num:
                return

            # Update last seen ids
            self.last_snapshot_id = packet.snapshot_id
            self.last_seq_num = packet.seq_num

            # Bookkeeping
            self.packet_count += 1
            latency = recv_ts_ms - packet.server_timestamp
            self.latencies.append(latency)

            # Payload Parsing
            # Expected payload structure:
            #   num_players: 1 byte (!B)
            #   then for each player: id (!B), x (!i), y (!i), dx (!i), dy (!i) => 17 bytes per player
            if payload and len(payload) >= 1:
                num_players = payload[0]
                offset = 1
                BYTES_PER_PLAYER = 17
                for _ in range(num_players):
                    if offset + BYTES_PER_PLAYER <= len(payload):
                        p_id, pos_x, pos_y, dx, dy = struct.unpack('!Biiii', payload[offset:offset + BYTES_PER_PLAYER])
                        
                        # --- Redundancy / Gap Filling ---
                        # If we missed exactly one packet (seq_num diff is 2), we can reconstruct the missing state:
                        # Missing pos = Current pos - Delta
                        if self.last_seq_num != -1 and packet.seq_num == self.last_seq_num + 2:
                            missing_x = pos_x - dx
                            missing_y = pos_y - dy
                            # For now, we just log that we recovered it. 
                            # In a full interpolation system, we would insert this into the state buffer.
                            print(f"[REDUNDANCY] Recovered missing state for P{p_id}: ({missing_x}, {missing_y})")

                        # update authoritative state (target)
                        self.target_players[p_id] = (pos_x, pos_y)
                        
                        # If this is the first time seeing this player, snap visual to target immediately
                        if p_id not in self.visual_players:
                            self.visual_players[p_id] = (float(pos_x), float(pos_y))
                        offset += BYTES_PER_PLAYER
                    else:
                        # malformed / truncated payload for remaining players
                        break

            # Periodic logging
            if self.packet_count % 60 == 0 and self.latencies:
                avg = sum(self.latencies) / len(self.latencies)
                print(f"[NET] Packets: {self.packet_count}, Avg Latency: {avg:.2f} ms")

        except Exception as e:
            print(f"Error unpacking packet: {e}")

    def update_visuals(self, dt):
        """
        Interpolate visual positions towards target positions.
        dt: Time delta in seconds since last frame.
        """
        # Smoothing factor: Higher = snappier, Lower = smoother/laggier
        # Using a frame-rate independent decay formula or simple lerp factor
        # SIMPLE LERP FACTOR adjusted for dt:
        # A common simple approach: factor = 1 - pow(decay, dt)
        # Let's use a simple constant speed or factor for now.
        
        SMOOTHING_SPEED = 10.0 # units per second? No, simpler to use t-value interpolation
        
        # t = 1 - pow(0.01, dt) # Moves 99% of the way in 1 second
        # Let's try a distinct factor:
        lerp_factor = 10.0 * dt
        if lerp_factor > 1.0:
            lerp_factor = 1.0

        for p_id, target_pos in self.target_players.items():
            tx, ty = target_pos
            
            if p_id not in self.visual_players:
                self.visual_players[p_id] = (float(tx), float(ty))
                continue

            vx, vy = self.visual_players[p_id]
            
            # LERP
            new_vx = vx + (tx - vx) * lerp_factor
            new_vy = vy + (ty - vy) * lerp_factor
            
            self.visual_players[p_id] = (new_vx, new_vy)


    def init_graphics(self):
        """Initialize Pygame graphics (Phase 3)."""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"GridClash - Player {self.client_id}")
        self.clock = pygame.time.Clock()

    def draw_game(self):
        """Render the game state (Phase 3)."""
        if not self.screen:
            return

        # 1. Background
        self.screen.fill(WHITE)

        # 2. Grid Lines
        for x in range(0, SCREEN_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))

        # 3. Players
        for p_id, (x, y) in self.visual_players.items():
            color = PLAYER_COLORS.get(p_id, PLAYER_COLORS['default'])

            # Note: Server currently sends raw pixels (10, 20, 30...). 
            # We draw a circle at these exact coordinates.
            pygame.draw.circle(self.screen, color, (x, y), 10)

            # Optional: Highlight self
            if p_id == self.client_id:
                pygame.draw.circle(self.screen, BLACK, (x, y), 12, 2)

        # 4. Display Flip
        pygame.display.flip()

    def run(self, duration_sec=30):
        """Main client loop (Phase 4)."""
        self.init_graphics()
        self.send_hello()

        # Non-Blocking Socket (Phase 4)
        self.socket.setblocking(False)

        start_time = time.time()
        running = True

        print(f"[CLIENT] Graphics started. Window open.")

        try:
            while running and (time.time() - start_time) < duration_sec:
                current_time = time.time()
                dt = self.clock.get_time() / 1000.0 # delta time in seconds (from tick)

                # --- 1. Event Pump & Input (Phase 4 & 5) ---
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                    # Phase 5: Client Input
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        grid_x = mouse_x // CELL_SIZE
                        grid_y = mouse_y // CELL_SIZE
                        print(f"[INPUT] Clicked Pixel ({mouse_x},{mouse_y}) -> Grid ({grid_x}, {grid_y})")
                        # Note: Sending the move request packet is skipped here 
                        # because protocol/server currently does not support MOVE messages.
                        # Logic acts as a visual placeholder for movement intent.

                # --- 2. Network Receive (Polling) (Phase 4) ---
                if (current_time - self.last_heartbeat_time) >= self.heartbeat_interval:
                    self.send_heartbeat()
                    self.last_heartbeat_time = current_time

                # Drain the socket buffer
                try:
                    while True:
                        data, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
                        if addr == self.server_address:
                            pkt, _ = unpack_packet(data)
                            if pkt.msg_type == MessageType.SERVER_INIT_RESPONSE:
                                self.handle_server_hello(data)
                            elif pkt.msg_type == MessageType.SNAPSHOT:
                                self.handle_game_state_update(data)
                except BlockingIOError:
                    # No more data available right now
                    pass
                except socket.timeout:
                    pass
                except Exception as e:
                    print(f"[NET ERROR] {e}")

                # --- 3. Render (Phase 4) ---
                self.update_visuals(dt)
                self.draw_game()
                self.clock.tick(60)  # Limit to 60 FPS

        except KeyboardInterrupt:
            print(f"[CLIENT {self.client_id}] Interrupted")
        finally:
            if self.latencies:
                avg_latency = sum(self.latencies) / len(self.latencies)
                print(f"FINAL STATS: Received {self.packet_count} packets. Average latency: {avg_latency:.4f} ms")

            try:
                if pygame.get_init():
                    pygame.quit()
            except Exception:
                # ignore pygame shutdown issues
                pass

            self.socket.close()


def main():
    parser = argparse.ArgumentParser(description="GridClash Client")
    parser.add_argument("--id", type=int, default=0, help="Client ID")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=12000, help="Server port")
    parser.add_argument("--duration", type=int, default=30, help="Run duration (seconds)")
    parser.add_argument("--heartbeat-interval", type=float, default=1.0, help="Heartbeat interval (seconds)")
    args = parser.parse_args()

    client = GridClient(args.id, (args.host, args.port))
    client.heartbeat_interval = args.heartbeat_interval
    client.run(duration_sec=args.duration)


if __name__ == "__main__":
    main()
