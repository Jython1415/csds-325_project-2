import socket, random, zlib, pickle

class UnreliableSocket:
    
    probabilityOfFailure = .7
    
    def __init__(self, ip = None, port = None):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.messageQueue = []     # Used to store an internal list of packets for delaying and reordering them
        self.delayedMessage = None # Used to store a delayed message
        
        self.address = (ip, port)
        # Bind the socket if it has an address to bind to
        if ip != None:
            self.bind()
    
    # Used to bind the socket to a port
    def bind(self):
        self.socket.bind(self.address)
    
    # Returns the results in the format (Packet, address)
    # If there is nothing to return, it returns (None, None)
    def recvfrom(self, bufferSize):
        # Receive new data
        try:
            newMessage = self.socket.recvfrom(bufferSize, socket.MSG_DONTWAIT)
        except:
            newMessage = (None, None)
        (packetData, _) = newMessage
        if packetData != None:
            self.messageQueue.append(newMessage)
        
        # Handle delayed message (if there is one)
        if self.delayedMessage != None:
            self.messageQueue.append(self.delayedMessage)
            self.delayedMessage = None
        
        # If there is nothing in the queue, return nothing
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

        # Return the message
        returnTuple = (packet, currentMessage[1])
        return returnTuple
    
    # Used to send a packet       
    def sendto(self, packet, address):
        # Encode package
        packet.packetHeader.address = self.socket.getsockname()
        data = pickle.dumps(packet)
        # Check for packages that are too long
        if len(data) > 1400:
            raise Exception(f"data size too big: {len(data)} > 1400")
        
        # Send
        try:
            self.socket.send(data)
        except: # If there is an error, connect the socket first
            self.socket.connect(address)
            self.socket.send(data)
    
    # Close the socket
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
    
    @staticmethod
    def getSeqNum(packet) -> int:
        return packet.packetHeader.seq_num
    
    def compute_checksum(self) -> int:
        if self.text != None:
            return zlib.crc32(self.text.encode())
        else:
            return 0
    
    def verify_packet(self) -> bool:
        return self.packetHeader.checksum == self.compute_checksum()

    # Get the estimated size of the package when it will be sent
    def compressedSize(self) -> int:
        return len(pickle.dumps(self))
    
    def __eq__(self, obj):
        if type(obj) != type(self):
            return False
        else:
            return self.packetHeader == obj.packetHeader and self.text == obj.text
        
    # Used to see if the package is in the input list
    def isInList(self, list):
        found = False
        for obj in list:
            if obj == self:
                found = True
        return found

class Debug:
    
    # Fills in text will an input fill character to a certain length
    # The fill character is added to the left of the input text
    @staticmethod
    def leftFill(inputText, targetLength, fillCharacter = " ") -> str:
        if len(inputText) > targetLength:
            raise Exception(f"Debug.leftFill: Input text is too long\n{len(inputText)} > {targetLength}")
        else:
            return (fillCharacter * (targetLength - len(inputText))) + inputText
       
    # Fills in text will an input fill character to a certain length
    # The fill character is added to the right of the input text 
    @staticmethod
    def rightFill(inputText, targetLength, fillCharacter = " ") -> str:
        if len(inputText) > targetLength:
            raise Exception(f"Debug.leftFill: Input text is too long\n{len(inputText)} > {targetLength}")
        else:
            return inputText + (fillCharacter * (targetLength - len(inputText)))