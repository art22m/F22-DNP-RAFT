servers = {}
servers[1] = ('11', 'p1')
servers[2] = ('22', 'p2')
servers[3] = ('33', 'p3')

for id, (ipaddr, port) in servers.items():
    print(id, ipaddr, port)