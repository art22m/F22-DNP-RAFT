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
    host = '127.0.0.1'
    port = '5001'

    servers = {} # {id : (ipaddr:port)}
    servers_number = None

    # Config

    is_voted_at_this_term = 0
    is_suspended = False

    should_update_timer = False

    votes_number = 0

    leader_id = 0

    # Constants 

    SERVER_TIMEOUT = 0.5
    CONFIG_PATH = 'config.conf'

    # Threads

    leader_election_mutex = Lock()

    server_time = 0
    timer_thread = None
    leader_thread = None 

    # Init

    def __init__(self, id):
        super().__init__()
        
        self.term = 0
        self.timer = random.randint(700, 1001) # TODO: Change
        self.state = State.follower
        
        self._fetch_servers_info(self.CONFIG_PATH)
        self.servers_number = len(self.servers)
        self.id = id
        self.host, self.port = self.servers[int(id)]

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

    def _fetch_servers_info(self, path):
        try:
            with open(path) as config:
                for line in config:
                    conf_id, ipaddr, port = line.split()
                    self.servers[int(conf_id)] = (ipaddr, port)
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
                self.timer = random.randint(700, 1001) # TODO: Change
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
        for id, (ipaddr, port) in self.servers.items():
            if id != self.id:
                threads.append(Thread(target=self._request_vote, args=(f'{ipaddr}:{port}',), daemon=True))

        [t.start() for t in threads]
        [t.join() for t in threads]

        print('Votes received')

        if self.state == State.candidate and self.votes_number >= self.servers_number / 2:
            self.should_update_timer = True
            self.state = State.leader
            self.leader_id = self.id

            self._print_state()

            self.leader_thread = Thread(target=self._start_leader_procedure, args=(), daemon=True)
            self.leader_thread.start()


    def _request_vote(self, socket_addr):
        if self.is_suspended:
            return

        server_channel = grpc.insecure_channel(socket_addr)
        try:
            grpc.channel_ready_future(server_channel).result(timeout=self.SERVER_TIMEOUT)
        except:
            print(f"Server {socket_addr} is unavailable")
            return
        else:
            server_stub = pb2_grpc.RaftServiceStub(server_channel)

        message = pb2.VoteRequest(term=self.term, candidate_id=self.id)
        try:
            response = server_stub.request_vote(message, timeout = self.SERVER_TIMEOUT)

            with self.leader_election_mutex:
                print(f"Server {socket_addr} result is {response.result}")
                if response.result:
                    self.votes_number += 1
                elif self.term < response.term:
                    self.state = State.follower
                    self.term = response.term
                    self._print_state

        except:
            server_channel.close()

    # Heartbeat 

    def _start_leader_procedure(self):
        while True:
            if self.state != State.leader:
                break

            if self.is_suspended:
                continue

            self.should_update_timer = True

            threads = []
            for id, (ipaddr, port) in self.servers.items():
                if id != self.id:
                    threads.append(Thread(target=self._send_hearbeat, args=(f'{ipaddr}:{port}',), daemon=True))

            [t.start() for t in threads]
            [t.join() for t in threads]

            time.sleep(0.05)

    
    def _send_hearbeat(self, socket_addr):
        if self.is_suspended or self.state != State.leader:
            return
            
        server_channel = grpc.insecure_channel(socket_addr)
        try:
            grpc.channel_ready_future(server_channel).result(timeout=self.SERVER_TIMEOUT)
        except:
            print(f"Server {socket_addr} is unavailable")
            return
        else:
            server_stub = pb2_grpc.RaftServiceStub(server_channel)

        message = pb2.AppendRequest(term=self.term, leader_id=self.id)
        try:
            response = server_stub.append_entries(message, timeout = self.SERVER_TIMEOUT)

            if self.term < response.term:
                self.term = response.term
                self.state = State.follower

        except:
            server_channel.close()

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
