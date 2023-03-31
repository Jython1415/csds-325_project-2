import random
import utility as Utility

class RDTSocket(Utility.UnreliableSocket):
    
    packetStringSize = 1000
    bufferSize = 2048
    
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
        (newSocket, address) = self.socket.accept()[0]
        self.socket = newSocket # This line is probably not necessary because the sockets are UDP sockets
        self.targetAddress = address
        
        while True:
            (recvPacket, _) = self.recv()
            if recvPacket.packetHeader.type == 0:
                self.receiverWindowPos = recvPacket.packetHeader.seq_num
                self.sendACK(recvPacket.packetHeader.seq_num)
                break
        
        return address

    # How the sender will connect with the receiver
    def connect(self, address):
        # Connect to the socket
        self.socket.connect(address)
        self.targetAddress = address
        
        # Send the START message and return the sequence number
        self.startSeqNum = random.randint(0, 2**30)
        self.sendto(Utility.Packet.newStartPacket(self.startSeqNum), self.targetAddress)
        return self.startSeqNum
    
    # Send ACK of seq_num
    def sendACK(self, seq_num):
        self.sendto(Utility.Packet.newAckPacket(seq_num), self.targetAddress)
    
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
        for packet in packetsToSend:
            self.senderPacketQueue.append(packet)
        packetsToSend.append(Utility.Packet.newEndPacket(self.startSeqNum + len(stringsToSend) + 1))
            
        # Initialize queues
        toSendQueue = list()
        sentQueue = list()

                
        ## Wait to receive an ACK
        while True:
            (recvPacket, _) = self.recv()
            if recvPacket.packetHeader.type == 3 and recvPacket.packetHeader.seq_num == self.startSeqNum:
                break
        
        ## Send the file
        while not self.senderPacketQueue.empty():
            # Add packets to the sending queue
            for packet in packetsToSend:
                if packet.packetHeader.seq_num < self.startSeqNum + self.senderWindowPos + self.senderWindowSize and packet not in toSendQueue and packet not in sentQueue:
                    toSendQueue.append(packet)
            
            # Send a packet (if there is a packet to send)
            if len(toSendQueue) > 0:
                packetToSend = toSendQueue.pop(0)
                self.sendto(packetToSend, self.targetAddress)
                sentQueue.append(packet)
                
            # Check for ACKs
            (recvPacket, _) = self.recv()
            if recvPacket != None and recvPacket.packetHeader.type == 3: # Check if is ACK
                seq_num = recvPacket.packetHeader.seq_num
                
                # Remove packet from queues
                for packet in packetsToSend:
                    if packet.packetHeader.seq_num < seq_num:
                        packetsToSend.remove(packet) # ! Only removes first instance and does not account for potential error
                        toSendQueue.remove(packet)
                        sentQueue.remove(packet)
                
                # Advance window if necessary
                if len(packetsToSend) > 0 and packetsToSend[0].packetHeader.seq_num > seq_num:
                    self.senderWindowPos = seq_num
        
        ## Close the connection
        self.close()
        print("Complete")
        
    
    # How the receiver and sender will receive messages from each other
    def recv(self):
        recvTuple = self.recvfrom(RDTSocket.bufferSize)
        (recvPacket, _) = recvTuple
        if recvPacket == None or not recvPacket.verifyPacket():
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
                seq_nums = list(buffer.keys()).sort()
                for num in seq_nums:
                    if num == self.receiverWindowPos:
                        self.receiverWindowPos += 1
                        if buffer[num].packetHeader.type == 2:
                            receivedFile += buffer.pop(num).text
                        elif buffer[num].packetHeader.type == 1:
                            buffer.clear()
                            gotEndPacket == True
                    else:
                        break
                
                # Send ACK
                self.sendACK(self.receiverWindowPos)                        
        
        ## Close the connections
        self.close()
        return receivedFile
    
    # How the server and client will close their connections
    def close(self):
        pass