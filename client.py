"""
|Client|
DNP Lab: RAFT
Students: Vagif Khalilov, Artem Murashko
Emails: v.khalilov@innopolis.university, ar.murashko@innopolis.univeristy
Group: BS20-SD-01
"""

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
server_port = 5000
server_channel = None
server_stub = None


# Helpers

def terminate(message, closure=None):
    print(message)
    if closure is not None:
        closure()
    sys.exit()


def print_help():
    print('\nAvailable commands:')
    print('connect <ipaddr> <port>')
    print('getleader')
    print('suspend <period>')
    print('quit\n')


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

### NEED TO TEST THIS ###

def check_stub():
    if server_stub is None:
        print(f"The server {server_addr}:{server_port} is unavailable")
        return False
    return True

def send_message(message, rpc_function):
    if not check_stub():
        return None

    try:
        response = rpc_function(message)
        return response
    except:
        print(f"The server {server_addr}:{server_port} is unavailable")
        return None

def get_leader():
    message = pb2.EmptyMessage()
    response = send_message(message, server_stub.get_leader)
    if response is not None:
        print(f"{response.leader_id} {response.address}")

def suspend(period):
    message = pb2.SuspendRequest(period=int(period))
    response = send_message(message, server_stub.suspend)

def set_val(key, value):
    message = pb2.SetValRequest(key=key, value=value)
    response = send_message(message, server_stub.set_val)
    if response is not None: # after testing, remove this if-statement
        print(response.message)

def get_val(key):
    message = pb2.GetValRequest(key=key)
    response = send_message(message, server_stub.get_val)
    if response is not None:
        print(response.value)

def start_client():
    print('The client starts')
    while True:
        client_input = input('> ')

        command = client_input.split(' ', 1)[0]
        arguments = client_input.split(' ', 1)[1::]

        if command == 'connect' and len(arguments[0].split(' ')) == 2:
            ipaddr = arguments[0].split(' ')[0]
            port = arguments[0].split(' ')[1]
            connect(ipaddr, port)

        elif command == 'getleader':
            get_leader()

        elif command == 'suspend' and len(arguments) == 1:
            suspend(arguments[0])

        elif command == 'setval' and len(arguments) == 2:
            set_val(arguments[0], arguments[1])

        elif command == 'getval' and len(arguments) == 1:
            get_val(arguments[0])

        elif command == 'quit':
            terminate('The client ends')

        else:
            print_help()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.default_int_handler)

    try:
        start_client()
    except KeyboardInterrupt as keys:
        terminate(f'{keys} was pressed, terminating the client.')
