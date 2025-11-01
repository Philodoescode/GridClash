import socket
serverName = '127.0.0.1'
serverPort = 12000
clientSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
message = input('Input message to be sent sentence: ')
clientSocket.sendto(message.encode('UTF-8'),(serverName, serverPort))
data, clientAddress = clientSocket.recvfrom(1200)
print (data.decode('UTF-8'))
clientSocket.close()


# TODO: define heartbeat interval to be sent to the server

# dunctions

# TODO: implement send_hello function : will INIT the connection handshake with the server
# TODO: implement send_heartbeat function : will send a periodic message to keep the connection alive
# TODO: implement parse_game_state_update function : will decode the payload of a state update (msg_type_state_update) packet
# TODO: implement handle_server_hello function : will process the server's response to our initial HELLO. get the player id
# TODO: implement render_game function : will update the current game state. probably will be just print outs at this phase

def main():
    pass
# TODO: init the socket(like above)
# TODO: send periodic heartbeat
# TODO: render game state