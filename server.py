# Imports

import raft_pb2 as pb2
import raft_pb2_grpc as pb2_grpc

import grpc
import sys
import signal
import enum 
import random
import time
import datetime

from concurrent import futures
from threading import Thread
from multiprocessing import Lock

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

    id = None
    socket = '127.0.0.1:5001'

    servers = {} # {id : (server_stub, socket)}
    servers_number = None

    # Config

    is_voted_at_this_term = False
    is_suspended = False

    should_update_timer = True

    votes_number = 0

    leader_id = 0

    # Constants 

    SERVER_TIMEOUT = 0.5
    CONFIG_PATH = 'config.conf'
    
    TIMER_FROM = 150
    TIMER_TO = 300

    # Threads

    leader_election_mutex = Lock()

    server_time = 0
    timer_thread = None
    leader_thread = None 

    # Init

    def __init__(self, id):
        super().__init__()
        
        self.term = 0
        self.timer = random.randint(self.TIMER_FROM, self.TIMER_TO)
        self.state = State.follower
        
        self._read_and_create_stubs(self.CONFIG_PATH)
        self.servers_number = len(self.servers)
        self.id = id
        _, self.socket = self.servers[int(id)]

        print(f'Server is started at {self.socket}')
        self._print_state()

        self.timer_thread = Thread(target=self._start_timer_thread, args=(), daemon=True)
        self.timer_thread.start()

    # Public Methods
    
    def request_vote(self, request, context):
        if self.is_suspended:
            return

        self.should_update_timer = True
        # print(f'Request from candidate with id = {request.candidate_id}')

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
        print(f'Heartbeat from leader with id = {request.leader_id}')

        success = self.term <= request.term
        if success:
            self.term = request.term
            self.leader_id = request.leader_id

            if self.state != State.follower:
                self.state = State.follower
                self._print_state()

        return pb2.AppendReply(term=self.term, success=success)

    def get_leader(self, request, context):
        if self.is_suspended:
            return

        print('Command from client: getleader')

        leader_ipaddr, leader_port = self.servers[self.leader_id]
        print(f'{self.leader_id} {leader_ipaddr}:{leader_port}')

        return pb2.GetLeaderReply(leader_id=self.leader_id, address=f'{leader_ipaddr}:{leader_port}')

    def suspend(self, request, context):
        if self.is_suspended:
            return

        print(f'Command from client: suspend {request.period}')
        print(f'Sleeping for {request.period} seconds')
        self.is_suspended = True
        time.sleep(request.period)
        self.is_suspended = False

        return pb2.EmptyMessage()

    # Private Methdos

    def _print_state(self):
        print(f'I am a {self.state.name}. Term: {self.term}')

    def _read_and_create_stubs(self, path):
        try:
            with open(path) as config:
                for line in config:
                    conf_id, ipaddr, port = line.split()

                    socket = f"{ipaddr}:{port}"
                    server_channel = grpc.insecure_channel(socket) 
                    server_stub = pb2_grpc.RaftServiceStub(server_channel)

                    self.servers[int(conf_id)] = (server_stub, socket)

        except Exception as e:
            terminate(f'Unable to open/parse {path} file:\n{e}')

    def _start_timer_thread(self):
        time_start = datetime.datetime.now()
        while True:
            if self.is_suspended:
                continue

            if self.should_update_timer:
                self.should_update_timer = False
                time_start = datetime.datetime.now()
                continue

            if (datetime.datetime.now() - time_start).total_seconds() * 1000 <= self.timer:
                continue

            if self.state == State.follower:
                self.state = State.candidate
                self.term += 1
                self.is_voted_at_this_term = False

                print('The leader is dead')
                self._print_state()

                self._start_leader_election()

            elif self.state == State.candidate:
                # MARK: Maybe useless, double check needed
                # if self.state == State.candidate and self.votes_number >= self.servers_number / 2:
                #     self.should_update_timer = True
                #     self.state = State.leader
                #     self._print_state()
                    
                # else:
                print('Timeout for elections')
                self.timer = random.randint(self.TIMER_FROM, self.TIMER_TO)
                self.state = State.follower
        
            elif self.state == State.leader:
                self.should_update_timer = True

    # Election 

    def _start_leader_election(self):
        if self.is_suspended or self.state != State.candidate:
            return

        print("Start leader election procedure")

        self.votes_number = 1
        self.is_voted_at_this_term = True

        threads = []
        for id, (server_stub, socket) in self.servers.items():
            if id != self.id:
                threads.append(Thread(target=self._request_vote, args=(server_stub, socket,)))

        [t.start() for t in threads]
        [t.join() for t in threads]

        print(f'Votes received: {self.votes_number} / {self.servers_number}')

        if self.state == State.candidate and self.votes_number >= self.servers_number / 2:
            self.should_update_timer = True
            self.state = State.leader
            self.leader_id = self.id

            self._print_state()

            self.leader_thread = Thread(target=self._start_leader_procedure, args=())
            self.leader_thread.start()


    def _request_vote(self, server_stub, socket):
        if self.is_suspended or self.state != State.candidate:
            return

        self.should_update_timer = True

        message = pb2.VoteRequest(term=self.term, candidate_id=self.id)
        try:
            response = server_stub.request_vote(message, timeout = self.SERVER_TIMEOUT)

            with self.leader_election_mutex:
                if response.result:
                    self.votes_number += 1
                elif self.term < response.term:
                    self.state = State.follower
                    self.term = response.term
                    self._print_state
        except:
            return # TODO: maybe do smth here

    # Heartbeat 

    def _start_leader_procedure(self):
        while True:
            if self.state != State.leader:
                break

            if self.is_suspended:
                continue

            self.should_update_timer = True

            threads = []
            for id, (server_stub, _) in self.servers.items():
                if id != self.id:
                    threads.append(Thread(target=self._send_hearbeat, args=(server_stub,)))

            [t.start() for t in threads]
            [t.join() for t in threads]

            time.sleep(0.05)

    
    def _send_hearbeat(self, server_stub):
        if self.is_suspended or self.state != State.leader:
            return
            
        message = pb2.AppendRequest(term=self.term, leader_id=self.id)
        try:
            response = server_stub.append_entries(message, timeout = self.SERVER_TIMEOUT)

            if self.term < response.term:
                self.term = response.term
                self.state = State.follower

        except:
            return # TODO: maybe do smth here

def start_server(id):
    serverHandler = ServerHandler(id)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    pb2_grpc.add_RaftServiceServicer_to_server(serverHandler, server)
    server.add_insecure_port(serverHandler.socket)
    server.start()

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
