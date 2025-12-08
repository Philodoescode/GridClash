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

from src.protocol import unpack_packet, get_current_timestamp_ms, pack_packet, MessageType, GRID_WIDTH, GRID_HEIGHT, UNCLAIMED_ID
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

        # Grid state (Phase 3)
        self.grid_state = bytearray([UNCLAIMED_ID] * (GRID_WIDTH * GRID_HEIGHT))
        self.player_scores = {}  # {player_id: score}
        self.game_over = False
        self.winner_info = None  # (winner_id, winner_score)

        # Graphics context
        self.screen = None
        self.clock = None
        self.font = None

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
        recv_ts_ms = get_current_timestamp_ms()

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

            # New Payload Structure:
            # 1. Grid data: 400 bytes (20x20 flat array)
            # 2. Player count: 1 byte
            # 3. Per player: ID (!B), Score (!H), X (!i), Y (!i) = 11 bytes each
            
            GRID_SIZE = GRID_WIDTH * GRID_HEIGHT  # 400
            
            if len(payload) < GRID_SIZE + 1:
                return  # Malformed payload
            
            self.grid_state = bytearray(payload[:GRID_SIZE])
            
            num_players = payload[GRID_SIZE]
            offset = GRID_SIZE + 1
            
            BYTES_PER_PLAYER = 11  # ID(1) + Score(2) + X(4) + Y(4)
            
            for _ in range(num_players):
                if offset + BYTES_PER_PLAYER <= len(payload):
                    p_id, score, pos_x, pos_y = struct.unpack('!BHii', payload[offset:offset + BYTES_PER_PLAYER])
                    
                    # Update authoritative state (target) and scores
                    self.target_players[p_id] = (pos_x, pos_y)
                    self.player_scores[p_id] = score
                    
                    # If this is the first time seeing this player, snap visual to target immediately
                    if p_id not in self.visual_players:
                        self.visual_players[p_id] = (float(pos_x), float(pos_y))
                    offset += BYTES_PER_PLAYER
                else:
                    break

            # Periodic logging
            if self.packet_count % 60 == 0 and self.latencies:
                avg = sum(self.latencies) / len(self.latencies)
                print(f"[NET] Packets: {self.packet_count}, Avg Latency: {avg:.2f} ms")

        except Exception as e:
            print(f"Error unpacking packet: {e}")

    def handle_game_over(self, data):
        """Process GAME_OVER message."""
        try:
            packet, payload = unpack_packet(data)
            if packet.msg_type == MessageType.GAME_OVER and len(payload) >= 3:
                winner_id, winner_score = struct.unpack('!BH', payload[:3])
                self.game_over = True
                self.winner_info = (winner_id, winner_score)
                print(f"[GAME OVER] Winner: Player {winner_id} with score {winner_score}")
        except Exception as e:
            print(f"Error handling game over: {e}")

    def send_acquire_request(self, row, col):
        """Send ACQUIRE_REQUEST to claim a cell."""
        if self.game_over:
            return
        payload = struct.pack('!BB', row, col)
        packet = pack_packet(MessageType.ACQUIRE_REQUEST, 0, 0, get_current_timestamp_ms(), payload)
        self.socket.sendto(packet, self.server_address)
        print(f"[CLIENT] Sent ACQUIRE_REQUEST for cell ({row}, {col})")

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
        self.font = pygame.font.Font(None, 24)

    def draw_game(self):
        """Render the game state (Phase 3)."""
        if not self.screen:
            return

        # 1. Background
        self.screen.fill(WHITE)

        # 2. Claimed Cells (render before grid lines)
        for row in range(GRID_HEIGHT):
            for col in range(GRID_WIDTH):
                owner_id = self.grid_state[row * GRID_WIDTH + col]
                if owner_id != UNCLAIMED_ID:
                    color = PLAYER_COLORS.get(owner_id, PLAYER_COLORS['default'])
                    rect = (col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(self.screen, color, rect)

        # 3. Grid Lines
        for x in range(0, SCREEN_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))

        # 4. Players (cursors)
        for p_id, (x, y) in self.visual_players.items():
            color = PLAYER_COLORS.get(p_id, PLAYER_COLORS['default'])
            pygame.draw.circle(self.screen, color, (int(x), int(y)), 10)
            # Highlight self
            if p_id == self.client_id:
                pygame.draw.circle(self.screen, BLACK, (int(x), int(y)), 12, 2)

        # 5. Scoreboard
        self.draw_scoreboard()

        # 6. Game Over Overlay
        if self.game_over and self.winner_info:
            self.draw_game_over_overlay()

        # 7. Display Flip
        pygame.display.flip()

    def draw_scoreboard(self):
        """Draw score overlay in top-left corner."""
        if not self.font:
            return
        
        y_offset = 10
        for p_id in sorted(self.player_scores.keys()):
            score = self.player_scores[p_id]
            color = PLAYER_COLORS.get(p_id, PLAYER_COLORS['default'])
            # Create label
            label = f"P{p_id}: {score}"
            if p_id == self.client_id:
                label += " (You)"
            text_surface = self.font.render(label, True, color)
            # Draw background for readability
            bg_rect = text_surface.get_rect(topleft=(10, y_offset))
            bg_rect.inflate_ip(6, 2)
            pygame.draw.rect(self.screen, (255, 255, 255, 200), bg_rect)
            self.screen.blit(text_surface, (10, y_offset))
            y_offset += 22

    def draw_game_over_overlay(self):
        """Draw game over screen."""
        if not self.font or not self.winner_info:
            return
        
        winner_id, winner_score = self.winner_info
        
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Winner text
        big_font = pygame.font.Font(None, 48)
        if winner_id == self.client_id:
            text = "YOU WIN!"
        else:
            text = f"Player {winner_id} Wins!"
        text_surface = big_font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
        self.screen.blit(text_surface, text_rect)
        
        # Score text
        score_text = f"Score: {winner_score}"
        score_surface = self.font.render(score_text, True, (200, 200, 200))
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(score_surface, score_rect)

    def run(self):
        """Main client loop (Phase 4)."""
        self.init_graphics()
        self.send_hello()

        # Non-Blocking Socket (Phase 4)
        self.socket.setblocking(False)

        running = True

        print(f"[CLIENT] Graphics started. Window open.")

        try:
            while running:
                current_time = time.time()
                dt = self.clock.get_time() / 1000.0 # delta time in seconds (from tick)

                # --- 1. Event Pump & Input (Phase 4 & 5) ---
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        grid_x = mouse_x // CELL_SIZE
                        grid_y = mouse_y // CELL_SIZE
                        print(f"[INPUT] Clicked Pixel ({mouse_x},{mouse_y}) -> Grid ({grid_x}, {grid_y})")
                        self.send_acquire_request(grid_y, grid_x)

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
                            elif pkt.msg_type == MessageType.GAME_OVER:
                                self.handle_game_over(data)
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
    parser.add_argument("--heartbeat-interval", type=float, default=1.0, help="Heartbeat interval (seconds)")
    args = parser.parse_args()

    client = GridClient(args.id, (args.host, args.port))
    client.heartbeat_interval = args.heartbeat_interval
    client.run()


if __name__ == "__main__":
    main()