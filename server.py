import socket
from common.protocol import *  # noqa: F403
import struct
import time
serverPort = 12000
CLIENT_COUNT = 4
HEARTBEAT_TIMEOUT = 10  # seconds
FREQUENCY_RATE = 10  # Hz
server_timestamp = int(time.time())
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSocket.bind(('', serverPort))
# client dictionary to manage connected clients
clients = {}
print ("The server is ready to receive")
while 1:
	data, clientAddress = serverSocket.recvfrom(2048)
	message=data.decode("UTF-8")
	print (message)
	modifiedMessage = message.upper()
	serverSocket.sendto(modifiedMessage.encode("UTF-8"), clientAddress)
	#unpack header
	header, payload = unpack_packet(data)