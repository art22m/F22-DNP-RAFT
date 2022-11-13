# Imports

import raft_pb2 as pb2
import raft_pb2_grpc as pb2_grpc

import grpc
import sys
import signal

# Constants 

SERVER_CONNECTION_TIMEOUT = 10

# Config

server_channel = None
server_stub = None

# Helper

def terminate(message, closure=None):
    print(message)
    if closure is not None:
        closure()
    sys.exit()

# Client functions

def connect(ipaddr, port):
    global server_channel
    global server_stub

    server_channel = grpc.insecure_channel(f"{ipaddr}:{port}")
    try:
        grpc.channel_ready_future(server_channel).result(timeout=SERVER_CONNECTION_TIMEOUT)
        server_stub = pb2_grpc.RaftServiceStub(server_channel)
    except grpc.FutureTimeoutError:
        print(f"The server {ipaddr}:{port} is unavailable")
        return


def get_leader():
    global server_stub
    if server_stub is None:
        print('The client is not connected to any server')
        return

    message = pb2.EmptyMessage()
    response = server_stub.get_leader(message)
    print(f"{response.leader_id} {response.address}")


def suspend(period):
    global server_stub
    if server_stub is None:
        print('The client is not connected to any server')
        return

    message = pb2.SuspendRequest(period=int(period))
    server_stub.suspend(message)


def start_client():
    print('The client starts')
    while True:
        client_input = input('> ')

        command = client_input.split(' ', 1)[0]
        arguments = client_input.split(' ', 1)[1::]

        # connect
        if command == 'connect':
            ipaddr = arguments[0].split(' ')[0]
            port = arguments[0].split(' ')[1]
            connect(ipaddr, port)

        elif command == 'getleader':
            get_leader()

        elif command == 'suspend':
            suspend(arguments[0])

        elif command == 'exit':
            terminate('The client ends')

        else:
            print('Unknown command')
            #print_help()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.default_int_handler)

    try:
        start_client()
    except KeyboardInterrupt as keys:
        terminate(f'{keys} was pressed, terminating server.')