from gurobipy import *

def get_bw_objective(flows):
    objective = 0
    for flows_over_tunnels in flows.values():
        objective += sum(flows_over_tunnels.values())
    return objective

def solve_hedge(max_network, edge_distributions, edge_weights=None):
    edge_capacities = {}
    for e, edge in max_network.edges.items():
        edge_capacities[e] = int(edge.capacity)
    
    if edge_weights is None:
        edge_weights = {}
        for e in max_network.edges:
            edge_weights[e] = 1
    
    model = Model("hedge")

    # intialize flow variables
    flows = {}
    for demand_id, demand in max_network.demands.items():
        tunnel_flows = {}
        for tunnel in demand.tunnels:
            tunnel_flows[tunnel.name()] = model.addVar(lb = 0, name = f"flow{demand_id}on{tunnel.name()}")
        flows[demand_id] = tunnel_flows

    objective = 0
    for demand_id, demand in max_network.demands.items():
        if demand.amount == 0: continue
        for tunnel in demand.tunnels:
            objective += flows[demand_id][tunnel.name()]
    
    for edge, states in edge_distributions.items():
        for capacity, prob in states.items():
            sum_over_tunnels = 0
            for tunnel in max_network.edges[edge].tunnels:
                demand_id = (tunnel.path[0].e[0], tunnel.path[len(tunnel.path) - 1].e[1])
                if demand_id not in flows: continue
                sum_over_tunnels += flows[demand_id][tunnel.name()]
            edge_name = "-".join(edge)
            slack = model.addVar(lb=0, name = f"slack{edge_name}state{capacity}")
            differential = model.addVar(lb=-GRB.INFINITY, name = f"diff{edge_name}state{capacity}")
            model.addConstr(differential == sum_over_tunnels - capacity)
            model.addConstr(slack == max_(differential, constant=0))
            objective -= (edge_weights[edge] * prob * slack)
    
    model.setObjective(objective, GRB.MAXIMIZE)

    # demand constraints
    for demand_id, demand in max_network.demands.items():
        flow_on_tunnels = sum([flows[demand_id][tunnel.name()] for tunnel in demand.tunnels])
        model.addConstr(flow_on_tunnels <= demand.amount)

    # edge capacity constraints
    for edge in max_network.edges.values():
        flow_on_tunnels = 0
        for tunnel in edge.tunnels:
            for demand_id, tunnel_list in flows.items():
                if tunnel.name() in tunnel_list:
                    flow_on_tunnels += flows[demand_id][tunnel.name()]
        model.addConstr(flow_on_tunnels <= edge_capacities[(edge.e[0], edge.e[1])])

    model.optimize()
    model.update()

    return {v.VarName : v.X for v in model.getVars()}

def solve_max_throughput(network):
    edge_capacities = {}
    for e, edge in network.edges.items():
        edge_capacities[e] = int(edge.capacity)
    model = Model("basic")
    
    # intialize flow variables
    flows = {}
    for demand_id, demand in network.demands.items():
        tunnel_flows = {}
        for tunnel in demand.tunnels:
            tunnel_flows[tunnel.name()] = model.addVar(lb = 0, name = f"flow{demand_id}on{tunnel.name()}")
        flows[demand_id] = tunnel_flows

    # demand constraints
    for demand_id, demand in network.demands.items():
        flow_on_tunnels = sum([flows[demand_id][tunnel.name()] for tunnel in demand.tunnels])
        model.addConstr(flow_on_tunnels <= demand.amount)
    
    # capacity constraints
    for edge in network.edges.values():
        flow_on_tunnels = 0
        for tunnel in edge.tunnels:
            for demand_id, tunnel_list in flows.items():
                if tunnel.name() in tunnel_list:
                    flow_on_tunnels += flows[demand_id][tunnel.name()]
        assert flow_on_tunnels is not None
        assert edge.capacity is not None
        model.addConstr(flow_on_tunnels <= edge_capacities[(edge.e[0], edge.e[1])])

    objective = get_bw_objective(flows)
    model.setObjective(objective, GRB.MAXIMIZE)
    model.optimize()
    model.update()
    return {v.VarName : v.X for v in model.getVars()}


def solve_radwan(demand_tunnel_mapping, edge_tunnel_mapping, edge_capacities, demand_amounts):
    model = Model("radwan")
    
    # intialize flow variables
    flows = {}
    for demand_id, tunnels in demand_tunnel_mapping.items():
        tunnel_flows = {}
        for tunnel in tunnels:
            tunnel_flows[tunnel] = model.addVar(lb = 0, name = f"flow{demand_id}on{tunnel}")
        flows[demand_id] = tunnel_flows

    # demand constraints
    for demand_id, amount in demand_amounts.items():
        flow_on_tunnels = sum([flows[demand_id][tunnel] for tunnel in demand_tunnel_mapping[demand_id]])
        model.addConstr(flow_on_tunnels <= amount)

    # capacity constraints
    for edge, tunnels in edge_tunnel_mapping.items():
        flow_on_tunnels = 0
        for tunnel in tunnels:
            for demand_id, tunnel_list in flows.items():
                if tunnel in tunnel_list:
                    flow_on_tunnels += flows[demand_id][tunnel]
        model.addConstr(flow_on_tunnels <= edge_capacities[edge])

    objective = get_bw_objective(flows)
    model.setObjective(objective, GRB.MAXIMIZE)
    model.optimize()
    model.update()
    return {v.VarName : v.X for v in model.getVars()}

def postprocess(network, allocations, overflow_set):
    model = Model("postprocess")

    epsilons = {}
    for tunnel in allocations:
        epsilons[tunnel] = model.addVar(lb = 0, name = tunnel)
    
    model.setObjective(sum(epsilons.values()), GRB.MINIMIZE)

    for e, tunnels in overflow_set.items():
        flow_on_tunnels = 0
        for tunnel in tunnels:
            if tunnel in allocations:
                flow_on_tunnels += (allocations[tunnel] - epsilons[tunnel])
        model.addConstr(flow_on_tunnels <= network.edges[e].capacity)
    
    model.optimize()
    model.update()
    return {v.VarName : v.X for v in model.getVars()}

def solve_teavar_star(scenarios, max_network, beta):
    edge_capacities = {}
    for e, edge in max_network.edges.items():
        edge_capacities[e] = int(edge.capacity)
    model = Model("TeaVaR*")
    alpha = model.addVar(lb = 0, name = "alpha")

    # A tunnel is enabled if all edges along the tunnel are operating at their max capacity
    def enabled(scenario, t):
        return all(scenario.edges[edge.e].relative_capacity == 1 for edge in t.path)

    # intialize flow variables
    flows = {}
    for demand_id, demand in max_network.demands.items():
        tunnel_flows = {}
        for tunnel in demand.tunnels:
            tunnel_flows[tunnel.name()] = model.addVar(lb = 0, name = f"flow{demand_id}on{tunnel.name()}")
        flows[demand_id] = tunnel_flows

    qs = [(i, scenario[0], scenario[1], model.addVar(lb = 0, name = f"slack{i}")) for i, scenario in enumerate(scenarios)]
    f_beta =  alpha + ((1.0 / (1.0 - beta)) * (sum(prob * slack for (i, scenario, prob, slack) in qs) + ((1 - sum(prob for i, scenario, prob, slack in qs)) * alpha)))
    model.setObjective(f_beta, GRB.MINIMIZE)

    scenario_cnt = 0
    for (i, scenario, prob, slack) in qs:
        t_q = 0
        for demand_id, demand in max_network.demands.items():
            if demand.amount == 0: continue
            loss = model.addVar(lb = 0, name=f"loss{i}_flow{demand_id}")
            sum_over_tunnels = 0
            for tunnel in demand.tunnels:
                tunnel_flow = 0
                if enabled(scenario, tunnel):
                    tunnel_flow = flows[demand_id][tunnel.name()]
                sum_over_tunnels += tunnel_flow
            model.addConstr(loss >= (demand.amount - sum_over_tunnels))
            t_q += loss
        model.addConstr(slack >= t_q - alpha)
        scenario_cnt += 1
    
    # demand constraints
    for demand_id, demand in max_network.demands.items():
        flow_on_tunnels = sum([flows[demand_id][tunnel.name()] for tunnel in demand.tunnels])
        model.addConstr(demand.amount >= flow_on_tunnels)
    
    # edge capacity constraints
    for edge in max_network.edges.values():
        flow_on_tunnels = 0
        for tunnel in edge.tunnels:
            for demand_id, tunnel_list in flows.items():
                if tunnel.name() in tunnel_list:
                    flow_on_tunnels += flows[demand_id][tunnel.name()]
        model.addConstr(flow_on_tunnels <= edge_capacities[(edge.e[0], edge.e[1])])

    model.optimize()
    model.update()

    return {v.VarName : v.X for v in model.getVars()}