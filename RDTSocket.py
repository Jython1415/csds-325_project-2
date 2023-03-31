import utility as Utility

class RDTSocket(Utility.UnreliableSocket):
    
    def __init__(self, ip, port):
        Utility.UnreliableSocket.__init__(self, ip, port) 
        self.sendAddress = None 
        
    def accept(self):
        (socket, address) = self.socket.accept()[0]
        self.socket = socket
        return address
    
    def connect(self, address):
        self.socket.connect(address)
        self.sendAddress = address
    
    def send(self, data):
        self.sendto(data, self.sendAddress)
    
    def recv(self):
        return self.recvfrom(2048)
    
    def close(self):
        self.close()