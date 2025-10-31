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
        'socket': serverSocket
        # TODO: add initial pos later
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
    # each upadte should include:
        # seq_num
        # snapshot_id
        # sever_timestamp
    # TODO: implement payload calculation

    # send packets to all connected clients    
    for clientAddress, clientData in clients.items():
        # create and pack data for each client to be sent to each
        state_packet = pack_packet(MSG_GAME_STATE_UPDATE,  # noqa: F405
                                   snapshot_id,
                                   clientData['seq_num'],
                                   current_timestamp,
                                   # payload for pos
                                   )
        serverSocket.sendto(state_packet, clientAddress)
        clientData['seq_num'] += 1

def main():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.bind(('', SERVER_PORT))
    serverSocket.setblocking(0) # so the server does not get stuck waiting for recvfrom()
    print("Server is up and running.")

    # main server loop
    while 1:
        pass