# Imports

import raft_pb2 as pb2
import raft_pb2_grpc as pb2_grpc

import grpc
import sys
import signal

# Constants 

SERVER_CONNECTION_TIMEOUT = 10

# Config

server_addr = '127.0.0.1'
server_port = 50051
server_channel = None
server_stub = None

# Helper

def terminate(message, closure=None):
    print(message)
    if closure is not None:
        closure()
    sys.exit()

def print_help():
    print('Commands:')
    print('connect <ipaddr> <port>')
    print('getleader')
    print('suspend <period>')
    print('exit')

# Client functions

def connect(ipaddr, port):
    global server_channel
    global server_stub
    global server_addr
    global server_port

    server_addr = ipaddr
    server_port = port

    server_channel = grpc.insecure_channel(f"{ipaddr}:{port}")
    try:
        grpc.channel_ready_future(server_channel).result(timeout=SERVER_CONNECTION_TIMEOUT)
        server_stub = pb2_grpc.RaftServiceStub(server_channel)
    except grpc.FutureTimeoutError:
        print(f"The server {server_addr}:{server_port} is unavailable")
        return


def get_leader():
    global server_stub
    if server_stub is None:
        print('The client is not connected to any server')
        return

    message = pb2.EmptyMessage()

    try: 
        response = server_stub.get_leader(message)
        print(f"{response.leader_id} {response.address}")
    except:
        print(f"The server {server_addr}:{server_port} is unavailable")


def suspend(period):
    global server_stub
    if server_stub is None:
        print('The client is not connected to any server')
        return

    message = pb2.SuspendRequest(period=int(period))
    try:
        server_stub.suspend(message)
    except:
        print(f"The server {server_addr}:{server_port} is unavailable")


def start_client():
    print('The client starts')
    while True:
        client_input = input('> ')

        command = client_input.split(' ', 1)[0]
        arguments = client_input.split(' ', 1)[1::]
        
        # connect
        if command == 'connect' and len(arguments[0].split(' ')) == 2:
            ipaddr = arguments[0].split(' ')[0]
            port = arguments[0].split(' ')[1]
            connect(ipaddr, port)

        elif command == 'getleader':
            get_leader()

        elif command == 'suspend' and len(arguments) == 1:
            suspend(arguments[0])

        elif command == 'exit':
            terminate('The client ends')

        else:
            print_help()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.default_int_handler)

    try:
        start_client()
    except KeyboardInterrupt as keys:
        terminate(f'{keys} was pressed, terminating server.')