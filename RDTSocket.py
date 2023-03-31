import random
import utility as Utility

class RDTSocket(Utility.UnreliableSocket):
    
    packetStringSize = 1000
    bufferSize = 2048
    
    def __init__(self, ip, port, windowSize):
        Utility.UnreliableSocket.__init__(self, ip, port) 
        self.sendAddress = None 
        self.windowSize = windowSize # Window size
        self.windowPos = -1          # Window position tracks where the start of the window is. -1: not started; >1: working
        self.startSeqNum = -1        # -1 because it has not been set yet
        self.packetQueue = list()    # packetQueue holds the packets that have not yet been sent and ACKed
        
    # How the receiver will accept new connections
    def accept(self):
        (newSocket, address) = self.socket.accept()[0]
        self.socket = newSocket # This line is probably not necessary because the sockets are UDP sockets
        return address
    
    # How the sender will connect with the receiver
    def connect(self, address):
        # Connect to the socket
        self.socket.connect(address)
        self.sendAddress = address
        
        # Send the START message and return the sequence number
        self.startSeqNum = random.randint(0, 2**30)
        self.sendto(Utility.Packet.newStartPacket(self.startSeqNum), self.sendAddress)
        return self.startSeqNum
    
    # How the sender will send the file
    def send(self, fileString, address = None):
        ## Initialize
        self.windowPos = 1
        
        # Connect to the receiver
        if address == None:
            self.connect(self.sendAddress)
        else:
            self.connect(address)
            self.sendAddress = address
        
        # Split the file into strings shorter than RDTSocket.packetStringSize
        stringsToSend = [fileString[i:i+RDTSocket.packetStringSize] for i in range(0, len(fileString), RDTSocket.packetStringSize)]
        
        # Create packets and add them to the queue of packets to send
        packetsToSend = [Utility.Packet.newDataPacket(self.startSeqNum + i + 1, stringsToSend[i]) for i in range(len(stringsToSend))]
        for packet in packetsToSend:
            self.packetQueue.append(packet)
            
        # Initialize queues
        toSendQueue = list()
        sentQueue = list()
                
        ## Wait to receive an ACK
        while True:
            (recvPacket, _) = self.recv(RDTSocket.bufferSize)
            if recvPacket.packetHeader.type == 3 and recvPacket.packetHeader.seq_num == self.startSeqNum:
                break
        
        ## Send the file
        while not self.packetQueue.empty():
            # Add packets to the sending queue
            for packet in packetsToSend:
                if packet.packetHeader.seq_num < self.startSeqNum + self.windowPos + self.windowSize and packet not in toSendQueue and packet not in sentQueue:
                    toSendQueue.append(packet)
            
            # Send a packet (if there is a packet to send)
            if len(toSendQueue) > 0:
                packetToSend = toSendQueue.pop(0)
                self.sendto(packetToSend, self.sendAddress)
                sentQueue.append(packet)
                
            # Check for ACKs
            (recvPacket, _) = self.recv(RDTSocket.bufferSize)
            if recvPacket != None and recvPacket.packetHeader.type == 3: # Check if is ACK
                seq_num = recvPacket.packetHeader.seq_num
                
                # Remove packet from queues
                for packet in packetsToSend:
                    if packet.packetHeader.seq_num == seq_num:
                        packetsToSend.remove(packet) # ! Only removes first instance and does not account for potential error
                        toSendQueue.remove(packet)
                        sentQueue.remove(packet)
                
                # Advance window if necessary
                if len(packetsToSend) > 0 and packetsToSend[0].packetHeader.seq_num > seq_num:
                    self.windowPos = seq_num
        
        ## Close the connection
        finalSeqNum = random.randint(0, 2**30)
        self.sendto(Utility.Packet.newEndPacket(finalSeqNum))
        while True:
            (recvPacket, _) = self.recv(RDTSocket.bufferSize)
            if recvPacket != None and recvPacket.packetHeader.type == 3 and recvPacket.packetHeader.seq_num == finalSeqNum:
                print("Complete")
        
    
    # How the receiver and sender will receive messages from each other
    def recv(self):
        recvTuple = self.recvfrom(RDTSocket.bufferSize)
        (recvPacket, _) = recvTuple
        if recvPacket != None and recvPacket.packetHeader.checksum != recvPacket.compute_checksum():
            return (None, None)
        else:
            return recvTuple
    
    # 
    def recvFile(self):
        ## Wait for accept
        self.accept()
        
        ## 
        
    
    # How the server and client will close their connections
    def close(self):
        pass