# Imports

import raft_pb2 as pb2
import raft_pb2_grpc as pb2_grpc

import grpc
import sys
import signal
import enum 
import os
import random
import time
from concurrent import futures

 # Constants 

MAX_WORKERS = 10

# Helper

def terminate(message, closure=None):
    print(message)
    if closure is not None:
        closure()
    sys.exit()

# Server

class State(enum.Enum):
    follower = 0
    candidate = 1
    leader = 2

class ServerHandler(pb2_grpc.RaftServiceServicer):

    # Properties

    term = None
    timer = None
    state = None

    host = '127.0.0.1'
    port = '5001'

    servers = {} # {id : (ipaddr:port)}
    servers_number = None

    config_path = 'config.conf'

    # Config

    is_voted_at_this_term = 0
    is_suspended = False

    should_update_timer = False

    leader_id = 0

    # Threads

    # Init

    def __init__(self, id):
        super().__init__()
        
        self.term = 0
        self.timer = random.randint(150, 301)
        self.state = State.follower
        
        self._fetch_servers_info(self.config_path)
        self.servers_number = len(self.servers)
        self.host, self.port = self.servers[int(id)]

    # Public Methods
    
    def request_vote(self, request, context):
        if self.is_suspended:
            return

        self.should_update_timer = True

        if self.term < request.term:
            self.is_voted_at_this_term = False
            self.term = request.term

        result = False
        if self.term == request.term and not self.is_voted_at_this_term:
            self.is_voted_at_this_term = True
            self.state = State.follower
            self.leader_id = request.candidate_id # TODO: Need to check the truth of this idea
            result = True

        return pb2.VoteReply(term=self.term, result=result)

    def append_entries(self, request, context):
        if self.is_suspended:
            return

        self.should_update_timer = True

        success = self.term <= request.term
        current_term = None
        if success:
            current_term = request.term
            self.leader_id = request.leader_id
        else:
            current_term = self.term

        self.term = current_term
        return pb2.AppendReply(term=current_term, success=success)

    def get_leader(self, request, context):
        if self.is_suspended:
            return

        leader_ipaddr, leader_port = self.servers[self.leader_id]
        return pb2.GetLeaderReply(leader_id=self.leader_id, address=f'{leader_ipaddr}:{leader_port}')

    def suspend(self, request, context):
        if self.is_suspended:
            return

        print("sleep")
        self.is_suspended = True
        time.sleep(request.period)
        self.is_suspended = False
        print("wake up")

        return pb2.EmptyMessage()

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
    serverHandler = ServerHandler(id)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    pb2_grpc.add_RaftServiceServicer_to_server(serverHandler, server)
    server.add_insecure_port(f"{serverHandler.host}:{serverHandler.port}")
    server.start()

    print(f'Server is started at {serverHandler.host}:{serverHandler.port}')
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
