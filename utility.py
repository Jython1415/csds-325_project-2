import socket, random, zlib, pickle

class UnreliableSocket:
    
    probabilityOfFailure = .3
    
    def __init__(self, ip, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = (ip, port)
        self.messageQueue = []
        self.delayedMessage = None
    
    def bind(self):
        self.socket.bind(self.address)
    
    # Returns the results in the format (Packet, address)
    # If there is nothing to return, it returns (None, None)
    def recvfrom(self, bufferSize):
        # Handle delayed message (if there is one)
        if self.delayedMessage != None:
            self.messageQueue.append(self.delayedMessage)
            self.delayedMessage = None
        
        # Receive new data
        newMessage = self.socket.recvfrom(bufferSize, socket.MSG_DONTWAIT)
        (packetData, _) = newMessage
        if packetData != None: # <- check new data and append it to the queue
            self.messageQueue.append(newMessage)
        
        # If there is nothing in the queue
        if len(self.messageQueue) == 0:
            return (None, None)
        
        # Select a message
        currentMessage = self.messageQueue.pop(0)
    
        # Apply simulated failures
        if random.random() < UnreliableSocket.probabilityOfFailure:
            simulatedEvent = random.choice(["packet loss", "packet delay", "packet corruption"])  
                
            # Apply the selected event  
            match simulatedEvent:
                case "packet loss":
                    self.messageQueue.pop(0)
                    currentMessage = (None, None)
                case "packet delay":
                    self.delayedMessage = currentMessage
                    currentMessage = (None, None)
                case "packet corruption":
                    currentPacketData = currentMessage[0]                                 # Isolate the data
                    selectedByte = random.randint(0, len(currentPacketData)-1)            # Select a byte to modify
                    currentPacketData[selectedByte] = currentPacketData[selectedByte] ^ 5 # Modify the byte
                    currentMessage[0] = currentPacketData                                 # Switch the data to the modified data

        # Reformat the object
        returnTuple = (pickle.loads(currentMessage[0]), currentMessage[1])

        # Return the message
        return returnTuple
                    
    def sendto(self, packet, address):
        data = pickle.dumps(packet)
        if len(data) > 1400:
            raise Exception(f"data size too big: {len(data)} > 1400")
        return self.socket.sendto(data, address)
    
    def close(self):
        self.socket.close()
        
class PacketHeader:
    
    def __init__(self, type, seq_num, length, checksum):
        self.type = type         # 0: START; 1: END; 2: DATA; 3: ACK
        self.seq_num = seq_num 
        self.length = length     # Length of data; 0 for ACK, START, and END packets
        self.checksum = checksum # 32-bit CRC
        
    def __eq__(self, obj):
        if type(self) != type(obj):
            return False
        else:
            return self.type == obj.type and self.seq_num == obj.seq_num and self.length == obj.length and self.checksum == obj.checksum

class Packet:
    
    def __init__(self, packetHeader, text):
        self.packetHeader = packetHeader
        self.text = text
    
    @classmethod
    def newStartPacket(cls, seq_num):
        packetHeader = PacketHeader(0, seq_num, 0, Packet.compute_checksum())
        return cls(packetHeader, None)
    
    @classmethod
    def newEndPacket(cls, seq_num):
        packetHeader = PacketHeader(1, seq_num, 0, Packet.compute_checksum())
        return cls(packetHeader, None)

    @classmethod
    def newDataPacket(cls, seq_num, text):
        packetHeader = PacketHeader(2, seq_num, len(text), Packet.compute_checksum())
        return cls(packetHeader, text)
    
    @classmethod
    def newAckPacket(cls, seq_num):
        packetHeader = PacketHeader(3, seq_num, 0, Packet.compute_checksum())
        return cls(packetHeader, None)
    
    @staticmethod
    def compute_checksum(self) -> int:
        return zlib.crc32(pickle.dumps(self))
    
    def verify_packet(self) -> bool:
        return self.packetHeader.checksum == Packet.compute_checksum()
    
    def __eq__(self, obj):
        if type(obj) != type(self):
            return False
        else:
            return self.packetHeader == obj.packetHeader and self.text == obj.text