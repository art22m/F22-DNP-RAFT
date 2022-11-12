# Imports

import raft_pb2 as pb2
import raft_pb2_grpc as pb2_grpc

import grpc
import sys
import signal
import enum 
import os
import random
from concurrent import futures

 # Constants 

MAX_WORKERS = 10

# Helper

def terminate(message, closure=None):
    print(message)
    if closure is not None:
        closure()
    sys.exit()


class State(enum.Enum):

    follower = 0
    candidate = 1
    leader = 2

class ServerHandler(pb2_grpc.RaftServiceServicer):

    # Properties

    term = 0
    timer = 0
    state = State.follower

    host = '127.0.0.1'
    port = '5001'

    servers = {} # {id : (ipaddr:port)}

    # Init

    def __init__(self, id):
        super().__init__()
        
        self.term = 0
        self.timer = random.randint(150, 301)
        self.state = State.follower
        
        self._fetch_servers_info('config.conf')
        self.host, self.port = self.servers[int(id)]
    

    # Public Methods
    
    def requestVote(self, request, context):
        raise NotImplementedError('Method not implemented!')

    def appendEntries(self, request, context):
        raise NotImplementedError('Method not implemented!')

    def getLeader(self, request, context):
        raise NotImplementedError('Method not implemented!')

    def suspend(self, request, context):
        raise NotImplementedError('Method not implemented!')

    # Private Methdos

    def _fetch_servers_info(self, path):
        try:
            with open(path) as config:
                for line in config:
                    conf_id, ipaddr, port = line.split()
                    self.servers[int(conf_id)] = (ipaddr, port)
        except Exception as e:
            terminate(f'Unable to open/parse {path} file:\n{e}')

def start_server(id):
    print('Starting...')

    serverHandler = ServerHandler(id)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    pb2_grpc.add_RaftServiceServicer_to_server(serverHandler, server)
    server.add_insecure_port(f"{serverHandler.host}:{serverHandler.port}")
    server.start()

    print(serverHandler.host, serverHandler.port)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt as keys:
        terminate(f'{keys} was pressed, terminating server')


# Main

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.default_int_handler)

    try:
        id = int(sys.argv[1])
    except:
         terminate("Specify arguments in the following order: \n \
                    python3 server.py ID")

    start_server(id)
