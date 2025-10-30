import struct
import binascii

PROTOCOL_ID = b"GCUP"
PROTOCOL_VERSION = 1
HEADER_FORMAT = ">4sBBIIQHI" # using checksum CRC32
HEADER_SIZE = struct.calcsize(HEADER_FORMAT) # 28 bytes

# Message Types
MSG_GAME_STATE_UPDATE = 1
MSG_HEARTBEAT = 2
MSG_CLIENT_HELLO = 3
MSG_SERVER_HELLO = 4

def create_header(msg_type, msg_length, sequence_number, ack_number, checksum=0):
    return struct.pack(HEADER_FORMAT, PROTOCOL_ID, PROTOCOL_VERSION, msg_type,
                       msg_length, sequence_number, ack_number, checksum)
def parse_header(header_bytes):
    return struct.unpack(HEADER_FORMAT, header_bytes)
def calculate_checksum(data):
    return binascii.crc32(data) & 0xffffffff
def verify_checksum(header_bytes, data):
    unpacked = parse_header(header_bytes)
    received_checksum = unpacked[6]
    temp_header = create_header(unpacked[2], unpacked[3], unpacked[4], unpacked[5], 0)
    computed_checksum = calculate_checksum(temp_header + data)
    return received_checksum == computed_checksum