import socket, random, zlib

class UnreliableSocket:
    
    probabilityOfFailure = .3
    
    def __init__(self, ip, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = (ip, port)
        self.messageQueue = []
        self.delayedMessage = None
    
    def bind(self):
        self.socket.bind(self.address)
    
    def recvfrom(self, bufferSize):
        # Handle delayed message (if there is one)
        if self.delayedMessage != None:
            self.messageQueue.append(self.delayedMessage)
            self.delayedMessage = None
        
        # Receive new data
        newMessage = self.socket.recvfrom(bufferSize, socket.MSG_DONTWAIT)
        (data, address) = newMessage
        if data != None: # <- check new data and append it to the queue
            self.messageQueue.append(newMessage)
        
        # If there is nothing in the queue
        if len(self.messageQueue) == 0:
            return (0, None)
        
        # Select a message
        currentMessage = self.messageQueue.pop(0)
    
        # Apply simulated failures
        if random.random() < UnreliableSocket.probabilityOfFailure:
            simulatedEvent = random.choice(["packet loss", "packet delay", "packet corruption"])  
                
            # Apply the selected event  
            match simulatedEvent:
                case "packet loss":
                    self.messageQueue.pop(0)
                    currentMessage = (0, None)
                case "packet delay":
                    self.delayedMessage = currentMessage
                    currentMessage = (0, None)
                case "packet corruption":
                    currentData = currentMessage[0]                           # Isolate the data
                    selectedByte = random.randint(0, len(currentData)-1)      # Select a byte to modify
                    currentData[selectedByte] = currentData[selectedByte] ^ 5 # Modify the byte
                    currentMessage[0] = currentData                           # Switch the data to the modified data

        # Return the message
        return currentMessage
                    
    def sendto(self, data, address):
        return self.socket.sendto(data, address)
    
    def close(self):
        self.socket.close()
        
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
    def newStartPacket(cls, seq_num, data):
        packetHeader = PacketHeader(0, seq_num, len(data), Packet.compute_checksum(data))
        return cls(packetHeader, data)
    
    @classmethod
    def newEndPacket(cls, seq_num, data):
        packetHeader = PacketHeader(1, seq_num, len(data), Packet.compute_checksum(data))
        return cls(packetHeader, data)

    @classmethod
    def newDataPacket(cls, seq_num, data):
        packetHeader = PacketHeader(2, seq_num, len(data), Packet.compute_checksum(data))
        return cls(packetHeader, data)
    
    @classmethod
    def newAckPacket(cls, seq_num, data):
        packetHeader = PacketHeader(3, seq_num, len(data), Packet.compute_checksum(data))
        return cls(packetHeader, data)
    
    @staticmethod
    def compute_checksum(data) -> int:
        return zlib.crc32(data)
    
    def verify_packet(self) -> bool:
        return self.packetHeader.checksum == Packet.compute_checksum(self.data)