import random, time
import utility as Utility

class RDTSocket(Utility.UnreliableSocket):
    
    packetStringSize = 100
    bufferSize = 2048
    waitTime = 5e8
    
    def __init__(self, windowSize, ip = None, port = None):
        Utility.UnreliableSocket.__init__(self, ip, port) 
        self.targetAddress = None            # Where to sends packets to
        
        self.senderWindowSize = windowSize # Window size
        self.senderWindowPos = -1          # Window position tracks where the start of the window is. -1: not started; >1: working
        self.startSeqNum = -1              # -1 because it has not been set yet
        self.senderPacketQueue = list()    # packetQueue holds the packets that have not yet been sent and ACKed
        
        self.receiverWindowSize = windowSize # Window size
        self.receiverWindowPos = -1          # Window position tracks the lower bound (inclusive) of the receiver window
                                             # -1: not started; >1: working        
        
    # How the receiver will accept new connections
    def accept(self):
        print(f"Waiting for START packet at {self.socket.getsockname()}...")
        
        # (newSocket, address) = self.socket.accept()[0]
        # self.socket = newSocket # This line is probably not necessary because the sockets are UDP sockets
        # self.targetAddress = address
        
        while True:
            (recvPacket, _) = self.recv()
            if recvPacket != None and recvPacket.packetHeader.type == 0:
                self.receiverWindowPos = recvPacket.packetHeader.seq_num + 1
                self.targetAddress = recvPacket.packetHeader.address
                self.sendACK(recvPacket.packetHeader.seq_num)
                break
        
        print(f"Connected to ({self.targetAddress[0]}, {self.targetAddress[1]})")
        
        return self.targetAddress

    # How the sender will connect with the receiver
    def connect(self, address):
        print(f"Connecting to ({address[0]}, {address[1]})")
        
        # Connect to the socket
        self.socket.connect(address)
        self.targetAddress = address
        
        # Set the START sequence number
        # self.startSeqNum = random.randint(0, 2**30)
        self.startSeqNum = 0
        
        # Send START and Wait until ACK
        receivedACK = False
        while not receivedACK:
            self.sendto(Utility.Packet.newStartPacket(self.startSeqNum), self.targetAddress)
            print(f"Sent START packet to {self.targetAddress}")
            
            startTime = time.time_ns()
            while time.time_ns() - startTime < RDTSocket.waitTime:
                (recvPacket, _) = self.recv()
                if recvPacket != None and recvPacket.packetHeader.type == 3 and recvPacket.packetHeader.seq_num == self.startSeqNum:
                    receivedACK = True
                    break
        
        print("START ACK received")
        return self.startSeqNum
    
    # Send ACK of seq_num
    def sendACK(self, seq_num):
        self.sendto(Utility.Packet.newAckPacket(seq_num), self.targetAddress)
        print(f"Sent ACK {seq_num}")
    
    # How the sender will send the file
    def send(self, fileString, address = None):        
        ## Initialize
        self.senderWindowPos = 1
        
        # Connect to the receiver (sends START message)
        if address == None:
            self.connect(self.targetAddress)
        else:
            self.connect(address)
            self.targetAddress = address
        
        # Split the file into strings shorter than RDTSocket.packetStringSize
        stringsToSend = [fileString[i:i+RDTSocket.packetStringSize] for i in range(0, len(fileString), RDTSocket.packetStringSize)]
        
        # Create packets and add them to the queue of packets to send
        packetsToSend = [Utility.Packet.newDataPacket(self.startSeqNum + i + 1, stringsToSend[i]) for i in range(len(stringsToSend))]
        # for packet in packetsToSend:
        #     self.senderPacketQueue.append(packet)
        packetsToSend.append(Utility.Packet.newEndPacket(self.startSeqNum + len(stringsToSend) + 1))
        print(f"# packets to send: {len(packetsToSend)}")
            
        # Initialize queues
        toSendQueue = list()
        sentQueue = list()
        
        ## Send the file
        startTime = time.time_ns()
        while len(packetsToSend) != 0:
            # Add packets to the sending queue
            for packet in packetsToSend:
                if packet.packetHeader.seq_num < self.startSeqNum + self.senderWindowPos + self.senderWindowSize and packet not in toSendQueue and packet not in sentQueue:
                    toSendQueue.append(packet)
            
            # Send a packet (if there is a packet to send)
            if len(toSendQueue) > 0:
                packetDict = {}
                for packet in toSendQueue:
                    packetDict[packet.packetHeader.seq_num] = packet
                keys = list(packetDict.keys())
                keys.sort()
                packetToSend = packetDict[keys[0]]
                toSendQueue.remove(packetToSend)
                self.sendto(packetToSend, self.targetAddress)
                print(f"Sent packet {packetToSend.packetHeader.seq_num}")
                sentQueue.append(packet)
                
            # Check for ACKs
            (recvPacket, _) = self.recv()
            if recvPacket != None and recvPacket.packetHeader.type == 3: # Check if is ACK
                seq_num = recvPacket.packetHeader.seq_num
                
                # Remove packet from queues
                for packet in packetsToSend:
                    if packet.packetHeader.seq_num < seq_num:
                        for l in [packetsToSend, toSendQueue, sentQueue]:
                            while True:
                                try:
                                    l.remove(packet)
                                except:
                                    break
                
                # Advance window if necessary
                if len(packetsToSend) > 0 and packetsToSend[0].packetHeader.seq_num > seq_num:
                    self.senderWindowPos = seq_num
                    startTime = time.time_ns()
            
            # Timeout
            if time.time_ns() - startTime > RDTSocket.waitTime:
                startTime = time.time_ns()
                if len(sentQueue) > 0:
                    toSendQueue.append(sentQueue.pop(0))
                else:
                    toSendQueue.append(packetsToSend[0])
        
        ## Close the connection
        self.close()
        print("Complete")
        
    
    # How the receiver and sender will receive messages from each other
    def recv(self):
        recvTuple = self.recvfrom(RDTSocket.bufferSize)
        (recvPacket, _) = recvTuple
        if recvPacket == None or not recvPacket.verify_packet():
            if recvPacket != None:
                print("Invalid packet received")
            return (None, None)
        else:
            return recvTuple
    
    # The entire process to receive a file from accepting a sender connection and closing the socket
    def recvFile(self):
        ## Wait for accept
        self.accept()
        
        ## Initialize file receiving
        buffer = {}
        receivedFile = ""
        
        ## Receive data packets
        gotEndPacket = False
        while not gotEndPacket:
            
            # Check for new packets
            (recvPacket, _) = self.recv()
            if recvPacket != None and (recvPacket.packetHeader.type == 1 or recvPacket.packetHeader.type == 2):
                seq_num = recvPacket.packetHeader.seq_num
                # See if packet is in window
                if seq_num >= self.receiverWindowPos and seq_num < self.receiverWindowPos + self.receiverWindowSize:
                    buffer[recvPacket.packetHeader.seq_num] = recvPacket
                elif seq_num < self.receiverWindowPos:
                    self.sendACK(self.receiverWindowPos)
                
                # Process buffer and advance window
                seq_nums = list(buffer.keys())
                seq_nums.sort()
                for num in seq_nums:
                    if num == self.receiverWindowPos:
                        print(f"Packet {num} processed: type {buffer[num].packetHeader.type}")
                        self.receiverWindowPos += 1
                        if buffer[num].packetHeader.type == 2:
                            receivedFile += buffer.pop(num).text
                        elif buffer[num].packetHeader.type == 1: # End packet check
                            buffer.clear()
                            gotEndPacket == True
                            for _ in range(10):
                                self.sendACK(self.receiverWindowPos)
                            self.close()
                            return receivedFile
                    else:
                        break
                
                # Send ACK
                self.sendACK(self.receiverWindowPos)                        
        
        ## Close the connections
        print("Closed connection")
        self.close()
        return receivedFile
    
    # How the server and client will close their connections
    def close(self):
        pass