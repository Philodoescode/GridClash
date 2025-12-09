"""Client for GridClash game."""
import argparse
import os
import socket
import struct
import sys
import time
from collections import deque

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
PLAYER_STRIP_HEIGHT = 100
SCREEN_HEIGHT = 600 + PLAYER_STRIP_HEIGHT  # Grid + player strip
GRID_SIZE = 20  # 20x20 Grid
CELL_SIZE = 600 // GRID_SIZE  # Grid cell size

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
GRID_COLOR = (200, 200, 200)
BUTTON_COLOR = (70, 130, 180)  # Steel blue
BUTTON_HOVER_COLOR = (100, 149, 237)  # Cornflower blue
STRIP_BG_COLOR = (240, 240, 240)

PLAYER_COLORS = {
    0: (255, 0, 0),      # Red
    1: (0, 0, 255),      # Blue
    2: (0, 255, 0),      # Green
    3: (255, 255, 0),    # Yellow
    'default': (100, 100, 100)  # Gray for unknown IDs
}

# Connection timeout
CONNECTION_TIMEOUT = 10.0  # seconds


class Button:
    """Simple button class for UI."""

    def __init__(self, x, y, width, height, text, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.hovered = False

    def is_hovered(self, mouse_pos):
        """Check if mouse is over button."""
        self.hovered = self.rect.collidepoint(mouse_pos)
        return self.hovered

    def is_clicked(self, mouse_pos):
        """Check if button was clicked."""
        return self.rect.collidepoint(mouse_pos)

    def draw(self, surface, mouse_pos):
        """Draw the button."""
        self.is_hovered(mouse_pos)
        color = BUTTON_HOVER_COLOR if self.hovered else BUTTON_COLOR

        # Draw button background
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, WHITE, self.rect, 2)  # Border

        # Draw text
        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)




class GridClient:
    """
    GridClient class for managing the client-side of the game.
    """

    def __init__(self, client_id=255, server_address=('127.0.0.1', 12000)):
        """Initialize client."""
        self.waiting_for_new_game = False
        self.client_id = client_id
        self.server_address = server_address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.last_heartbeat_time = time.time()
        self.heartbeat_interval = 1.0
        self.packet_count = 0
        self.latencies = deque(maxlen=1000)  # Limit memory usage

        # Connection tracking
        self.last_packet_time = time.time()
        self.connected = True
        self.server_full = False
        # State Management (Phase 2)
        self.target_players = {}  # {player_id: (target_x, target_y)} -> Authoritative from server
        self.visual_players = {}  # {player_id: (curr_x, curr_y)} -> Smoothed for rendering

        # Snapshot/sequence tracking to detect stale/duplicate packets
        self.last_snapshot_id = -1
        self.last_seq_num = -1
        self.pos_x = 0
        self.pos_y = 0
        # Grid state (Phase 3)
        self.grid_state = bytearray([UNCLAIMED_ID] * (GRID_WIDTH * GRID_HEIGHT))
        self.player_scores = {}  # {player_id: score}
        self.game_over = False
        self.winner_info = None  # (winner_id, winner_score)

        # Graphics context
        self.screen = None
        self.clock = None
        self.font = None
        self.big_font = None
        self.new_game_button = None

    def is_legal_move(self, row, col):
        """Check if move is legal."""
        # Check if cell is unclaimed
        index = row * GRID_WIDTH + col
        # Bounds check
        if not (0 <= row < GRID_HEIGHT and 0 <= col < GRID_WIDTH):
            return False

        if self.grid_state[index] != UNCLAIMED_ID and self.grid_state[index] != self.client_id:
            print(f"[CLIENT] Cell ({row}, {col}) is already claimed")
            return False

        # check if the cell is adjacent (one step up, down, left, or right)
        dx = abs(col - self.pos_x) # change in x/column
        dy = abs(row - self.pos_y) # change in y/row
        # dx  = 1, dy = 0 -> move right
        if  not (((dx == 1 and dy == 0) or
                 (dx == 0 and dy == 1))):
            print(f"[CLIENT] Move to ({row}, {col}) is not adjacent to current position ({self.pos_x}, {self.pos_y}) , dx: {dx}, dy: {dy}")
            return False


        return True
        pass

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

    def handle_server_hello(self, data):
        """Process SERVER_HELLO response."""

        try:
            pkt, payload = unpack_packet(data)
            if pkt.msg_type == MessageType.SERVER_INIT_RESPONSE and len(payload) >= 1:
                assigned_id, pos_x, pos_y = struct.unpack('!Bii', payload[:9])
                self.pos_x = pos_x
                self.pos_y = pos_y
                print(f"[CLIENT {self.client_id}] Server assigned ID: {assigned_id}, pos: ({pos_x}, {pos_y})")
                if self.waiting_for_new_game:
                    self.reset_game_state()
                    self.waiting_for_new_game = False
                    print(f"[CLIENT {self.client_id}] New game confirmed, state reset")
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

            # Stale/duplicate checks
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

            # Update connection time
            self.last_packet_time = time.time()
            self.connected = True

            # Parse payload
            GRID_SIZE_BYTES = GRID_WIDTH * GRID_HEIGHT  # 400
            if len(payload) < GRID_SIZE_BYTES + 1:
                return  # Malformed payload

            self.grid_state = bytearray(payload[:GRID_SIZE_BYTES])
            num_players = payload[GRID_SIZE_BYTES]
            offset = GRID_SIZE_BYTES + 1

            BYTES_PER_PLAYER = 11  # ID(1) + Score(2) + X(4) + Y(4)

            # Track which players are in this update
            current_players = set()

            for _ in range(num_players):
                if offset + BYTES_PER_PLAYER <= len(payload):
                    p_id, score, pos_x, pos_y = struct.unpack('!BHii', payload[offset:offset + BYTES_PER_PLAYER])

                    # Update authoritative state (target) and scores
                    self.target_players[p_id] = (pos_x, pos_y)
                    self.player_scores[p_id] = score
                    current_players.add(p_id)

                    # If this is the first time seeing this player, snap visual to target immediately
                    if p_id not in self.visual_players:
                        self.visual_players[p_id] = (float(pos_x), float(pos_y))

                    offset += BYTES_PER_PLAYER
                else:
                    break

            # Remove disconnected players
            for p_id in list(self.visual_players.keys()):
                if p_id not in current_players:
                    del self.visual_players[p_id]
                    if p_id in self.target_players:
                        del self.target_players[p_id]
                    if p_id in self.player_scores:
                        del self.player_scores[p_id]

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
        if not self.is_legal_move(row, col):
            print(f"[CLIENT] Illegal move: ({row}, {col}), pos: ({self.pos_x}, {self.pos_y})")
            return
        # Bounds check
        if not (0 <= row < GRID_HEIGHT and 0 <= col < GRID_WIDTH):
            return
        self.pos_x = col
        self.pos_y = row
        payload = struct.pack('!BB', row, col)
        packet = pack_packet(MessageType.ACQUIRE_REQUEST, 0, 0, get_current_timestamp_ms(), payload)
        self.socket.sendto(packet, self.server_address)
        print(f"[CLIENT] Sent ACQUIRE_REQUEST for cell ({row}, {col})")

    def update_visuals(self, dt):
        """
        Interpolate visual positions towards target positions.
        dt: Time delta in seconds since last frame.
        """
        SMOOTHING_SPEED = 10.0
        lerp_factor = SMOOTHING_SPEED * dt
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
        self.big_font = pygame.font.Font(None, 48)

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


        # 2.5 Highlight current player position
        highlight_color = (255, 255, 255, 120)  # semi-transparent white overlay
        overlay = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(overlay, highlight_color, overlay.get_rect())
        self.screen.blit(overlay, (self.pos_x * CELL_SIZE, self.pos_y * CELL_SIZE))
        highlight_rect = (
            self.pos_x * CELL_SIZE,
            self.pos_y * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE
        )
        pygame.draw.rect(self.screen, (255, 255, 255), highlight_rect, 4)  # white border
        pygame.draw.rect(self.screen, (0, 0, 0), highlight_rect, 2)

        # 3. Grid Lines
        for x in range(0, SCREEN_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, 600))
        for y in range(0, 600, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))

        # # 4. Players (cursors)
        # for p_id, (x, y) in self.visual_players.items():
        #     color = PLAYER_COLORS.get(p_id, PLAYER_COLORS['default'])
        #     pygame.draw.circle(self.screen, color, (int(x), int(y)), 10)
        #     # Highlight self
        #     if p_id == self.client_id:
        #         pygame.draw.circle(self.screen, BLACK, (int(x), int(y)), 12, 2)

        # 5. Player Strip
        self.draw_player_strip()


        # 6. Server Full Overlay
        if self.server_full:
            self.draw_server_full_overlay()
        else:
            # 7. Connection Status
            if not self.connected:
                self.draw_connection_lost()
            # 8. Game Over Overlay
            if self.game_over and self.winner_info:
                self.draw_game_over_overlay()





        # 9. Display Flip
        pygame.display.flip()

    def draw_player_strip(self):
        """Draw horizontal player strip below the grid."""
        strip_y = 600

        # Background
        pygame.draw.rect(self.screen, STRIP_BG_COLOR, (0, strip_y, SCREEN_WIDTH, PLAYER_STRIP_HEIGHT))

        # Dividing lines
        pygame.draw.line(self.screen, DARK_GRAY, (0, strip_y), (SCREEN_WIDTH, strip_y), 2)

        # Get sorted player list (max 4)
        players = sorted(self.player_scores.keys())[:4]
        if not players:
            return

        slot_width = SCREEN_WIDTH // 4

        for idx, p_id in enumerate(players):
            x_start = idx * slot_width
            x_center = x_start + slot_width // 2

            # Player color indicator
            color = PLAYER_COLORS.get(p_id, PLAYER_COLORS['default'])
            indicator_rect = (x_start + 10, strip_y + 10, 40, 40)
            pygame.draw.rect(self.screen, color, indicator_rect)
            pygame.draw.rect(self.screen, BLACK, indicator_rect, 2)

            # Player cursor icon
            pygame.draw.circle(self.screen, color, (x_start + 30, strip_y + 30), 8)
            if p_id == self.client_id:
                pygame.draw.circle(self.screen, BLACK, (x_start + 30, strip_y + 30), 10, 2)

            # Player label
            if p_id == self.client_id:
                label = f"Player {p_id} (You)"
            else:
                label = f"Player {p_id}"

            label_surface = self.font.render(label, True, BLACK)
            self.screen.blit(label_surface, (x_start + 60, strip_y + 15))

            # Score
            score = self.player_scores.get(p_id, 0)
            score_text = f"Score: {score}"
            score_surface = self.font.render(score_text, True, DARK_GRAY)
            self.screen.blit(score_surface, (x_start + 60, strip_y + 45))

            # Vertical divider (except for last player)
            if idx < len(players) - 1:
                pygame.draw.line(self.screen, LIGHT_GRAY,
                               (x_start + slot_width, strip_y),
                               (x_start + slot_width, strip_y + PLAYER_STRIP_HEIGHT))

    def draw_connection_lost(self):
        """Draw connection lost indicator."""
        text = "Connection Lost..."
        text_surface = self.font.render(text, True, (255, 0, 0))
        text_rect = text_surface.get_rect(topright=(SCREEN_WIDTH - 10, 10))

        # Background
        bg_rect = text_rect.inflate(10, 4)
        pygame.draw.rect(self.screen, (255, 255, 200), bg_rect)
        self.screen.blit(text_surface, text_rect)

    def draw_game_over_overlay(self):
        """Draw game over screen with New Game button."""
        if not self.big_font or not self.winner_info:
            return

        winner_id, winner_score = self.winner_info

        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Winner text
        if winner_id == self.client_id:
            text = "YOU WIN!"
            text_color = (50, 255, 50)  # Bright green
        else:
            text = f"Player {winner_id} Wins!"
            text_color = (255, 255, 255)

        text_surface = self.big_font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
        self.screen.blit(text_surface, text_rect)

        # Score text
        score_text = f"Final Score: {winner_score}"
        score_surface = self.font.render(score_text, True, (200, 200, 200))
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
        self.screen.blit(score_surface, score_rect)

        # New Game Button
        button_width = 200
        button_height = 50
        button_x = (SCREEN_WIDTH - button_width) // 2
        button_y = SCREEN_HEIGHT // 2 + 20

        if not self.new_game_button:
            self.new_game_button = Button(button_x, button_y, button_width, button_height,
                                         "New Game", self.font)

        mouse_pos = pygame.mouse.get_pos()
        self.new_game_button.draw(self.screen, mouse_pos)

    def reset_game_state(self):
        """Reset game state for new game."""
        self.game_over = False
        self.winner_info = None
        self.grid_state = bytearray([UNCLAIMED_ID] * (GRID_WIDTH * GRID_HEIGHT))
        self.player_scores.clear()
        self.target_players.clear()
        self.visual_players.clear()
        self.new_game_button = None
        self.last_snapshot_id = -1
        self.last_seq_num = -1
        self.draw_game()
        print("[CLIENT] Game state reset")

    def request_new_game(self):
        """Send new game request to server."""
        payload = struct.pack('!B', self.client_id)
        packet = pack_packet(MessageType.NEW_GAME, 0, 0, get_current_timestamp_ms(), payload)
        self.socket.sendto(packet, self.server_address)
        print(f"[CLIENT {self.client_id}] Sent new game request")
        #self.reset_game_state()
        self.waiting_for_new_game = True
        self.new_game_button = None

    def check_connection(self):
        """Check if connection to server is still alive."""
        if time.time() - self.last_packet_time > CONNECTION_TIMEOUT:
            if self.connected:
                print("[WARNING] Connection timeout - no packets received")
                self.connected = False

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
                dt = self.clock.get_time() / 1000.0  # delta time in seconds (from tick)


                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        # Check for New Game button click first
                        if self.game_over and self.new_game_button:
                            if self.new_game_button.is_clicked(event.pos):
                                self.request_new_game()
                                continue  # Skip grid click handling

                        # Handle keyboard clicks (only if not game over)
                    elif event.type == pygame.KEYDOWN:
                        if not self.game_over:
                            match event.key:
                                case pygame.K_UP:
                                    self.send_acquire_request(self.pos_y - 1, self.pos_x)
                                case pygame.K_DOWN:
                                    self.send_acquire_request(self.pos_y + 1, self.pos_x)
                                case pygame.K_LEFT:
                                    self.send_acquire_request(self.pos_y, self.pos_x - 1)
                                case pygame.K_RIGHT:
                                    self.send_acquire_request(self.pos_y, self.pos_x + 1)
                                case _:
                                    pass



                # --- 2. Network Receive (Polling) (Phase 4) ---
                if (current_time - self.last_heartbeat_time) >= self.heartbeat_interval:
                    self.send_heartbeat()
                    self.last_heartbeat_time = current_time

                # Check connection status
                self.check_connection()

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
                            elif pkt.msg_type == MessageType.SERVER_FULL:
                                self.handle_server_full(data)
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
                pygame.quit()
            except Exception:
                pass
            self.socket.close()

    def handle_server_full(self, data):
        """Process SERVER_FULL message."""
        self.server_full = True
        print("[CLIENT] Server is full. Please try again later.")


    def draw_server_full_overlay(self):
        """Draw server full screen."""
        if not self.big_font:
            return

        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Server full text
        text = "SERVER IS FULL"
        text_surface = self.big_font.render(text, True, (255, 100, 100))  # Red
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
        self.screen.blit(text_surface, text_rect)

        # Subtitle
        subtitle = "Maximum 4 players reached"
        subtitle_surface = self.font.render(subtitle, True, (200, 200, 200))
        subtitle_rect = subtitle_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(subtitle_surface, subtitle_rect)



def main():
    parser = argparse.ArgumentParser(description="GridClash Client")
    parser.add_argument("--id", type=int, default=255, help="Client ID")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=12000, help="Server port")
    parser.add_argument("--heartbeat-interval", type=float, default=1.0, help="Heartbeat interval (seconds)")
    args = parser.parse_args()

    client = GridClient(args.id, (args.host, args.port))
    client.heartbeat_interval = args.heartbeat_interval
    client.run()


if __name__ == "__main__":
    main()