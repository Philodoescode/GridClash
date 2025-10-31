import socket
from common.protocol import *  # noqa: F403
import struct
import time

# The server must:
# Broadcast periodic snapshots to all connected clients.
# Maintain per-client state (sequence tracking, last acknowledged snapshot).
# Support 4 concurrent clients without exceeding CPU limits.
# Send additional redundant or delta updates to improve reliability. (will be implemented later in phase 2)
# Log performance metrics (CPU usage, update frequency, packet counts)

# configurations
SERVER_PORT = 12000
MAX_CLIENTS = 4
HEARTBEAT_TIMEOUT = 10  # seconds
BROADCAST_FREQUENCY = 20  # hz
MAX_PACKET_SIZE = 1200

clients = {}
next_player_id = 0
snapshot_id = 0

# INIT handshake
def handle_client_hello(clientAddress, serverSocket):
    global next_player_id

    # checks if player is already connected
    if clientAddress in clients:
        print(f"{clientAddress} already connected.")
        return
    
    # check if server is full
    if len(clients) >= MAX_CLIENTS:
        print(f"Server full. connection failed with {clientAddress}")
        return
    
    # add the new client
    player_id = next_player_id
    clients[clientAddress] = {
        'player_id': player_id,
        'seq_num': 0,
        'last_heartbeat': time.time(),
        'pos': (10 * (player_id + 1), 10 * (player_id + 1)) # just a placeholder
    }
    next_player_id += 1
    print(f"{clientAddress} connected. player_id {player_id}")
    
    # respond with server hello message
    payload = struct.pack('!B', player_id) # as max is 4
    response_packet = pack_packet(MSG_SERVER_HELLO, 0, 0, time.time(), payload)  # noqa: F405
    serverSocket.sendto(response_packet, clientAddress)

# updating client heartbeat
def handle_client_heartbeat(clientAddress):
    if clientAddress in clients:
        clients[clientAddress]['last_heartbeat'] = time.time()

# timeout handling
def handle_timeout():
    current_time = time.time()
    timed_out_clients = []
    for clientAddress, clientData in clients.items():
        if current_time - clientData['last_heartbeat'] > HEARTBEAT_TIMEOUT:
            timed_out_clients.append(clientAddress)

    # remove timed out clients    
    for clientAddress in timed_out_clients:
        print(f"{clientAddress} timed out")
        del clients[clientAddress]


# DATA broadcast
def state_broadcast(serverSocket):
    global snapshot_id
    if not clients:
        return
    snapshot_id += 1
    current_timestamp = time.time()
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
    num_players = len(clients)
    payload = struct.pack('!B', num_players)
    for clientData in clients.values():
        player_id = clientData['player_id']
        posx, posy = clientData['pos']
        payload += struct.pack('!Bii', player_id, posx, posy)
    


    # send packets to all connected clients    
    for clientAddress, clientData in clients.items():
        clientData['seq_num'] += 1
        packet = pack_packet(MSG_GAME_STATE_UPDATE, snapshot_id, clientData['seq_num'], current_timestamp, payload)  # noqa: F405
        serverSocket.sendto(packet, clientAddress)

def main():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.bind(('', SERVER_PORT))
    serverSocket.setblocking(0) # so the server does not get stuck waiting for recvfrom()
    print("Server is up and running.")

    last_broadcast_time = time.time()
    last_timeout_check = time.time()
    broadcast_interval = 1.0 / BROADCAST_FREQUENCY


    # main server loop
    while 1:
        try:
            try:
                data, clientAdress = serverSocket.recvfrom(MAX_PACKET_SIZE)
                pkt, payload = unpack_packet(data) #noqa: F405
                if pkt.msg_type == MSG_CLIENT_HELLO:  # noqa: F405
                    handle_client_hello(clientAdress, serverSocket)
                elif pkt.msg_type == MSG_CLIENT_HEARTBEAT:  # noqa: F405
                    handle_client_heartbeat(clientAdress)
            
            except socket.error:
                pass
            except ValueError as e:
                print(f"Error: {e}")
                continue

            current_time = time.time()

            # brodacast at the configured freq
            if current_time - last_broadcast_time >= broadcast_interval:
                state_broadcast(serverSocket)
                last_broadcast_time = current_time
            
            # checking timeouts periodically (currently once every sec)
            if current_time - last_timeout_check >= 1.0:
                handle_timeout()
                last_timeout_check = current_time
            
            # somehow this prevents 100% usage of cpu based on ai response
            time.sleep(0.001)
            
        except KeyboardInterrupt:
            print("Server shutting down.")
            break
        except Exception as e:
            print(f"Error: {e}")
            break
        
    serverSocket.close()

if __name__ == "__main__":
    main()