"""Client for GridClash game."""
import argparse
import os
import socket
import struct
import sys
import time

# import from parent directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.protocol import unpack_packet, get_current_timestamp_ms, pack_packet, MessageType
from src.server import MAX_PACKET_SIZE


class GridClient:
    """
    GridClient class for managing the client-side of the game.
    """

    def __init__(self, client_id=0, server_address=('127.0.0.1', 12000)):
        """Initialize client."""
        self.client_id = client_id
        self.server_address = server_address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.last_heartbeat_time = time.time()
        self.heartbeat_interval = 1.0
        self.packet_count = 0
        self.latencies = []

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
        print(f"[CLIENT {self.client_id}] Sent HEARTBEAT")

    def handle_server_hello(self, data):
        """Process SERVER_HELLO response."""
        try:
            pkt, payload = unpack_packet(data)
            if pkt.msg_type == MessageType.SERVER_INIT_RESPONSE and len(payload) >= 1:
                assigned_id = struct.unpack('!B', payload[:1])[0]
                print(f"[CLIENT {self.client_id}] Server assigned ID: {assigned_id}")
                self.client_id = assigned_id  # BUG FIX: Update client ID with the one assigned by the server
        except ValueError as e:
            print(f"[ERROR] Invalid SERVER_HELLO: {e}")

    def handle_game_state_update(self, data):
        """Process game state update."""
        recv_ts_ms = get_current_timestamp_ms()

        try:
            packet, payload = unpack_packet(data)
            if packet.msg_type == MessageType.SNAPSHOT:
                # self.handle_game_state_update(payload)
                self.packet_count += 1
                latency = recv_ts_ms - packet.server_timestamp
                self.latencies.append(latency)

                if self.packet_count % 20 == 0:
                    print(
                        f"Received {self.packet_count} packets. Average latency: {sum(self.latencies) / len(self.latencies)} ms")

        except Exception as e:
            print(f"Error unpacking packet: {e}")

    def run(self, duration_sec=30):
        """Main client loop."""
        self.send_hello()
        self.socket.settimeout(1.0)

        start_time = time.time()
        try:
            while (time.time() - start_time) < duration_sec:
                current_time = time.time()

                if (current_time - self.last_heartbeat_time) >= self.heartbeat_interval:
                    self.send_heartbeat()
                    self.last_heartbeat_time = current_time

                try:
                    data, addr = self.socket.recvfrom(MAX_PACKET_SIZE)
                    if addr == self.server_address:
                        pkt, _ = unpack_packet(data)
                        if pkt.msg_type == MessageType.SERVER_INIT_RESPONSE:
                            self.handle_server_hello(data)
                        elif pkt.msg_type == MessageType.SNAPSHOT:
                            self.handle_game_state_update(data)
                except socket.timeout:
                    pass
        except KeyboardInterrupt:
            print(f"[CLIENT {self.client_id}] Interrupted")
        finally:
            # IMPROVEMENT: Add a final summary print for robust log parsing
            if self.latencies:
                avg_latency = sum(self.latencies) / len(self.latencies)
                print(
                    f"FINAL STATS: Received {self.packet_count} packets. Average latency: {avg_latency:.4f} ms")
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