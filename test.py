import enum
import datetime
import time
import random 

servers = {}
servers[1] = ('11', 'p1')
servers[2] = ('22', 'p2')
servers[3] = ('33', 'p3')

# for id, (ipaddr, port) in servers.items():
#     print(id, ipaddr, port)

# class State(enum.Enum):
#     follower = 0
#     candidate = 1
#     leader = 2

# time_start = datetime.datetime.now()
# time.sleep(0.1)
# print((datetime.datetime.now() - time_start).total_seconds() * 1000 < 150)

print(random.randint(1, 3))