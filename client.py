import socket
serverName = '127.0.0.1'
serverPort = 12000
clientSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
message = input('Input message to be sent sentence: ')
clientSocket.sendto(message.encode('UTF-8'),(serverName, serverPort))
data, clientAddress = clientSocket.recvfrom(2048)
print (data.decode('UTF-8'))
clientSocket.close()