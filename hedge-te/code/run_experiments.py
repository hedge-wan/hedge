from NetworkTopology import *
from NetworkParser import *
from solver import *
from util import *
import copy
from threading import Thread
import time
import pickle
import numpy as np

def setup(network_name, topology_filename, demand_filename, prob_threshold=0, demand_scale=1.0):
    scenarios = parse_stochastic_topology_for_teavar(network_name, topology_filename, prob_threshold)
    baseline_networks, _, _ = get_max_and_min_networks(network_name, topology_filename)
    assert len(baseline_networks) == 2
    total_demand = None
    for (network, prob) in baseline_networks:
        parse_demands(network, demand_filename, scale=demand_scale)
        if total_demand is None:
            total_demand = total_demand_requested_network(network)
        parse_tunnels(network)
    min_network = baseline_networks[0][0]
    max_network = baseline_networks[1][0]
    return scenarios, min_network, max_network, total_demand

def scale_demands(network, scale):
    for demand in network.demands.values():
        demand.amount *= scale

def changed_edges(old_network_state, new_network_state):
    flux = set()
    for e in old_network_state.edges:
        if old_network_state.edges[e].capacity == 0 or new_network_state.edges[e].capacity == 0:
            continue
        if old_network_state.edges[e].capacity != new_network_state.edges[e].capacity:
            flux.add(e)
    return flux

def run_simulation(scenarios, max_network, min_network, link_capacity_distributions, demand_scale, num_simulations, results):
    max_network_cpy = copy.deepcopy(max_network)
    min_network_cpy = copy.deepcopy(min_network)

    scale_demands(max_network_cpy, demand_scale)
    scale_demands(min_network_cpy, demand_scale)

    demand_tunnel_mapping = {}
    for demand in max_network_cpy.demands:
        demand_tunnel_mapping[demand] = [tunnel.name() for tunnel in max_network_cpy.demands[demand].tunnels]
    demand_amounts = {}
    for demand in max_network_cpy.demands:
        demand_amounts[demand] = max_network_cpy.demands[demand].amount
    edge_tunnel_mapping = {}
    for edge in max_network_cpy.edges:
        edge_tunnel_mapping[edge] = [tunnel.name() for tunnel in max_network_cpy.edges[edge].tunnels]
    edge_capacities = {}
    for edge in max_network_cpy.edges:
        edge_capacities[edge] = int(max_network_cpy.edges[edge].capacity)
    tunnels_used = set()
    for tunnels in demand_tunnel_mapping.values():
        for tunnel in tunnels:
            tunnels_used.add(tunnel)

    max_results = solve_max_throughput(max_network_cpy)

    min_results = solve_max_throughput(min_network_cpy)

    directional_link_capacity_distributions = {}
    for edge, states in link_capacity_distributions.items():
        directional_link_capacity_distributions[(edge[0], edge[1])] = states.copy()
        directional_link_capacity_distributions[(edge[1], edge[0])] = states.copy()
    
    hedge_results = solve_hedge(max_network_cpy, directional_link_capacity_distributions)
    print(f"{demand_scale}x: solved hedge")
    teavar50_results = solve_teavar_star(scenarios, max_network_cpy, 0.5)
    teavar50_allocations = postprocess_teavar(teavar50_results, max_network_cpy, scenarios, 0.5)
    print(f"{demand_scale}x: solved teavar 50")
    teavar90_results = solve_teavar_star(scenarios, max_network_cpy, 0.9)
    teavar90_allocations = postprocess_teavar(teavar90_results, max_network_cpy, scenarios, 0.9)
    print(f"{demand_scale}x: solved teavar 90")

    radwan_results = solve_radwan(demand_tunnel_mapping, edge_tunnel_mapping, edge_capacities, demand_amounts)
    print("solved initial radwan")

    max_allocations = get_tunnel_allocations(max_results)
    min_allocations = get_tunnel_allocations(min_results)
    hedge_allocations = get_tunnel_allocations(hedge_results)
    radwan_allocations = get_tunnel_allocations(radwan_results)

    naive_max_throughput = sum(max_allocations.values())
    naive_min_throughput = sum(min_allocations.values())
    hedge_throughput = sum(hedge_allocations.values())
    teavar50_throughput = sum(teavar50_allocations.values())
    teavar90_throughput = sum(teavar90_allocations.values())
    radwan_throughputs = [sum(radwan_allocations.values())]

    naive_max_overflow = []
    naive_min_overflow = []
    hedge_overflow = []
    teavar50_overflow = []
    teavar90_overflow = []
    radwan_overflow = []
    max_state = []

    naive_max_recomputations = 0
    naive_min_recomputations = 0
    hedge_recomputations = 0
    teavar50_recomputations = 0
    teavar90_recomputations = 0
    radwan_recomputations = 0

    prev_state = copy.deepcopy(max_network_cpy)

    for i in range(1, num_simulations + 1):
        is_max = simulate_network_state(max_network_cpy, link_capacity_distributions)
        max_state.append(is_max)
       
        if i % 5 == 0:
            edges_that_changed = changed_edges(prev_state, max_network_cpy)
            if len(edges_that_changed) > 0:
                for edge in max_network_cpy.edges:
                    edge_capacities[edge] = int(max_network_cpy.edges[edge].capacity)
                for edge in edges_that_changed:
                    edge_capacities[edge] = 0
                radwan_results = solve_radwan(demand_tunnel_mapping, edge_tunnel_mapping, edge_capacities, demand_amounts)
                radwan_recomputations += 1
                radwan_allocations = get_tunnel_allocations(radwan_results)
                radwan_throughputs.append(sum(radwan_allocations.values()))
                prev_state = copy.deepcopy(max_network_cpy)

        max_edge_util, max_raw_overflow = edge_coverage(max_network_cpy, max_allocations)
        min_edge_util, min_raw_overflow = edge_coverage(max_network_cpy, min_allocations)
        hedge_edge_util, hedge_raw_overflow = edge_coverage(max_network_cpy, hedge_allocations)
        teavar50_edge_util, teavar50_raw_overflow = edge_coverage(max_network_cpy, teavar50_allocations)
        teavar90_edge_util, teavar90_raw_overflow = edge_coverage(max_network_cpy, teavar90_allocations)
        radwan_edge_util, radwan_raw_overflow = edge_coverage(max_network_cpy, radwan_allocations)

        if max_raw_overflow >= 1:
            max_lp_postproc = postprocess(max_network_cpy, max_allocations, prepare_postprocessing(max_network_cpy, max_edge_util))
            naive_max_recomputations += 1
            naive_max_overflow.append(sum(max_lp_postproc.values()))
        else:
            naive_max_overflow.append(0)

        if min_raw_overflow >= 1:
            min_lp_postproc = postprocess(max_network_cpy, min_allocations, prepare_postprocessing(max_network_cpy, min_edge_util))
            naive_min_recomputations += 1
            naive_min_overflow.append(sum(min_lp_postproc.values()))
        else:
            naive_min_overflow.append(0)
    
        if hedge_raw_overflow >= 1:
            hedge_lp_postproc = postprocess(max_network_cpy, hedge_allocations, prepare_postprocessing(max_network_cpy, hedge_edge_util))
            hedge_recomputations += 1
            hedge_overflow.append(sum(hedge_lp_postproc.values()))
        else:
            hedge_overflow.append(0)
        
        if teavar50_raw_overflow >= 1:
            teavar50_lp_postproc = postprocess(max_network_cpy, teavar50_allocations, prepare_postprocessing(max_network_cpy, teavar50_edge_util))
            teavar50_recomputations += 1
            teavar50_overflow.append(sum(teavar50_lp_postproc.values()))
        else:
            teavar50_overflow.append(0)

        if teavar90_raw_overflow >= 1:
            teavar90_lp_postproc = postprocess(max_network_cpy, teavar90_allocations, prepare_postprocessing(max_network_cpy, teavar90_edge_util))
            teavar90_recomputations += 1
            teavar90_overflow.append(sum(teavar90_lp_postproc.values()))
        else:
            teavar90_overflow.append(0)
        
        if radwan_raw_overflow >= 1:
            radwan_lp_postproc = postprocess(max_network_cpy, radwan_allocations, prepare_postprocessing(max_network_cpy, radwan_edge_util))
            radwan_recomputations += 1
            radwan_overflow.append(sum(radwan_lp_postproc.values()))
        else:
            radwan_overflow.append(0)
        
        if (i+1) % 100 == 0:
            print(f"Current progress for {demand_scale}x:", i+1)
    
    results[demand_scale] = {
        'naive_optimistic_throughput': naive_max_throughput,
        'naive_pessimistic_throughput': naive_min_throughput,
        'hedge_throughput': hedge_throughput,
        'teavar50_throughput': teavar50_throughput,
        'teavar90_throughput': teavar90_throughput,
        'radwan_throughput': np.mean(radwan_throughputs),
        'naive_optimistic_reductions': naive_max_overflow,
        'naive_pessimistic_reductions': naive_min_overflow,
        'hedge_reductions': hedge_overflow,
        'teavar50_reductions': teavar50_overflow,
        'teavar90_reductions': teavar90_overflow,
        'radwan_reductions': radwan_overflow,
        'naive_optimistic_runs': naive_max_recomputations,
        'naive_pessimistic_runs': naive_min_recomputations,
        'hedge_runs': hedge_recomputations,
        'teavar50_runs': teavar50_recomputations,
        'teavar90_runs': teavar90_recomputations,
        'radwan_runs': radwan_recomputations,
        'is_max_state': max_state
    }
    print(f"{demand_scale}x demand scale completed")


TEAVAR_PROB_THRESHOLD = 0.005  # Set by you based on the topology (if you are comparing to Teavar). This is the probability threshold at which we prune a capacity state, for Teavar only.
DEMAND_SCALES = [0.1, 0.3, 0.5, 1, 3]
NUM_SIMULATIONS = 1000
sys.setrecursionlimit(10000)

if len(sys.argv) != 4:
    print("Usage: python run_experiments.py <path_to_stochastic_topology_file> <path_to_demand_file> <path_to_results_file>")
    sys.exit(1)

topology_filename = sys.argv[1]

demand_filename = sys.argv[2]

path_to_results_file = sys.argv[3]

scenarios, min_network, max_network, total_demand = setup("b4", topology_filename, demand_filename, prob_threshold=TEAVAR_PROB_THRESHOLD)
total_prob = sum([scenario[1] for scenario in scenarios])
print("teavar total probability covered", total_prob)
assert total_prob >= 0.9

link_capacity_distributions = get_link_capacity_distributions_with_filename(topology_filename)

results = {}
threads = []
start_time = time.time()
for demand_scale in DEMAND_SCALES:
    t = Thread(target=run_simulation, args=(scenarios, max_network, min_network, link_capacity_distributions, demand_scale, NUM_SIMULATIONS, results))
    t.start()
    threads.append(t)
print("All threads have started running")

for t in threads:
    t.join()

print("All threads have finished running")
print("Elapsed seconds:", time.time() - start_time)

with open(path_to_results_file, 'wb') as outf:
    pickle.dump(results, outf)