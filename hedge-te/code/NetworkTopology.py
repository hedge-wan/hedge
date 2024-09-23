from itertools import islice
import sys

class Node:
    def __init__(self, mkt):
        self.mkt = mkt
        self.incoming_edges = {}
        self.outgoing_edges = {}
    
    def add_incoming_edge(self, e, edge):
        self.incoming_edges[e] = edge
    
    def add_outgoing_edge(self, e, edge):
        self.outgoing_edges[e] = edge
            
class Edge:
    #
    # An Edge contains a Graph edge object.
    # and additional attributes.
    # tunnels   - List of tunnels that the edge is part of
    #
    def __init__(self, e, unity, capacity, maxCapacity):
        self.e = e
        self.unity = unity
        self.capacity = capacity
        self.relative_capacity = capacity / maxCapacity
        self.max_capacity = maxCapacity
        self.distance = None
        self.tunnels = []

    def __repr__(self):
        return f"{self.e}"

    def add_tunnel(self, t):
        assert self.e in [edge.e for edge in t.path]
        if all(t.pathstr != x.pathstr for x in self.tunnels):
            self.tunnels.append(t)

class Demand:
    def __init__(self, src, dst, amount):
        self.src = src
        self.dst = dst
        self.amount = amount
        self.tunnels = []
        self.b_d = None

    def __repr__(self):
        return f"({self.src}:{self.dst})"

    def add_tunnel(self, t):
        assert t.pathstr.split(':')[0] == self.src
        assert t.pathstr.split(':')[-1] == self.dst
        if t.pathstr not in [x.pathstr for x in self.tunnels]:
            self.tunnels.append(t)
        
class Tunnel:
    def __init__(self, path, pathstr):
        # path here is a list of edges
        self.path = path
        self.pathstr = pathstr
        self.weight = 0
        for e in path:
            e.add_tunnel(self)

    def name(self):
        return self.pathstr

    def __repr__(self):
        return self.name()
    
    def add_weight(self, weight):
        self.weight = weight

class Network:
    def __init__(self, name):
        self.name = name
        self.nodes = {}
        self.edges = {}
        self.tunnels = {}
        self.demands = {}
        self.graph = None
        
    def add_node(self, mkt):
        assert isinstance(mkt, str)
        if mkt in self.nodes:
            node = self.nodes[mkt]
        else:
            node = Node(mkt)
            self.nodes[mkt] = node
        return node

    def add_edge(self, mktA, mktB, unity=None, capacity=None, maxCapacity=None):
        assert isinstance(mktA, str)
        assert isinstance(mktB, str)
        self.add_node(mktA)
        self.add_node(mktB)
        if mktA == mktB: return None
        
        if (mktA, mktB) in self.edges:
            edge = self.edges[(mktA, mktB)]
            edge.increment_capacity(capacity)
        else:
            edge = Edge((mktA, mktB), unity, capacity, maxCapacity)
            self.edges[(mktA, mktB)] = edge
            self.nodes[mktA].add_outgoing_edge((mktA, mktB), edge)
            self.nodes[mktB].add_incoming_edge((mktA, mktB), edge)
            
        return edge

    def remove_zero_capacity_edges(self):
        edges_to_rm = []
        for edge in self.edges:
            if self.edges[edge].capacity == 0:
                edges_to_rm.append(edge)
        for edge in edges_to_rm:
            self.edges.pop(edge)
                
    def add_demand(self, src, dst, amount, scale=1):
        assert isinstance(src, str)
        assert isinstance(dst, str)
        self.add_node(src)
        self.add_node(dst)
        
        if (src, dst) not in self.demands:
            self.demands[(src, dst)] = Demand(src, dst, amount*scale)

        return self.demands[(src, dst)]

    def add_tunnel(self, tunnel):
        assert isinstance(tunnel, list)
        assert isinstance(tunnel[0], str)
        tunnel_str = ":".join(tunnel)
        if tunnel_str in self.tunnels: return
        
        tunnel_start = tunnel[0]
        tunnel_end = tunnel[-1]
        tunnel_edge_list = []
        for src, dst in zip(tunnel, tunnel[1:]):
            nodeA = self.add_node(src)
            nodeB = self.add_node(dst)
            assert (src, dst) in self.edges
            edge = self.edges[(src, dst)]
            tunnel_edge_list.append(edge)

        tunnel_obj = Tunnel(tunnel_edge_list, tunnel_str)
        self.tunnels[tunnel_str] = tunnel_obj        
        if (tunnel_start, tunnel_end) in self.demands:
            demand = self.demands[(tunnel_start, tunnel_end)]
            demand.add_tunnel(tunnel_obj)

    def to_nx(self):
        import networkx
        graph = networkx.DiGraph()
        for n in self.nodes.keys():
            graph.add_node(n)
        for (s,t) in self.edges:
            graph.add_edge(s, t, distance=400)
        return graph

    def draw(self, labels):
        import matplotlib.pyplot as plt
        import networkx as nx
        G = self.to_nx()
        pos = nx.spring_layout(G) #, weight=1,
                               # pos={'0':(0,0), '1':(0,1), '2':(1,1), '3':(1,0)}, 
                               # fixed=['0', '1', '2', '3'])
        plt.figure(figsize=(25,20))
        options = {
            'width': 1,
            'arrowstyle': '-|>',
            'arrowsize': 12
        }
        nx.draw(G, pos, edge_color = 'black', linewidths = 3,
                # connectionstyle='arc3, rad = 0.1',
                node_size = 1000, node_color = 'pink',
                alpha = 0.9, with_labels = True, **options)
        nx.draw_networkx_edge_labels(G, pos, font_size=10,
                                     label_pos=0.3,
                                     edge_labels=labels)
        ax = plt.gca()
        ax.collections[0].set_edgecolor("#000000")
        plt.axis('off')
        plt.show()

    def k_shortest_paths(self, source, target, k):
        import networkx as nx
        G = self.to_nx()
        return list(islice(nx.shortest_simple_paths(G, source, target), k))

    def k_shortest_edge_disjoint_paths(self, source, target, k):
        import networkx as nx
        G = self.to_nx()
        possibilities = list(nx.edge_disjoint_paths(G, source, target))
        possibilities.sort(key=len)
        return list(islice(possibilities, k))