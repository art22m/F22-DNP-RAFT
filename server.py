"""
|Server|
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
import enum
import random
import time
import datetime

from concurrent import futures
from threading import Thread

# Constants

MAX_WORKERS = 10


# Helpers

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

    servers = {}  # {id : (server_stub, socket)}
    servers_number = None

    # Config

    is_voted_at_this_term = False
    is_suspended = False

    should_reset_timer = True

    votes_number = 0

    leader_id = 0

    commit_idx = 0 # index of the last log entry on the server
    last_applied_idx = 0 # index of the last applied log entry.

    logs = [] # List of entries [{term, command}]
    next_idx = {} # {id : next_index}
    match_idx = {} # {id : highest_log_idx}
    
    hash_table = {} # {key : value}

    # Constants 

    CONFIG_PATH = 'config.conf'

    TIMER_FROM = 150
    TIMER_TO = 300

    # Threads

    timer_thread = None
    leader_thread = None
    leader_election_thread = None

    # Init

    def __init__(self, server_id):
        super().__init__()

        self.term = 0
        self.timer = random.randint(self.TIMER_FROM, self.TIMER_TO)
        self.state = State.follower

        self._read_and_create_stubs(self.CONFIG_PATH)
        self.servers_number = len(self.servers)
        self.id = server_id

        if int(server_id) not in self.servers:
            terminate('No such id in the config file')
        _, self.socket = self.servers[int(server_id)]

        print(f'Server is started at {self.socket}')
        self._print_state()

        self.timer_thread = Thread(target=self._start_timer_thread, args=(), daemon=True)
        self.timer_thread.start()

    # Public Methods

    def request_vote(self, request, context): # DONE
        if self.is_suspended:
            return

        self.should_reset_timer = True

        failure_reply = pb2.VoteReply(term=self.term, result=False)
        if request.term < self.term:
            return failure_reply
        elif self.is_voted_at_this_term:
            return failure_reply
        elif request.last_log_index < self.commit_id:
            return failure_reply
        elif (request.last_log_index < len(self.logs)) and (self.logs[request.last_log_index][0] != request.last_log_term):
            return failure_reply
        else:
            self.is_voted_at_this_term = True
            self.state = State.follower
            self.leader_id = request.candidate_id
            self.term = request.term
            
            print(f'Voted for node {self.leader_id}')
            self._print_state()

            return pb2.VoteReply(term=self.term, result=True)

    def append_entries(self, request, context): # TODO: add code for adding new entries in hash_table
        if self.is_suspended:
            return

        self.should_reset_timer = True

        success = ((self.term <= request.term) and (request.prev_log_index < len(self.logs)))
        if success:
            self.term = request.term
            self.leader_id = request.leader_id
            
            start_idx = request.prev_log_index + 1
            logs_start = self.logs[:start_idx]
            logs_middle = self.logs[start_idx : start_idx + len(request.entries)]
            logs_end = self.logs[start_idx + len(request.entries):]

            is_conflict = False
            for i in range(0, logs_middle):
                if logs_middle[i] != request.entries[i]:
                    is_conflict = True
                    break
            
            last_new_entry_idx = 0
            if is_conflict:
                self.logs = logs_start + request.entries
                last_new_entry_idx = len(self.logs) - 1 if len(self.logs) > 0 else 0
            else:
                self.logs = logs_start + request.entries + logs_end
                last_new_entry_idx = len(logs_start + request.entries) - 1 if len(logs_start + request.entries) > 0 else 0

            if request.commit_idx > self.commit_idx:
                self.commit_idx = min(request.commit_idx, last_new_entry_idx)

            if self.state != State.follower:
                self.state = State.follower
                self._print_state()

        return pb2.AppendReply(term=self.term, success=success)

    def get_leader(self, request, context):
        if self.is_suspended or not self.is_voted_at_this_term:
            return

        print('Command from client: getleader')

        _, leader_socket = self.servers[self.leader_id]
        print(f'{self.leader_id} {leader_socket}')

        return pb2.GetLeaderReply(leader_id=self.leader_id, address=leader_socket)

    def suspend(self, request, context):
        if self.is_suspended:
            return

        print(f'Command from client: suspend {request.period}')
        print(f'Sleeping for {request.period} seconds')
        self.is_suspended = True
        time.sleep(request.period)
        self.is_suspended = False

        return pb2.EmptyMessage()

    def set_val(self, request, context):
        if self.is_suspended:
            return

        print(f'Command from client: set {request.key} {request.value}')

        success = False
        if self.state == State.follower:
            leader_stub, _ = self.servers[self.leader_id]
            try:
                response = leader_stub.SetVal(pb2.SetRequest(key=request.key, value=request.value))
                success = response.success
            except:
                success = False
        elif self.state == State.candidate:
            success = False
        else: 
            # add entry to log
            self.logs.append((self.term, ('set', request.key, request.value)))
            self.commit_idx += 1

            current_commit_idx = self.commit_idx

            time.sleep(0.5) # TODO: decrease
            
            success = (current_commit_idx <= self.last_applied_idx)


        return pb2.SetReply(success=success)


    def get_val(self, request, context):
        if self.is_suspended:
            return
            
        value = self.hash_table.get(request.key)

        success = (value is not None)
        value = value if success else "None"
        return pb2.GetReply(success=success, value=value)
        
        
    # Private Methods

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

            if self.should_reset_timer:
                self.should_reset_timer = False
                time_start = datetime.datetime.now()
                continue

            if (datetime.datetime.now() - time_start).total_seconds() * 1000 <= self.timer:
                continue

            if self.state == State.follower:
                self.should_reset_timer = True
                self.state = State.candidate
                self.term += 1

                print('The leader is dead')
                self._print_state()

                self.leader_election_thread = Thread(target=self._start_leader_election, args=(), daemon=True)
                self.leader_election_thread.start()

            elif self.state == State.candidate:
                self.should_reset_timer = True

                if self.votes_number >= self.servers_number / 2:
                    self._become_leader()
                else:
                    self.timer = random.randint(self.TIMER_FROM, self.TIMER_TO)
                    self.state = State.follower
                    self._print_state()

            elif self.state == State.leader:
                self.should_reset_timer = True

    # Election 

    def _start_leader_election(self):
        if self.is_suspended or self.state != State.candidate:
            return

        self.votes_number = 1
        self.is_voted_at_this_term = True
        print(f"Voted for node {self.id}")

        threads = []
        for current_id, (server_stub, _) in self.servers.items():
            if current_id != self.id:
                threads.append(Thread(target=self._request_vote, args=(server_stub,), daemon=True))

        [t.start() for t in threads]
        [t.join() for t in threads]

        if self.state != State.candidate:
            return

        # print(f'Votes received: {self.votes_number} / {self.servers_number}')
        print(f'Votes received')
        if self.votes_number >= self.servers_number / 2:
            self._become_leader()

    def _request_vote(self, server_stub):
        if self.is_suspended or self.state != State.candidate:
            return

        message = pb2.VoteRequest(term=self.term, candidate_id=self.id)
        try:
            response = server_stub.request_vote(message)

            if response.result:
                self.votes_number += 1
            elif self.term < response.term:
                self.state = State.follower
                self.term = response.term
                self._print_state()
        except:
            return

    # Heartbeat 
    def _become_leader(self): # TODO: rewrite this
        if self.state == State.leader:
            return

        self.should_reset_timer = True
        self.state = State.leader
        self.leader_id = self.id
        self._print_state()

        self.leader_thread = Thread(target=self._start_leader_procedure, args=(), daemon=True)
        self.leader_thread.start()

    def _start_leader_procedure(self):
        while True:
            if self.state != State.leader:
                break

            if self.is_suspended:
                continue

            self.should_reset_timer = True

            threads = []
            for current_id, (server_stub, _) in self.servers.items():
                if current_id != self.id:
                    threads.append(Thread(target=self._send_heartbeat, args=(server_stub,), daemon=True))

            [t.start() for t in threads]
            [t.join() for t in threads]

            time.sleep(0.05)

    def _send_heartbeat(self, server_stub): # TODO: rewrite this
        if self.is_suspended or self.state != State.leader:
            return

        self.should_reset_timer = True

        message = pb2.AppendRequest(term=self.term, leader_id=self.id)
        try:
            response = server_stub.append_entries(message) # Modify this

            if self.term < response.term:
                self.term = response.term
                self.state = State.follower

        except:
            return


def start_server(server_id):
    server_handler = ServerHandler(server_id)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    pb2_grpc.add_RaftServiceServicer_to_server(server_handler, server)
    server.add_insecure_port(server_handler.socket)
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt as keys:
        terminate(f'{keys} was pressed, terminating the server...')


# Main

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.default_int_handler)

    input_id = -1
    try:
        input_id = int(sys.argv[1])
    except:
        terminate("Specify arguments in the following order: \n \
                    python3 server.py ID")

    start_server(input_id)
