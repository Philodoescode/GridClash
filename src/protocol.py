"""
This module contains the protocol definition for the GridClash project.

28-byte Header Format: !4sBBIIQHI
    - 4s: protocol_id (4 bytes, ASCII)
    - B: version (1 byte, uint8)
    - B: msg_type (1 byte, uint8)
    - I: snapshot_id (4 bytes, uint32, big-endian)
    - I: seq_num (4 bytes, uint32, big-endian)
    - Q: server_ts_ms (8 bytes, uint64, big-endian)
    - H: payload_len (2 bytes, uint16, big-endian)
    - I: checksum (4 bytes, uint32, big-endian)
    Total: 4+1+1+4+4+8+2+4 = 28 bytes
"""
import binascii
import struct
import time
from collections import namedtuple
from enum import IntEnum

PROTOCOL_ID = b"GCUP"
PROTOCOL_VERSION = 1
HEADER_FORMAT = "!4sBBIIQHI"  # using checksum CRC32
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 28 bytes


class MessageType(IntEnum):
    """Message types for the GridClash protocol."""
    SNAPSHOT = 0  # Server → Client (grid state/update)
    HEARTBEAT = 1  # Client → Server (keep-alive)
    CLIENT_INIT = 2  # Client → Server (register)
    SERVER_INIT_RESPONSE = 3  # Server → Client (confirm registration)


# used a namedtuple instead of class for simplicity
packet = namedtuple(
    'Packet',
    ['protocol_id', 'version', 'msg_type', 'snapshot_id', 'seq_num', 'server_timestamp', 'payload_len', 'checksum']
)


# modify the function to be this order: HEADER_FORMAT, PROTOCOL_ID, PROTOCOL_VERSION, msg_type, snapshot_id, seq_num, server_timestamp, payload_len, checksum
def create_header(msg_type, snapshot_id, seq_num, server_timestamp, payload_len, checksum=0):
    """Create packet header."""
    return struct.pack(
        HEADER_FORMAT,
        PROTOCOL_ID,
        PROTOCOL_VERSION,
        msg_type,
        snapshot_id,
        seq_num,
        server_timestamp,
        payload_len,
        checksum
    )


def parse_header(header_bytes):
    """Parse packet header."""
    return struct.unpack(HEADER_FORMAT, header_bytes)


def unpack_packet(data):
    """Unpack raw data into packet object with multiple verifications."""
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
        0  # checksum set to 0 for calculation
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


def pack_packet(msg_type, snapshot_id, seq_num, server_timestamp, payload):
    """Pack packet fields and payload into raw bytes."""
    payload_len = len(payload)
    temp_header = create_header(msg_type, snapshot_id, seq_num, server_timestamp, payload_len, 0)
    checksum = calculate_checksum(temp_header + payload)
    final_header = create_header(msg_type, snapshot_id, seq_num, server_timestamp, payload_len, checksum)
    return final_header + payload


def calculate_checksum(data):
    """Calculate CRC32 checksum."""
    return binascii.crc32(data) & 0xffffffff


def get_current_timestamp_ms():
    """Get current time in milliseconds since epoch."""
    return int(time.time() * 1000)
