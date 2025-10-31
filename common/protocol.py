import struct
import binascii
from collections import namedtuple

PROTOCOL_ID = b"GCUP"
PROTOCOL_VERSION = 1
HEADER_FORMAT = ">4sBBIIQHI" # using checksum CRC32
HEADER_SIZE = struct.calcsize(HEADER_FORMAT) # 28 bytes

# Message Types
MSG_GAME_STATE_UPDATE = 1
MSG_CLIENT_HEARTBEAT = 2
MSG_CLIENT_HELLO = 3
MSG_SERVER_HELLO = 4

# modify the function to be this order: HEADER_FORMAT, PROTOCOL_ID, PROTOCOL_VERSION, msg_type, snapshot_id, seq_num, server_timestamp, payload_len, checksum
def create_header(msg_type, snapshot_id, seq_num, server_timestamp, payload_len, checksum=0):
    return struct.pack(HEADER_FORMAT, PROTOCOL_ID, PROTOCOL_VERSION, msg_type, snapshot_id, seq_num, server_timestamp, payload_len, checksum)
def parse_header(header_bytes):
    return struct.unpack(HEADER_FORMAT, header_bytes)

# used a namedtuple instead of class for simplicity
packet = namedtuple('Packet', ['protocol_id', 'version', 'msg_type', 'snapshot_id', 'seq_num', 'server_timestamp', 'payload_len', 'checksum'])

# unpack_packet function. it unpack raw data into packet object. and do multiple verifications
def unpack_packet(data):
    # check for minimum length
    if len(data) < HEADER_SIZE:
        raise ValueError("Incomplete packet")

    # extract header and payload
    header_bytes = data[:HEADER_SIZE]
    payload = data[HEADER_SIZE:]
    
    unpacked_header = parse_header(header_bytes)
    
    payload_len = unpacked_header[6]
    received_checksum = unpacked_header[7]

    # verify payload length matches the length in header
    if len(payload) != payload_len:
        raise ValueError("Payload length mismatch")
    
    # verify protocol ID
    if unpacked_header[0] != PROTOCOL_ID:
        raise ValueError("Invalid Protocol ID")
    
    # verify protocol version
    if unpacked_header[1] != PROTOCOL_VERSION:
        raise ValueError("Unsupported Protocol Version")

    # verify checksum
    temp_header = create_header(
        unpacked_header[2],  # msg_type
        unpacked_header[3],  # snapshot_id
        unpacked_header[4],  # seq_num
        unpacked_header[5],  # server_timestamp
        unpacked_header[6],  # payload_len
        0                    # checksum set to 0 for calculation
    )
    calculated_checksum = calculate_checksum(temp_header + payload)
    if calculated_checksum != received_checksum:
        raise ValueError("Checksum mismatch")

    # create packet object from unpacked data and return with payload
    pkt = packet(
        protocol_id=unpacked_header[0],
        version=unpacked_header[1],
        msg_type=unpacked_header[2],
        snapshot_id=unpacked_header[3],
        seq_num=unpacked_header[4],
        server_timestamp=unpacked_header[5],
        payload_len=unpacked_header[6],
        checksum=unpacked_header[7]
    )
    return pkt, payload


# pack_packet function. it pack packet fields and payload into raw bytes
def pack_packet(msg_type, snapshot_id, seq_num, server_timestamp, payload):
    payload_len = len(payload)
    temp_header = create_header(msg_type, snapshot_id, seq_num, server_timestamp, payload_len, 0)
    checksum = calculate_checksum(temp_header + payload)
    final_header = create_header(msg_type, snapshot_id, seq_num, server_timestamp, payload_len, checksum)
    return final_header + payload


def calculate_checksum(data):
    return binascii.crc32(data) & 0xffffffff