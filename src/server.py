"""Server for GridClash game."""
import os
import random
import socket
import struct
import sys
import time

# import from parent directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.protocol import pack_packet, MessageType, get_current_timestamp_ms, unpack_packet, GRID_WIDTH, GRID_HEIGHT, UNCLAIMED_ID

# Network configurations
DEFAULT_PORT = 12000
GRID_SIZE = 20
MAX_PACKET_SIZE = 1200


PLAYER_POSITIONS = {
    0: (random.randint(2, 8), random.randint(2, 8)),      # Top Left
    1: (random.randint(12, 18), random.randint(2, 8)),      # Top Right
    2: (random.randint(2, 8), random.randint(12, 18)),      # Bottom Left
    3: (random.randint(12, 18), random.randint(12, 18)),    # Bottom Right
    'default': (10, 10)  # middle for unknown IDs
}

class GridServer:
    """
    GridServer class for managing the game state and client connections.

    The server must:
    - Broadcast periodic snapshots to all connected clients.
    - Maintain per-client state (sequence tracking, last acknowledged snapshot).
    - Support 4 concurrent clients without exceeding CPU limits.
    - Send additional redundant or delta updates to improve reliability. (will be implemented later in phase 2)
    - Log performance metrics (CPU usage, update frequency, packet counts)
    """

    def __init__(self, port=DEFAULT_PORT, grid_size=GRID_SIZE):
        """Initialize server"""
        self.port = port
        self.grid_size = grid_size
        self.max_clients = 4
        self.heartbeat_timeout = 10  # seconds
        self.broadcast_frequency = 20  # hz
        self.max_packet_size = MAX_PACKET_SIZE

        # Socket setup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', self.port))
        self.socket.setblocking(False)

        # State
        self.clients = {}
        self.next_player_id = 0
        self.snapshot_id = 0
        self.seq_num = 0
        self.active_clients_ids = []
        self.clients_pos = {}
        # Grid state: 400 bytes (20x20), each cell stores owner ID (255 = unclaimed)
        self.grid_state = bytearray([UNCLAIMED_ID] * (GRID_WIDTH * GRID_HEIGHT))
        self.grid_ts = [[0 for _ in range(GRID_HEIGHT)] for _ in range(GRID_WIDTH)]  # ← CRITICAL: Timestamp per cell
        self.scores = {}  # {player_id: score}
        self.game_active = True
        self.claimed_cells = 0
        self.winner_id = None
        self.winner_score = 0


        print(f"[SERVER] Grid size: {grid_size}x{grid_size}")
        print(f"[SERVER] Server is up and running on port {self.port}")

    def get_available_player_id(self):
        used_ids = self.active_clients_ids.copy()
        for pid in range(self.max_clients):
            if pid not in used_ids:
                return pid
        return None  # server full

    def handle_client_hello(self, client_address):
        """INIT handshake with client"""
        if self.game_active:

            # checks if player is already connected
            if client_address in self.clients:
                print(f"{client_address} already connected.")
                return

            # check if server is full
            if len(self.active_clients_ids) >= self.max_clients:
                print(f"Server full. connection declined with {client_address}")
                payload = struct.pack('!B', 0)

                response_packet = pack_packet(MessageType.SERVER_FULL, 0, 0, get_current_timestamp_ms(),
                                              payload)
                self.socket.sendto(response_packet, client_address)
                return
            # find id of disconnected player to give
            player_id = self.get_available_player_id()


            if player_id in self.clients_pos:
                pos = self.clients_pos[player_id]
            else:
                pos = PLAYER_POSITIONS.get(player_id, PLAYER_POSITIONS['default'])

            self.clients_pos[player_id] = pos

            self.clients[client_address] = {
                'player_id': player_id,
                'seq_num': 0,
                'last_heartbeat': time.time(),
                'pos': pos, # starting position
                'processed_seqs': set()
            }
            self.active_clients_ids.append(player_id)
            if player_id not in self.scores:
                self.scores[player_id] = 0
            self.next_player_id += 1
            print(f"{client_address} connected. player_id {player_id}")

            # respond with server hello message
            pos_x, pos_y = self.clients[client_address]['pos']

            payload = struct.pack('!Bii', player_id, pos_x, pos_y) # 9 bytes
            #payload = struct.pack('!B', player_id)  # as max is 4
            response_packet = pack_packet(MessageType.SERVER_INIT_RESPONSE, 0, 0, get_current_timestamp_ms(),
                                          payload)
            self.socket.sendto(response_packet, client_address)
            self.acquire_cell(pos_x, pos_y, player_id)
        else:
            print(f"Game over. connection Declined with {client_address}")
            # send current state
            self.send_current_state(client_address)
            current_timestamp = get_current_timestamp_ms()
            #send winner data
            payload = struct.pack('!BH', self.winner_id, self.winner_score)
            packet = pack_packet(MessageType.GAME_OVER, self.snapshot_id, 0, current_timestamp,
                                 payload)
            self.socket.sendto(packet, client_address)

            return

    # updating client heartbeat
    def handle_client_heartbeat(self, client_address):
        if client_address in self.clients:
            self.clients[client_address]['last_heartbeat'] = time.time()

    # timeout handling
    def handle_timeout(self):
        current_time = time.time()
        timed_out_clients = []
        for clientAddress, clientData in self.clients.items():
            if current_time - clientData['last_heartbeat'] > self.heartbeat_timeout:
                timed_out_clients.append(clientAddress)

        # remove timed out clients
        for clientAddress in timed_out_clients:
            player_id = self.clients[clientAddress]['player_id']
            print(f"{clientAddress} timed out (Player {player_id})")
            if player_id in self.active_clients_ids:
                self.active_clients_ids.remove(player_id)
            del self.clients[clientAddress]

    def handle_acquire_request(self, client_address, payload, packet_seq_num):
        """Handle ACQUIRE_REQUEST with reliability (ACKs) and Duplicate Suppression."""
        
        if not self.game_active or client_address not in self.clients:
            return
    
        client = self.clients[client_address]
    
    # Duplicate suppression
        if packet_seq_num in client['processed_seqs']:
        # Re-send previous ACK/NACK if needed
            prev_ack_payload = struct.pack('!I?', packet_seq_num, True)  # True=ACK
            ack_packet = pack_packet(MessageType.ACK, self.snapshot_id, 0, get_current_timestamp_ms(), prev_ack_payload)
            self.socket.sendto(ack_packet, client_address)
            return

    # Payload unpack
        if len(payload) < 2:
            return
        row, col = struct.unpack('!BB', payload[:2])
        if row >= GRID_HEIGHT or col >= GRID_WIDTH:
            return

        index = row * GRID_WIDTH + col
        player_id = client['player_id']
        success = False

    # Check cell ownership
        if self.grid_state[index] == UNCLAIMED_ID:
            self.grid_state[index] = player_id
            self.scores[player_id] = self.scores.get(player_id, 0) + 1
            self.claimed_cells += 1
            success = True
            print(f"[ACQUIRE] Player {player_id} claimed ({row},{col})")
        elif self.grid_state[index] == player_id:
            success = True  # Already owned
    # else success=False (cell claimed by another player)

    # Update position regardless
        client['pos'] = (col, row)
        self.clients_pos[player_id] = (col, row)

    # Mark processed
        client['processed_seqs'].add(packet_seq_num)

    # Send selective ACK/NACK
        ack_payload = struct.pack('!I?', packet_seq_num, success)  # bool: True=ACK, False=NACK
        ack_packet = pack_packet(MessageType.ACK, self.snapshot_id, 0, get_current_timestamp_ms(), ack_payload)
        self.socket.sendto(ack_packet, client_address)

    # Check game over
        if self.claimed_cells >= GRID_WIDTH * GRID_HEIGHT or self.scores[player_id] >= GRID_WIDTH * GRID_HEIGHT / 2:
            self.broadcast_game_over()

    def acquire_cell(self, col, row, player_id):
        index = row * GRID_WIDTH + col

        self.grid_state[index] = player_id
        self.scores[player_id] = self.scores.get(player_id, 0) + 1
        self.claimed_cells += 1



    def broadcast_game_over(self):
        """Broadcast GAME_OVER to all clients."""
        self.game_active = False
        
        # Find winner (highest score)

        self.winner_id = 0  # Default to player 0
        for player_id, score in self.scores.items():
            if score > self.winner_score:
                self.winner_id = player_id
                self.winner_score = score
        
        print(f"[GAME OVER] Winner: Player {self.winner_id} with score {self.winner_score}")
        
        payload = struct.pack('!BH', self.winner_id, self.winner_score)
        current_timestamp = get_current_timestamp_ms()
        clients_snapshot = list(self.clients.items())
        for clientAddress, clientData in clients_snapshot:
            clientData['seq_num'] += 1
            packet = pack_packet(MessageType.GAME_OVER, self.snapshot_id, clientData['seq_num'], current_timestamp, payload)
            self.socket.sendto(packet, clientAddress)

    # DATA broadcast
    def state_broadcast(self):
        if not self.clients:
            return
        self.snapshot_id += 1
        current_timestamp = get_current_timestamp_ms()
        
        # New payload structure:
        # 1. Grid data: 400 bytes (20x20 flat array, 1 byte per cell = owner ID)
        # 2. Player count: 1 byte
        # 3. Per player: ID (!B), Score (!H), Cursor_X (!i), Cursor_Y (!i) = 11 bytes each
        
        # Pack grid state (400 bytes)
        payload = bytes(self.grid_state)
        
        # Pack player count and player data
        num_players = len(self.clients)
        payload += struct.pack('!B', num_players)
        
        for clientData in self.clients.values():
            player_id = clientData['player_id']
            score = self.scores.get(player_id, 0)
            curr_pos = clientData['pos']
            
            # ← DELTA ENCODING
            prev_pos = clientData.get('prev_pos', curr_pos)
            dx = curr_pos[0] - prev_pos[0]
            dy = curr_pos[1] - prev_pos[1]
            clientData['prev_pos'] = curr_pos  # Save for next

            # Pack: ID, Score, X, Y, dX, dY → 17 bytes
            payload += struct.pack('!BHiiii', player_id, score, curr_pos[0], curr_pos[1], dx, dy)

        # send packets to all connected clients
        for clientAddress, clientData in self.clients.items():
            clientData['seq_num'] += 1
            packet = pack_packet(MessageType.SNAPSHOT, self.snapshot_id, clientData['seq_num'], current_timestamp,
                                 payload)
            self.socket.sendto(packet, clientAddress)


    def send_current_state(self, client_address):
        """Send current game state to a new client."""
        current_timestamp = get_current_timestamp_ms()

        # Pack grid state (400 bytes)
        payload = bytes(self.grid_state)

        # Pack player count and player data
        num_players = len(self.clients)
        payload += struct.pack('!B', num_players)

        for clientData in self.clients.values():
            player_id = clientData['player_id']
            score = self.scores.get(player_id, 0)
            curr_pos = clientData['pos']

            # Pack: ID (1 byte), Score (2 bytes), X (4 bytes), Y (4 bytes) = 11 bytes
            payload += struct.pack('!BHii', player_id, score, curr_pos[0], curr_pos[1])

            packet = pack_packet(MessageType.SNAPSHOT, self.snapshot_id, clientData['seq_num'], current_timestamp,
                                 payload)
            self.socket.sendto(packet, client_address)

    def run(self):
        # self.socket.settimeout(0.001)

        last_broadcast_time = time.time()
        last_timeout_check = time.time()
        broadcast_interval = 1.0 / self.broadcast_frequency

        # main server loop
        while 1:
            try:
                try:
                    data, client_address = self.socket.recvfrom(self.max_packet_size)
                    pkt, payload = unpack_packet(data)
                    if pkt.msg_type == MessageType.CLIENT_INIT:
                        self.handle_client_hello(client_address)
                    elif pkt.msg_type == MessageType.HEARTBEAT:
                        self.handle_client_heartbeat(client_address)
                    elif pkt.msg_type == MessageType.ACQUIRE_REQUEST:
                        self.handle_acquire_request(client_address, payload, pkt.seq_num)
                    elif pkt.msg_type == MessageType.NEW_GAME:
                        self.handle_new_game()
                except BlockingIOError:
                    # Expected: no data to receive
                    pass
                except socket.timeout:
                    # Expected: timeout
                    pass
                except ConnectionResetError:
                    # BUG FIX: This error occurs on Windows when a client socket is forcibly closed.
                    # For a connectionless protocol like UDP, it's safe to ignore and continue operating.
                    pass
                except Exception as e:
                    print(f"[ERROR] Unexpected socket error: {e}")
                    continue

                current_time = time.time()

                # brodacast at the configured freq
                if current_time - last_broadcast_time >= broadcast_interval:
                    self.state_broadcast()
                    last_broadcast_time += broadcast_interval

                # checking timeouts periodically (currently once every sec)
                if current_time - last_timeout_check >= 1.0:
                    self.handle_timeout()
                    last_timeout_check = current_time

                # somehow this prevents 100% usage of cpu based on ai response
                time.sleep(0.001)

            except KeyboardInterrupt:
                print("Server shutting down.")
                break
            except Exception as e:
                print(f"Error: {e}")
                break

        self.socket.close()
    def reset_server(self):
        print("[SERVER] Resetting server state...")
        self.snapshot_id = 0
        self.seq_num = 0
        self.grid_state = bytearray([UNCLAIMED_ID] * (GRID_WIDTH * GRID_HEIGHT))
        self.grid_ts = [[0 for _ in range(GRID_HEIGHT)] for _ in range(GRID_WIDTH)]  # ← RESET TIMESTAMPS
        self.scores = {}
        self.game_active = True
        self.claimed_cells = 0
        self.winner_id = None
        self.winner_score = 0
        self.clients_pos = {}


    def handle_new_game(self):
        if self.game_active:
            print("[SERVER] Game already active, ignoring NEW_GAME request")
            return
        print("[SERVER] Processing NEW_GAME request...")
        # Store current client addresses before reset
        connected_clients = list(self.clients.keys())


        for client_addr in connected_clients:
            player_id = self.clients[client_addr]['player_id']
            self.clients[client_addr] = {
                'player_id': player_id,
                'seq_num': 0,
                'last_heartbeat': time.time(),
                'pos': PLAYER_POSITIONS.get(player_id, PLAYER_POSITIONS['default']),
                'processed_seqs': set()
            }
            self.scores[player_id] = 0
            #self.next_player_id += 1
            pos_x, pos_y = PLAYER_POSITIONS.get(player_id, PLAYER_POSITIONS['default'])
            # Send SERVER_INIT_RESPONSE with new ID
            payload = struct.pack('!Bii', player_id, pos_x, pos_y)
            response_packet = pack_packet(
                MessageType.SERVER_INIT_RESPONSE,
                0, 0,
                get_current_timestamp_ms(),
                payload
            )
            self.socket.sendto(response_packet, client_addr)
            print(f"[SERVER] Re-assigned Player {player_id} to {client_addr}")

            # Reset server state
        self.reset_server()
            # Broadcast initial clean state immediately
        self.state_broadcast()
        print("[SERVER] New game started and broadcasted to all clients")




def main():
    server = GridServer()
    server.run()


if __name__ == "__main__":
    main()