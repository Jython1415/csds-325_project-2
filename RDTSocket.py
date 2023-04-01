import time, random
import utility as Utility

class RDTSocket(Utility.UnreliableSocket):
    
    packetStringSize = 100 # How long each string in the packet is. Can be adjusted but an exception will be thrown if it is set too large
    bufferSize = 2048      # How large the buffer is when receiving packets
    waitTime = 5e8         # How long (in ns) to wait before retransmitting. Currently set to 500 ms
    
    def __init__(self, windowSize, ip = None, port = None):
        Utility.UnreliableSocket.__init__(self, ip, port) 
        self.targetAddress = None            # Where to sends packets to
        self.startSeqNum = -1                # -1 because it has not been set yet
        
        self.senderWindowSize = windowSize   # Window size
        self.senderWindowPos = -1            # Window position tracks where the start of the window is. -1: not started; >1: working
        
        self.receiverWindowSize = windowSize # Window size
        self.receiverWindowPos = -1          # Window position tracks the lower bound (inclusive) of the receiver window
                                             # -1: not started; >1: working        
        
    # How the receiver will accept new connections
    def accept(self):
        print(f"Waiting for START packet at {self.socket.getsockname()}...")
                
        while True:
            (recvPacket, _) = self.recv()
            if recvPacket != None and recvPacket.packetHeader.type == 0:     # Check packet == START packet
                self.receiverWindowPos = recvPacket.packetHeader.seq_num + 1 # Set the window position to the next expected packet
                self.startSeqNum = recvPacket.packetHeader.seq_num           # Save the start sequence number for later use
                self.targetAddress = recvPacket.packetHeader.address         # Save the target address
                self.sendACK(recvPacket.packetHeader.seq_num)                # Send ACK to start receiving the message
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
        self.startSeqNum = random.randint(0, 2**30)
        
        # Send START and Wait until ACK
        receivedACK = False
        while not receivedACK:
            # Send START message
            self.sendto(Utility.Packet.newStartPacket(self.startSeqNum), self.targetAddress)
            print(f"Sent START packet to {self.targetAddress}")
            
            # Wait for message; retransmit start if ACK is not received in time
            startTime = time.time_ns()
            while time.time_ns() - startTime < RDTSocket.waitTime:
                (recvPacket, _) = self.recv()
                
                # Check for ACK; if received, move on
                if recvPacket != None and recvPacket.packetHeader.type == 3 and recvPacket.packetHeader.seq_num == self.startSeqNum:
                    receivedACK = True
                    break
        
        print("START ACK received")
        return self.startSeqNum
    
    # Send ACK of seq_num
    def sendACK(self, seq_num):
        self.sendto(Utility.Packet.newAckPacket(seq_num), self.targetAddress)
        print("Sent ACK" + str(seq_num - self.startSeqNum).zfill(4))
    
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
        # Add the end packet
        packetsToSend.append(Utility.Packet.newEndPacket(self.startSeqNum + len(stringsToSend) + 1))
        print(f"# packets to send: {len(packetsToSend)}\n")
        
        # Initialize queues
        toSendQueue = list()
        sentQueue = list()
        
        ## Send the file
        startTime = time.time_ns()
        while len(packetsToSend) != 0:
            # Add packets to the sending queue
            for packet in packetsToSend:
                if packet.packetHeader.seq_num < self.startSeqNum + self.senderWindowPos + self.senderWindowSize and not packet.isInList(toSendQueue) and not packet.isInList(sentQueue):
                    toSendQueue.append(packet)
            
            # Send a packet (if there is a packet to send)
            if len(toSendQueue) > 0:
                # Select the packet with the smallest sequence number in toSendQueue
                toSendQueue.sort(key = Utility.Packet.getSeqNum)
                packetToSend = toSendQueue.pop(0)
                
                # Send the packet
                self.sendto(packetToSend, self.targetAddress)
                sentQueue.append(packetToSend)
                print("Sent P" + str(packetToSend.packetHeader.seq_num - self.startSeqNum).zfill(4) + " Size: " + str(packetToSend.compressedSize()).zfill(5))
                
            # Check for ACKs
            (recvPacket, _) = self.recv()
            if recvPacket != None and recvPacket.packetHeader.type == 3: # Check if it is ACK
                seq_num = recvPacket.packetHeader.seq_num
                print("Received ACK" + str(seq_num - self.startSeqNum).zfill(4))
                
                # Remove packet from queues
                for packet in packetsToSend:                              # For every packet that has not been ACKed
                    if packet.packetHeader.seq_num < seq_num:             # If the sequence number of that packet is less than the ACK number
                        for l in [packetsToSend, toSendQueue, sentQueue]: # Remove that packet from every list used to store packets in the sending process
                            while True: # Removes all duplicates from the queues
                                try:
                                    l.remove(packet)
                                except:
                                    break # The loop continues until the remove functions raises an exception
                
                # Advance window if necessary
                if seq_num > self.startSeqNum + self.senderWindowPos:
                    self.senderWindowPos = seq_num - self.startSeqNum
                    startTime = time.time_ns() # Reset the timer when the window advances
            
            # Timeout
            if time.time_ns() - startTime > RDTSocket.waitTime:
                print(f"Timeout: {len(sentQueue)} scheduled to be retransmitted\n\t" + str([i.packetHeader.seq_num - self.startSeqNum for i in sentQueue]))
                startTime = time.time_ns()
                toSendQueue.extend(sentQueue) # Send all "sent" packets back to the "send" queue
                sentQueue.clear()             # Clear the "sent" queue
        
        ## Close the connection
        self.close()
        print("Complete")
        
    # How the receiver and sender will receive messages from each other
    # This is where packets are verified
    def recv(self):
        recvTuple = self.recvfrom(RDTSocket.bufferSize)
        (recvPacket, _) = recvTuple
        if recvPacket == None or not recvPacket.verify_packet():
            if recvPacket != None:
                print("Invalid packet received")
            return (None, None)
        else:
            return recvTuple
    
    # How the recvFile function closes the connection
    def recvFile_closeConnection(self):
        # Send initial ACK
        self.sendACK(self.receiverWindowPos)
        
        # Make sure the ACK has been received
        # Wait 10 * default wait time to make sure the END message is not being re-sent
        startTime = time.time_ns()
        while time.time_ns() - startTime < RDTSocket.waitTime * 10:            
            (recvPacket, _) = self.recv()
            if recvPacket != None and recvPacket.packetHeader.type == 1 and recvPacket.packetHeader.seq_num == self.receiverWindowPos - 1:
                startTime = time.time_ns()
                self.sendACK(self.receiverWindowPos)
        
        # Close
        self.close()
        print("Closed connection")
    
    # The entire process to receive a file from accepting a sender connection and closing the socket
    def recvFile(self):
        ## Wait for accept
        self.accept()
        
        ## Initialize file receiving
        buffer = {}
        receivedFile = ""
        
        ## Receive data packets
        while True:
            
            # Check for new packets
            (recvPacket, _) = self.recv()
            if recvPacket != None and (recvPacket.packetHeader.type == 1 or recvPacket.packetHeader.type == 2 or recvPacket.packetHeader.type == 0):
                seq_num = recvPacket.packetHeader.seq_num
                print("Received P" + str(seq_num - self.startSeqNum).zfill(4) + f" Type: {recvPacket.packetHeader.type}")
                
                # Check start condition
                if recvPacket.packetHeader.type == 0 and recvPacket.packetHeader.seq_num == self.startSeqNum and self.receiverWindowPos == self.startSeqNum + 1:
                    self.sendACK(recvPacket.packetHeader.seq_num)
                
                # Check end condition
                if recvPacket.packetHeader.type == 1 and self.receiverWindowPos == seq_num:
                    self.receiverWindowPos += 1
                    self.recvFile_closeConnection()
                    return receivedFile
                
                # See if packet is in window
                if seq_num >= self.receiverWindowPos - 1 and seq_num < self.receiverWindowPos + self.receiverWindowSize: # If yes
                    buffer[recvPacket.packetHeader.seq_num] = recvPacket                                                 # Add to buffer
                elif seq_num < self.receiverWindowPos:   # If no
                    self.sendACK(self.receiverWindowPos) # Send ACK to indicate expected packet
                
                # Process buffer and advance window
                seq_nums = list(buffer.keys())
                seq_nums.sort()
                print([i - self.startSeqNum for i in seq_nums])
                for num in seq_nums:                               # Process the packets in order of increasing sequence number
                    if num < self.receiverWindowPos:               # If there are old packets in the buffer
                        buffer.pop(num)                            #     Remove them
                    elif num == self.receiverWindowPos:            # If the packet is the next packet expected
                        self.receiverWindowPos += 1                #     Advance window pos 1
                        if buffer[num].packetHeader.type == 1:     #     If end condition
                            self.recvFile_closeConnection()        #         End connection
                            return receivedFile                    #         Return file contents
                        else:                                      #     Else
                            receivedFile += buffer.pop(num).text   #         Add the packet contents to the file contents
                            print(f"Processed P" + str(num - self.startSeqNum).zfill(4) + "; Window advanced")
                    else:
                        print("Can't process further. Waiting on P" + str(self.receiverWindowPos - self.startSeqNum).zfill(4) + ". Lowest in buffer is P" + str(num - self.startSeqNum).zfill(4))
                        break # If there is a missing packet, stop processing and wait for more packets to come in
                
                # Send ACK
                self.sendACK(self.receiverWindowPos)
    
    # How the server and client will close their connections
    def close(self):
        pass