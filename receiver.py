import sys
from RDTSocket import RDTSocket

localIP = "127.0.0.1"

def main():
    # Set up the socket
    recvSocket = RDTSocket(int(sys.argv[2]), localIP, int(sys.argv[1]))
    
    # Receive the file
    fileString = recvSocket.recvFile()
    
    # Export the contents
    with open("download.txt", "w") as f:
        f.write(fileString)
    
    # Complete
    print("File downloaded")
    
if __name__ == "__main__":
    main()