import socket
serverName = '127.0.0.1'
serverPort = 12000
clientSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
message = input('Input message to be sent sentence: ')
clientSocket.sendto(message.encode('UTF-8'),(serverName, serverPort))
data, clientAddress = clientSocket.recvfrom(2048)
print (data.decode('UTF-8'))
clientSocket.close()

# 3.1. Task: Basic UDP Socket and INIT Handshake

#     Create a UDP socket.
#     On startup, pack and send a CLIENT_HELLO packet to the server's address.
#     Wait for a SERVER_WELCOME response. Once received, store the assigned player_id and consider the client "connected".

# 3.2. Task: Implement Receiver Loop

#     Create a dedicated thread to listen for incoming server packets. This prevents the main application from blocking.
#     The loop will:
#         Call sock.recvfrom().
#         When a packet is received, unpack the header.
#         Validate protocol_id and version.
#         Check msg_type. If it's STATE_UPDATE, proceed to the next step.

# 3.3. Task: Implement DATA Processing Logic

#     Maintain a variable: last_processed_snapshot_id = 0.
#     When a STATE_UPDATE packet is received:
#         Read the snapshot_id from the header.
#         Discard Outdated Packets: If snapshot_id <= last_processed_snapshot_id, print a log message ("Discarding outdated snapshot") and ignore the packet.
#         If the packet is new, update last_processed_snapshot_id = snapshot_id.
#         Parse Payload: Unpack the payload data to retrieve the list of player positions.
#         Display State: For this prototype, simply print the received state to the console in a clean format (e.g., "Snapshot #ID | Player 1 at (x,y), Player 2 at (x,y)").

# 3.4. Task: Implement Heartbeat
#     In the client's main loop (not the receiver thread), send a CLIENT_HEARTBEAT packet to the server every few seconds (e.g., every 2 seconds) to signal that the client is still active.