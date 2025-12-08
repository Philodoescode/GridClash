"""Server for GridClash game."""
import os
import socket
import struct
import sys
import time

# import from parent directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.protocol import pack_packet, MessageType, get_current_timestamp_ms, unpack_packet

# Network configurations
DEFAULT_PORT = 12000
GRID_SIZE = 20
MAX_PACKET_SIZE = 1200


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

        print(f"[SERVER] Grid size: {grid_size}x{grid_size}")
        print(f"[SERVER] Server is up and running on port {self.port}")

    def handle_client_hello(self, client_address):
        """INIT handshake with client"""

        # checks if player is already connected
        if client_address in self.clients:
            print(f"{client_address} already connected.")
            return

        # check if server is full
        if len(self.clients) >= self.max_clients:
            print(f"Server full. connection failed with {client_address}")
            return

        # add the new client
        player_id = self.next_player_id
        self.clients[client_address] = {
            'player_id': player_id,
            'seq_num': 0,
            'last_heartbeat': time.time(),
            'pos': (10 * (player_id + 1), 10 * (player_id + 1))  # just a placeholder
        }
        self.next_player_id += 1
        print(f"{client_address} connected. player_id {player_id}")

        # respond with server hello message
        payload = struct.pack('!B', player_id)  # as max is 4
        response_packet = pack_packet(MessageType.SERVER_INIT_RESPONSE, 0, 0, get_current_timestamp_ms(),
                                      payload)
        self.socket.sendto(response_packet, client_address)

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
            print(f"{clientAddress} timed out")
            del self.clients[clientAddress]

    # DATA broadcast
    def state_broadcast(self):
        if not self.clients:
            return
        self.snapshot_id += 1
        current_timestamp = get_current_timestamp_ms()
        # create the payload for the game state update.
        # the payload contains positions of all players.
        # each upadte should include (already included in):
        # seq_num
        # snapshot_id
        # sever_timestamp
        # TODO: implement payload calculation

        # payload calculation
        # payload:
        #   number of players
        #   each player id
        #   each player current pos in x and y
        #   redundant delta (dx, dy) from previous frame
        num_players = len(self.clients)
        payload = struct.pack('!B', num_players)
        for clientData in self.clients.values():
            player_id = clientData['player_id']
            curr_pos = clientData['pos']
            
            # Retrieve previous position, default to current if not set
            prev_pos = clientData.get('prev_pos', curr_pos)
            
            # Calculate delta
            dx = curr_pos[0] - prev_pos[0]
            dy = curr_pos[1] - prev_pos[1]
            
            # Update prev_pos for next broadcast
            clientData['prev_pos'] = curr_pos

            # Pack: ID, X, Y, dX, dY
            payload += struct.pack('!Biiii', player_id, curr_pos[0], curr_pos[1], dx, dy)

        # send packets to all connected clients
        for clientAddress, clientData in self.clients.items():
            clientData['seq_num'] += 1
            packet = pack_packet(MessageType.SNAPSHOT, self.snapshot_id, clientData['seq_num'], current_timestamp,
                                 payload)
            self.socket.sendto(packet, clientAddress)

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


def main():
    server = GridServer()
    server.run()


if __name__ == "__main__":
    main()