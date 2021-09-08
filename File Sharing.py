#!/usr/bin/env python3

########################################################################
#
# GET File Transfer
#
# When the client connects to the server, it immediately sends a
# 1-byte GET command followed by the requested filename. The server
# checks for the GET and then transmits the file. The file transfer
# from the server is prepended by an 8 byte file size field. These
# formats are shown below.
#
# The server needs to have REMOTE_FILE_NAME defined as a text file
# that the client can request. The client will store the downloaded
# file using the filename LOCAL_FILE_NAME. This is so that you can run
# a server and client from the same directory without overwriting
# files.
#
########################################################################

import socket
import argparse
import sys
import time
import datetime
import os


########################################################################

# Define all of the packet protocol field lengths. See the
# corresponding packet formats below.
CMD_FIELD_LEN = 1 # 1 byte commands sent from the client.
FILE_SIZE_FIELD_LEN  = 8 # 8 byte file size field.

# Packet format when a GET command is sent from a client, asking for a
# file download:

# -------------------------------------------
# | 1 byte GET command  | ... file name ... |
# -------------------------------------------

# When a GET command is received by the server, it reads the file name
# then replies with the following response:

# -----------------------------------
# | 8 byte file size | ... file ... |
# -----------------------------------

# Define a dictionary of commands. The actual command field value must
# be a 1-byte integer. For now, we only define the "GET" command,
# which tells the server to send a file.

CMD = { "GET" : 1,
        "PUT" : 2,
        "LIST": 3,
        "BYE" : 4}

MSG_ENCODING = "utf-8"
  
########################################################################
# SERVER
########################################################################

class Server:

    HOSTNAME = "127.0.0.1"

    ALL_IF_ADDRESS = "0.0.0.0"
    SERVICE_SCAN_PORT = 30000
    ADDRESS_PORT = (ALL_IF_ADDRESS, SERVICE_SCAN_PORT)

    SCAN_CMD = "SCAN"
    SCAN_CMD_ENCODED = SCAN_CMD.encode(MSG_ENCODING)
    
    MSG = "Thananjai and Winky's Sharing Service"
    MSG_ENCODED = MSG.encode(MSG_ENCODING)

    PORT = 50000
    RECV_SIZE = 1024
    BACKLOG = 10

    
    FILE_NOT_FOUND_MSG = "Error: Requested file is not available!"

    # This is the file that the client will request using a GET.
    REMOTE_FILE_NAME = "Test_1.txt"

    def __init__(self):
        self.thread_list = []
        self.tcp_udp_thread_list = []
        
        arr = os.listdir()
        print(arr)
        
        self.create_listen_socket()
        self.process_connections_forever()  

    def create_listen_socket(self):
        try:
            # Create an IPv4 UDP socket.
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Get socket layer socket options.
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind socket to socket address, i.e., IP address and port.
            self.udp_socket.bind((Server.ALL_IF_ADDRESS, Server.SERVICE_SCAN_PORT))
        except Exception as msg:
            print(msg)
            sys.exit(1)
        try:
            # Create the TCP server listen socket in the usual way.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((Server.HOSTNAME, Server.PORT))
            self.socket.listen(Server.BACKLOG)
            print("Listening on port {} ...".format(Server.PORT))
        except Exception as msg:
            print(msg)
            exit()
            
    def check_udp(self):
        print(Server.MSG, "listening on port {} ...".format(Server.SERVICE_SCAN_PORT))
        recvd_bytes, address_udp = self.udp_socket.recvfrom(Server.RECV_SIZE)

        print("Received: ", recvd_bytes.decode('utf-8'), " Address:", address_udp)
            
        # Decode the received bytes back into strings.
        recvd_str = recvd_bytes.decode(MSG_ENCODING)
                
        # Check if the received packet contains a service scan
        # command.
        if Server.SCAN_CMD in recvd_str:
            # Send the service advertisement message back to
            # the client.
            self.udp_socket.sendto(Server.MSG_ENCODED, address_udp)
        print("SCANNED")

    def check_tcp(self):
        new_client = self.socket.accept()
        print("Connection received")
                
        # A new client has connected. Create a new thread and
        # have it process the client using the connection
        # handler function.
        new_thread = threading.Thread(target=self.connection_handler,
                                      args=(new_client,))

        # Record the new thread.
        self.thread_list.append(new_thread)

        # Start the new thread running.
        print("Starting serving thread: ", new_thread.name)
        new_thread.daemon = True
        new_thread.start()
        print("TCP Connection")
                
    def process_connections_forever(self):
        try:
            #Create pool for parallel processing
            pool = multiprocessing.Pool()

            #In While loop call both UDP and TCP connection functions at the same time
            while True:
                pool.apply_async(self.check_udp)
                pool.apply_async(self.check_tcp)
            pool.close()
            pool.join()
                
                #print("LOOPING")
        except Exception as msg:
            print(msg)
        except KeyboardInterrupt:
            print()
        finally:
            print("Closing server socket ...")
            self.socket.close()
            sys.exit(1)

    def connection_handler(self, client):
        while True:
            connection, address = client
            print("-" * 72)

            #receive TCP connection
            print("Connection received from {}.".format(address))
            recvd_bytes = connection.recv(CMD_FIELD_LEN)
            cmd = int.from_bytes(recvd_bytes, byteorder='big')

            #Call function based on TCP CMD Message
            if cmd == CMD["GET"]:
                self.get_function(connection)
            elif cmd == CMD["PUT"]:
                self.put_function(connection)
            elif cmd == CMD["LIST"]:
                self.list_function(connection)
            elif cmd == CMD["BYE"]:
                print("Closing client connection ... ")
                connection.close()
            else:
                if len(recvd_bytes) == 0:
                    print("Closing client connection ... ")
                    connection.close()
                    break

                # Decode the received bytes back into strings. Then output
                # them.
                recvd_str = "Done"
                print("Received: ", recvd_str)

                send_bytes =recvd_str.encode(MSG_ENCODING)
                # Send the received bytes back to the client.
                connection.sendall(send_bytes)
                print("Sent: ", recvd_str)

    def get_function(self, connection):
        print("get")
        # The command is good. Now read and decode the requested
        # filename.
        filename_bytes = connection.recv(Server.RECV_SIZE)
        filename = filename_bytes.decode(MSG_ENCODING)

        # Open the requested file and get set to send it to the
        # client.
        try:
            file = open(filename, 'r').read()
        except FileNotFoundError:
            print(Server.FILE_NOT_FOUND_MSG)
            connection.close()                   
            return

        # Encode the file contents into bytes, record its size and
        # generate the file size field used for transmission.
        file_bytes = file.encode(MSG_ENCODING)
        file_size_bytes = len(file_bytes)
        file_size_field = file_size_bytes.to_bytes(FILE_SIZE_FIELD_LEN, byteorder='big')

        # Create the packet to be sent with the header field.
        pkt = file_size_field + file_bytes
        
        self.connection_send(pkt, connection)
        
    def socket_recv_size(self, length):
        bytes = self.socket.recv(length)
        if len(bytes) < length:
            self.socket.close()
            exit()
        return(bytes)
    
    def put_function(self, connection):
        print("put")
        # The command is good. Now read and decode the requested
        # filename.
        filename_bytes = connection.recv(Server.RECV_SIZE)
        filename = filename_bytes.decode(MSG_ENCODING)
        
        print(filename)
        
        ack = "PUT requestion received"
        ack_bytes = ack.encode(MSG_ENCODING)
        connection.sendall(ack_bytes)
        

        # Read the file size field.
        '''
        file_size_bytes = self.socket_recv_size(FILE_SIZE_FIELD_LEN)
        if len(file_size_bytes) == 0:
               self.socket.close()
               return
        '''

        # Make sure that you interpret it in host byte order.
        file_size = int.from_bytes(file_size_bytes, byteorder='big')

        # Receive the file itself.
        recvd_bytes_total = bytearray()
        try:
            # Keep doing recv until the entire file is downloaded. 
            while len(recvd_bytes_total) < file_size:
                recvd_bytes_total += self.socket.recv(Client.RECV_SIZE)

            # Create a file using the received filename and store the
            # data.
            print("Received {} bytes. Creating file: {}" \
                  .format(len(recvd_bytes_total), filename))

            with open(fname, 'w') as f:
                f.write(recvd_bytes_total.decode(MSG_ENCODING))
        except KeyboardInterrupt:
            print()
            exit(1)
        # If the socket has been closed by the server, break out
        # and close it on this end.
        except socket.error:
            self.socket.close()


    def list_function(self, connection):
        print("list")
        arr = os.listdir()
        package = ""
        for list in arr:
            package += list
            package += " "
        arr_bytes = package.encode(MSG_ENCODING)
        connection.sendall(arr_bytes)
        print("list sent")

    def connection_send(self, pkt, connection):
        try:
            # Send the packet to the connected client.
            connection.sendall(pkt)
            # print("Sent packet bytes: \n", pkt)
            print("Sending file: ", Server.REMOTE_FILE_NAME)
        except socket.error:
            # If the client has closed the connection, close the
            # socket on this end.
            print("Closing client connection ...")
            connection.close()
            return

########################################################################
# CLIENT
########################################################################

class Client:

    # Define the local file name where the downloaded file will be
    # saved.
    LOCAL_FILE_NAME = "Test_1.txt"
    # LOCAL_FILE_NAME = "bee1.jpg"
    
    RECV_SIZE = 1024
    MSG_ENCODING = "utf-8"    

    # for UDP connection
    BROADCAST_ADDRESS = "255.255.255.255"
    # BROADCAST_ADDRESS = "192.168.1.255"    
    SERVICE_PORT = 30000
    ADDRESS_PORT = (BROADCAST_ADDRESS, SERVICE_PORT)

    SCAN_CYCLES = 3
    SCAN_TIMEOUT = 5

    SCAN_CMD = "SCAN"
    SCAN_CMD_ENCODED = SCAN_CMD.encode(MSG_ENCODING)


    # for TCP connection
    TCP_ADDRESS = "127.0.0.1"
    TCP_PORT = 50000
    

    def __init__(self):
        self.get_socket()
        self.send_console_input_forever()

    def get_socket(self):
        try:
            # Create an IPv4 TCP socket.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Service discovery done using UDP packets.
            self.UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Arrange to send a broadcast service discovery packet.
            self.UDP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Set the socket for a socket.timeout if a scanning recv
            # fails.
            self.UDP_socket.settimeout(Client.SCAN_TIMEOUT);
            
            
        except Exception as msg:
            print(msg)
            sys.exit(1)
    
    def send_console_input_forever(self):
        while True:
            try:
                self.get_console_input()
                #self.connection_send()
                #print("Send Loop")
                #self.connection_receive()
            except (KeyboardInterrupt, EOFError):
                print()
                print("Closing server connection ...")
                self.socket.close()
                sys.exit(1)
    
    def get_console_input(self):
        # In this version we keep prompting the user until a non-blank
        # line is entered.
        while True:
            self.input_text = input("Input: ")
            print("Command Entered: ", self.input_text)
            #Grade Averages
            if self.input_text == "scan":
                print("Scanning for file sharing server")
                self.scan_for_service()
                break
            if self.input_text == "connect":
                self.connect_to_server()
                break
            if self.input_text == "llist":
                # looking in a directory
                arr = os.listdir()
                print(arr)
                break
            if self.input_text == "rlist":
                self.input_text = "list"
                self.connection_send()
                self.connection_receive()
                break
            if self.input_text == "put":
                self.fname = input("File name: ")
                self.put_file(self.fname)
                print("Saving file to remote directory")
                break
            if self.input_text == "get":
                #fname = input("File name: ")
                self.get_file("Test_1.txt")
                break
            if self.input_text == "bye":
                self.connection_send()
                print("Closing server connection ... ")
                
                self.socket.close()
                sys.exit(1)
                break

    def scan_for_service(self):
        # Collect our scan results in a list.
        scan_results = []

        # Repeat the scan procedure a preset number of times.
        for i in range(Client.SCAN_CYCLES):

            # Send a service discovery broadcast.
            print("Sending broadcast scan {}".format(i))            
            self.UDP_socket.sendto(Client.SCAN_CMD_ENCODED, Client.ADDRESS_PORT)
        
            while True:
                # Listen for service responses. So long as we keep
                # receiving responses, keep going. Timeout if none are
                # received and terminate the listening for this scan
                # cycle.
                try:
                    recvd_bytes, address = self.UDP_socket.recvfrom(Client.RECV_SIZE)
                    recvd_msg = recvd_bytes.decode(Client.MSG_ENCODING)

                    # Record only unique services that are found.
                    if (recvd_msg, address) not in scan_results:
                        scan_results.append((recvd_msg, address))
                        continue
                # If we timeout listening for a new response, we are
                # finished.
                except socket.timeout:
                    break

        # Output all of our scan results, if any.
        if scan_results:
            for result in scan_results:
                print(result)
        else:
            print("No services found.")
    
    def connect_to_server(self):
        try:
            # Connect to the server using its socket address tuple.
            self.socket.connect((Client.TCP_ADDRESS, Client.TCP_PORT))
            #print("Connection received from {}".format(Server.HOSTNAME) + " on port {}.".format(Server.PORT))
        except Exception as msg:
            print(msg)
            sys.exit(1)    
                
    def connection_send(self):
        try:
            # Send string objects over the connection. The string must
            # be encoded into bytes objects first.
            package = CMD["LIST"].to_bytes(CMD_FIELD_LEN, byteorder='big')
            self.socket.sendall(package)
            #print("Send")
        except Exception as msg:
            print(msg)
            sys.exit(1)

    def connection_receive(self):
        try:
            # Receive and print out text. The received bytes objects
            # must be decoded into string objects.
            recvd_bytes, address = self.socket.recvfrom(Client.RECV_SIZE)

            # recv will block if nothing is available. If we receive
            # zero bytes, the connection has been closed from the
            # other end. In that case, close the connection on this
            # end and exit.
            if len(recvd_bytes) == 0:
                print("Closing server connection ... ")
                self.socket.close()
                sys.exit(1)

            print("Received: ", recvd_bytes.decode(MSG_ENCODING))

        except Exception as msg:
            print(msg)
            sys.exit(1)

    def connection_send_BYE(self):
        try:
            # Send string objects over the connection. The string must
            # be encoded into bytes objects first.
            package = CMD["LIST"].to_bytes(CMD_FIELD_LEN, byteorder='big')
            self.socket.sendall(package)
            #print("Send")
        except Exception as msg:
            print(msg)
            sys.exit(1)
     
    def socket_recv_size(self, length):
        bytes = self.socket.recv(length)
        if len(bytes) < length:
            self.socket.close()
            exit()
        return(bytes)
            
    def get_file(self, fname):

        # Create the packet GET field.
        get_field = CMD["GET"].to_bytes(CMD_FIELD_LEN, byteorder='big')

        # Create the packet filename field.
        filename_field = fname.encode(MSG_ENCODING)

        # Create the packet.
        pkt = get_field + filename_field

        # Send the request packet to the server.
        self.socket.sendall(pkt)

        # Read the file size field.

        file_size_bytes = self.socket_recv_size(FILE_SIZE_FIELD_LEN)
        if len(file_size_bytes) == 0:
               self.socket.close()
               return

        # Make sure that you interpret it in host byte order.
        file_size = int.from_bytes(file_size_bytes, byteorder='big')

        # Receive the file itself.
        recvd_bytes_total = bytearray()
        try:
            # Keep doing recv until the entire file is downloaded. 
            while len(recvd_bytes_total) < file_size:
                recvd_bytes_total += self.socket.recv(Client.RECV_SIZE)

            # Create a file using the received filename and store the
            # data.
            print("Received {} bytes. Creating file: {}" \
                  .format(len(recvd_bytes_total), fname))

            with open(Client.LOCAL_FILE_NAME, 'w') as f:
                f.write(recvd_bytes_total.decode(MSG_ENCODING))
        except KeyboardInterrupt:
            print()
            exit(1)
        # If the socket has been closed by the server, break out
        # and close it on this end.
        except socket.error:
            self.socket.close()

    def put_file(self, fname):
        
        put_field = CMD["PUT"].to_bytes(CMD_FIELD_LEN, byteorder='big')

        # Create the packet filename field.
        filename_field = fname.encode(MSG_ENCODING)

        # Create the packet.
        pkt = put_field + filename_field
        self.socket.sendall(pkt)
        print("Sending put request")
        
        
        recvd_bytes, address = self.socket.recvfrom(Client.RECV_SIZE)

        if len(recvd_bytes) == 0:
            print("Closing server connection ... ")
            self.socket.close()
            sys.exit(1)

        print("Received: ", recvd_bytes.decode(MSG_ENCODING))
        
         
        # Open the requested file and get set to send it to the server
        try:
            file = open(fname, 'r').read()
        except FileNotFoundError:
            print("Error: Requested file is not available!")
            connection.close()                   
            return
        
        # Encode the file contents into bytes, record its size and
        # generate the file size field used for transmission.
        file_bytes = file.encode(MSG_ENCODING)
        file_size_bytes = len(file_bytes)
        file_size_field = file_size_bytes.to_bytes(FILE_SIZE_FIELD_LEN, byteorder='big')

        # Create the packet to be sent with the header field.
        pkt = file_size_field + file_bytes
        
        try:
            # Send the packet to the connected client.
            self.socket.sendall(pkt)
            # print("Sent packet bytes: \n", pkt)
            print("Sending file: ", fname)
        except socket.error:
            # If the client has closed the connection, close the
            # socket on this end.
            print("Closing client connection ...")
            self.socket.close()
            return
            
########################################################################

if __name__ == '__main__':
    roles = {'client': Client,'server': Server}
    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--role',
                        choices=roles, 
                        help='server or client role',
                        required=True, type=str)

    args = parser.parse_args()
    roles[args.role]()

########################################################################






