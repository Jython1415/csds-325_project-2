

class UnreliableSocket:
    
    def bind():
        print("bind")
    
    def recvfrom():
        print("recvfrom")
    
    def sendto():
        print("sendTo")
    
    def close():
        print("close")
        
class PacketHeader:
    
    def __init__(self, type, seq_num, length, checksum):
        self.type = type         # 0: START; 1: END; 2: DATA; 3: ACK
        self.seq_num = seq_num 
        self.length = length     # Length of data; 0 for ACK, START, and END packets
        self.checksum = checksum # 32-bit CRC

class Packet:
    
    def __init__(self, packetHeader, data):
        self.packetHeader = packetHeader
        self.data = data
    
    @classmethod
    def newDataPacket(cls, seq_num, data):
        packetHeader = PacketHeader(2, seq_num, len(data), Packet.compute_checksum(data))
        return cls(packetHeader, data)
    
    @staticmethod
    def compute_checksum() -> int:
        return 1
    
    def verify_packet(self) -> bool:
        return True