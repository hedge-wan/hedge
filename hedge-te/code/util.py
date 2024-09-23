from ast import literal_eval
from collections import defaultdict
import numpy as np

def total_demand_requested(demand_matrix):
    total_demand = 0
    for src in demand_matrix:
        total_demand += sum(demand_matrix[src].values())
    return total_demand

def total_demand_requested_network(network):
    total_demand = 0
    for demand_id in network.demands:
        total_demand += network.demands[demand_id].amount
    return total_demand

def get_tunnel_allocations(gurobi_results):
    tunnel_allocations = {}
    for var_name, var_val in gurobi_results.items():
        if not var_name.startswith('flow'):
            continue
        parsed = var_name.removeprefix('flow').split('on')
        tunnel_id = parsed[1]
        tunnel_allocations[tunnel_id] = var_val
    
    return tunnel_allocations

def edge_coverage(max_network, tunnel_allocations):
    capacity_utilizations = {}
    displaced_traffic = 0
    for edge_id, edge in max_network.edges.items():
        capacity_used = 0
        for tunnel in edge.tunnels:
            if tunnel.name() in tunnel_allocations:
                capacity_used += tunnel_allocations[tunnel.name()]
        capacity_utilizations[edge_id] = (capacity_used, edge.capacity, capacity_used/edge.capacity)
        if capacity_used > edge.capacity:
            displaced_traffic += (capacity_used - edge.capacity)
    return capacity_utilizations, displaced_traffic

def prepare_postprocessing(max_network, edge_utilizations):
    overallocated_edges = {}
    for e in edge_utilizations:
        if edge_utilizations[e][2] > 1.0000001:
            overallocated_edges[e] = [tunnel.name() for tunnel in max_network.edges[e].tunnels]
    
    return overallocated_edges

def effective_throughput(postproc_lp_results, original_tunnel_allocations):
    new_tunnel_allocations = {}

    for tunnel in original_tunnel_allocations:
        if tunnel in postproc_lp_results:
            new_tunnel_allocations[tunnel] = original_tunnel_allocations[tunnel] - postproc_lp_results[tunnel]
        else:
            new_tunnel_allocations[tunnel] = original_tunnel_allocations[tunnel]
    
    return new_tunnel_allocations

def effective_throughput_opt(postproc_lp_results, tunnel_ids, original_tunnel_allocations):
    new_tunnel_allocations = {}

    for tunnel in original_tunnel_allocations:
        if str(tunnel_ids[tunnel]) in postproc_lp_results:
            new_tunnel_allocations[tunnel] = original_tunnel_allocations[tunnel] - postproc_lp_results[str(tunnel_ids[tunnel])]
        else:
            new_tunnel_allocations[tunnel] = original_tunnel_allocations[tunnel]
    
    return new_tunnel_allocations

def simulate_network_state(base_network, link_capacity_distributions):
    is_max = True
    for bidirectional_link, states in link_capacity_distributions.items():
        scenario_edge_capacity = np.random.choice(list(states.keys()), p=list(states.values()))
        base_network.edges[(bidirectional_link[0], bidirectional_link[1])].capacity = scenario_edge_capacity
        base_network.edges[(bidirectional_link[1], bidirectional_link[0])].capacity = scenario_edge_capacity
        if scenario_edge_capacity < max(states.keys()):
            is_max = False
    return is_max

def postprocess_teavar(teavar_star_results, max_network, scenarios, beta):
    demand_flows = defaultdict(lambda: {})
    demand_losses = defaultdict(lambda: {})
    for var_name, var_val in teavar_star_results.items():
        if var_name.startswith('flow'):
            parsed = var_name.removeprefix('flow').split('on')
            flow_id = literal_eval(parsed[0])
            tunnel_id = parsed[1]
            demand_flows[flow_id][tunnel_id] = var_val
        elif var_name.startswith('loss'):
            parsed = var_name.removeprefix('loss').split('_')
            scenario_id = int(parsed[0])
            flow_id = literal_eval(parsed[1].removeprefix('flow'))
            new_var_val  = var_val
            if var_val < 0:
                new_var_val = 0
            demand_losses[flow_id][scenario_id] = new_var_val
    demand_flows = dict(demand_flows)
    demand_losses = dict(demand_losses)

    postproc_demand_flows = {}
    for demand_id in demand_flows:
        # Sort losses in ascending order
        sorted_losses = sorted(demand_losses[demand_id].items(), key=lambda item: item[1])
        i = 0
        prob_sum = 0
        while (prob_sum < beta):
            scenario_idx = sorted_losses[i][0]
            prob_sum += scenarios[scenario_idx][1]
            i += 1
        crossing_idx = i - 1
        assert crossing_idx >= 0
        assert crossing_idx < len(sorted_losses)
        if sorted_losses[crossing_idx][1] > max_network.demands[demand_id].amount:
            print("LOSS EXCEEDED DEMAND", sorted_losses[crossing_idx][1], max_network.demands[demand_id].amount)
        
        dmd_permitted = max(max_network.demands[demand_id].amount - sorted_losses[crossing_idx][1], 0)
        sum_over_tunnels = sum(demand_flows[demand_id].values())
        if sum_over_tunnels == 0:
            tunnel_weights = {tunnel:0 for tunnel in demand_flows[demand_id]}
        else:
            tunnel_weights = {tunnel:alloc/sum_over_tunnels for tunnel,alloc in demand_flows[demand_id].items()}
        for tunnel, weight in tunnel_weights.items():
            postproc_demand_flows[tunnel] = weight * dmd_permitted
    return postproc_demand_flows

def num_changed_allocations(old_allocations, new_allocations):
    changed_allocs_cnt = 0
    routers = set()
    for tunnel in old_allocations:
        if np.abs(new_allocations[tunnel] - old_allocations[tunnel]) > 0.01:
            changed_allocs_cnt += 1
            start_node = tunnel.split(":")[0]
            routers.add(start_node)
    
    return (changed_allocs_cnt, len(routers))

def num_nodes_affected_by_postproc(postproc_output):
    routers = set()
    for tunnel in postproc_output:
        if postproc_output[tunnel] > 0.01:
            start_node = tunnel.split(":")[0]
            routers.add(start_node)
    
    return len(routers)