from NetworkTopology import *
import csv
from itertools import product
import pickle

def get_max_and_min_networks(network_name: str, topology_filename):
    bidirectional_link_possibilities = {}
    bidirectional_link_identifiers = {}

    with open(topology_filename, 'rb') as fi:
        data = pickle.load(fi)
        for edge_id, dist in data.items():
            to_node = edge_id[0]
            from_node = edge_id[1]
            if (to_node, from_node) in bidirectional_link_possibilities:
                continue
            nonzero_states = [x for x in dist.keys() if x > 0]
            min_nonzero_state = min(nonzero_states)
            max_state = max(nonzero_states)
            states = {min_nonzero_state: dist[min_nonzero_state], max_state: dist[max_state]}
            bidirectional_link_possibilities[(from_node, to_node)] = states
    
    bidirectional_link_combos = []
    max_capacities = {}
    min_nonzero_capacities = {}
    bidirectional_link_id = 0

    for link, link_states in bidirectional_link_possibilities.items():
        assert (link[1], link[0]) not in bidirectional_link_identifiers
        if link not in bidirectional_link_identifiers:
            bidirectional_link_combos.append(list(link_states.keys()))
            bidirectional_link_identifiers[link] = bidirectional_link_id
            max_capacities[bidirectional_link_id] = max(link_states.keys())
            min_nonzero_capacities[bidirectional_link_id] = min([x for x in link_states.keys() if x > 0])
            bidirectional_link_id += 1
    
    min_possibility = [min(capacities) for capacities in bidirectional_link_combos]
    max_possibility = [max(capacities) for capacities in bidirectional_link_combos]
    network_possibilities = [min_possibility, max_possibility]
    scenarios = []
    max_scenario = None
    min_nonzero_scenario = None
    for instance in network_possibilities:
        network = Network(network_name)
        scenario_prob = 1
        is_max = len(bidirectional_link_identifiers) > 0
        is_min_nonzero = len(bidirectional_link_identifiers) > 0
        for link, link_id in bidirectional_link_identifiers.items():
            network.add_node(link[0])
            network.add_node(link[1])
            network.add_edge(link[0], link[1], 200, instance[link_id], max_capacities[link_id])
            network.add_edge(link[1], link[0], 200, instance[link_id], max_capacities[link_id])
            scenario_prob *= bidirectional_link_possibilities[link][instance[link_id]]

            if instance[link_id] < max_capacities[link_id]:
                is_max = False
            
            if instance[link_id] != min_nonzero_capacities[link_id]:
                is_min_nonzero = False
            
        scenarios.append((network, scenario_prob))
        if is_max:
            max_scenario = network
        if is_min_nonzero:
            min_nonzero_scenario = network

    return scenarios, max_scenario, min_nonzero_scenario

def parse_stochastic_topology_for_teavar(network_name: str, topology_filename, prob_threshold=0):
    bidirectional_link_possibilities = {}
    bidirectional_link_identifiers = {}

    with open(topology_filename, 'rb') as fi:
        data = pickle.load(fi)
        for edge_id, dist in data.items():
            to_node = edge_id[0]
            from_node = edge_id[1]
            if (to_node, from_node) in bidirectional_link_possibilities:
                continue
            states = {}
            max_capacity = max(dist.keys())
            states[max_capacity] = dist[max_capacity]
            if 1 - dist[max_capacity] >= prob_threshold:
                states[0] = 1 - dist[max_capacity]
            bidirectional_link_possibilities[(from_node, to_node)] = states
            
    bidirectional_link_combos = []
    max_capacities = {}
    bidirectional_link_id = 0
    num_scenarios = 1
    for link, link_states in bidirectional_link_possibilities.items():
        assert (link[1], link[0]) not in bidirectional_link_identifiers
        if link not in bidirectional_link_identifiers:
            assert len(link_states.keys()) == 1 or len(link_states.keys()) == 2
            num_scenarios *= len(link_states.keys())
            bidirectional_link_combos.append(list(link_states.keys()))
            bidirectional_link_identifiers[link] = bidirectional_link_id
            max_capacities[bidirectional_link_id] = max(link_states.keys())
            bidirectional_link_id += 1
    
    print("Number of network scenarios:", num_scenarios)
    network_possibilities = product(*bidirectional_link_combos)
    scenarios = []
    for instance in network_possibilities:
        network = Network(network_name)
        scenario_prob = 1
        for link, link_id in bidirectional_link_identifiers.items():
            network.add_node(link[0])
            network.add_node(link[1])
            network.add_edge(link[0], link[1], 200, instance[link_id], max_capacities[link_id])
            network.add_edge(link[1], link[0], 200, instance[link_id], max_capacities[link_id])
            scenario_prob *= bidirectional_link_possibilities[link][instance[link_id]]

        scenarios.append((network, scenario_prob))
    return scenarios

def get_link_capacity_distributions_with_filename(topology_filename):
    import pickle
    bidirectional_link_possibilities = {}

    with open(topology_filename, 'rb') as fi:
        data = pickle.load(fi)
        for edge_id, dist in data.items():
            to_node = edge_id[0]
            from_node = edge_id[1]
            if (to_node, from_node) in bidirectional_link_possibilities:
                continue
            states = {}
            for capacity, prob in dist.items():
                states[capacity] = prob
            bidirectional_link_possibilities[(from_node, to_node)] = states
    return bidirectional_link_possibilities

def parse_demands(network, demand_filename, scale=1):
    num_nodes = len(network.nodes)
    demand_matrix = {}
    with open(demand_filename, 'r') as fi:
        reader = csv.reader(fi, delimiter=" ")
        for row_ in reader:
            row = [float(x) for x in row_ if x]
            assert len(row) == num_nodes ** 2
            for idx, dem in enumerate(row):
                from_node = int(idx/num_nodes) + 1
                to_node = (idx % num_nodes) + 1
                assert str(from_node) in network.nodes
                assert str(to_node) in network.nodes
                if from_node == to_node: continue
                if from_node not in demand_matrix:
                    demand_matrix[from_node] = {}
                if to_node not in demand_matrix[from_node]:
                    demand_matrix[from_node][to_node] = []
                demand_matrix[from_node][to_node].append(dem)
        for from_node in demand_matrix:
            for to_node in demand_matrix[from_node]:
                max_demand = max(demand_matrix[from_node][to_node])
                network.add_demand(str(from_node), str(to_node), max_demand / 1000.0, scale)
    if network.tunnels:
        remove_demands_without_tunnels(network)

def parse_tunnels(network):
    for node1 in network.nodes:
        for node2 in network.nodes:
            if node1 == node2: continue
            paths = network.k_shortest_paths(node1, node2, 4)
            for path in paths:
                tunnel = network.add_tunnel(path)
    if network.demands:
        remove_demands_without_tunnels(network)

def remove_demands_without_tunnels(network):
    removable_demands = [p for p, d in network.demands.items() if not d.tunnels]
    assert len(removable_demands) == 0
    for demand_pair in removable_demands:
        del network.demands[demand_pair]