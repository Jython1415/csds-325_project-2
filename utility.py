import socket, random, zlib, pickle

class UnreliableSocket:
    
    probabilityOfFailure = .3
    
    def __init__(self, ip = None, port = None):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.messageQueue = []
        self.delayedMessage = None
        self.connected = False
        
        self.address = (ip, port)
        if ip != None:
            self.bind()
    
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
        try:
            newMessage = self.socket.recvfrom(bufferSize, socket.MSG_DONTWAIT)
        except:
            newMessage = (None, None)
        (packetData, _) = newMessage
        if packetData != None: # <- check new data and append it to the queue
            self.messageQueue.append(newMessage)
        
        # If there is nothing in the queue
        if len(self.messageQueue) == 0:
            return (None, None)
        
        # Select a message
        currentMessage = self.messageQueue.pop(0)
        packet = pickle.loads(currentMessage[0])
    
        # Apply simulated failures
        if random.random() < UnreliableSocket.probabilityOfFailure:
            simulatedEvent = random.choice(["packet loss", "packet delay", "packet corruption"])  
                
            # Apply the selected event  
            match simulatedEvent:
                case "packet loss":
                    return (None, None)
                case "packet delay":
                    self.delayedMessage = currentMessage
                    return (None, None)
                case "packet corruption":
                    if packet.text != None: # If there is data to corrupt, corrupt it
                        encodedText = bytearray(packet.text, "utf-8")
                        selectedByte = random.randint(0, len(encodedText)-1)      # Select a byte to modify
                        encodedText[selectedByte] = encodedText[selectedByte] ^ 5 # Modify the byte
                        packet.text = encodedText.decode("utf-8")                 # Switch the data to the modified data

        # Reformat the object
        returnTuple = (packet, currentMessage[1])

        # Return the message
        return returnTuple
                    
    def sendto(self, packet, address):
        packet.packetHeader.address = self.socket.getsockname()
        data = pickle.dumps(packet)
        if len(data) > 1400:
            raise Exception(f"data size too big: {len(data)} > 1400")
        
        # if not self.connected:
        #     self.socket.connect(address)
        #     self.connected = True
        try:
            self.socket.send(data)
        except:
            self.socket.connect(address)
            self.socket.send(data)
    
    def close(self):
        self.socket.close()
        
class PacketHeader:
    
    def __init__(self, type, seq_num, length, checksum):
        self.type = type         # 0: START; 1: END; 2: DATA; 3: ACK
        self.seq_num = seq_num 
        self.length = length     # Length of data; 0 for ACK, START, and END packets
        self.checksum = checksum # 32-bit CRC
        self.address = None      # Sender socket address
        
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
        newPacket = Packet(None, None)
        newPacket.packetHeader = PacketHeader(0, seq_num, 0, newPacket.compute_checksum())
        return newPacket
    
    @classmethod
    def newEndPacket(cls, seq_num):
        newPacket = Packet(None, None)
        newPacket.packetHeader = PacketHeader(1, seq_num, 0, newPacket.compute_checksum())
        return newPacket

    @classmethod
    def newDataPacket(cls, seq_num, text):
        newPacket = Packet(None, text)
        newPacket.packetHeader = PacketHeader(2, seq_num, len(text), newPacket.compute_checksum())
        return newPacket
    
    @classmethod
    def newAckPacket(cls, seq_num):
        newPacket = Packet(None, None)
        newPacket.packetHeader = PacketHeader(3, seq_num, 0, newPacket.compute_checksum())
        return newPacket
    
    def compute_checksum(self) -> int:
        if self.text != None:
            return zlib.crc32(self.text.encode())
        else:
            return 0
    
    def verify_packet(self) -> bool:
        return self.packetHeader.checksum == self.compute_checksum()
    
    def __eq__(self, obj):
        if type(obj) != type(self):
            return False
        else:
            return self.packetHeader == obj.packetHeader and self.text == obj.text