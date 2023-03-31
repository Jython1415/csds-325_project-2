import sys
from RDTSocket import RDTSocket

def main():
    # Read the file
    fileString = ""
    with open("alice.txt", "r") as f:
        fileString = "".join(f.readlines())
    
    # Set up the socket
    sendSocket = RDTSocket(int(sys.argv[3]))
    
    # Send the file
    sendSocket.send(fileString, (sys.argv[1], int(sys.argv[2])))
    
    # Complete
    print("File Sent")

if __name__ == "__main__":
    main()