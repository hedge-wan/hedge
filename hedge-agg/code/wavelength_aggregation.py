import numpy as np
import math

# The function generates the link's capacity distribution
# Input note: snr_thresholds is a list where index i corresponds to the minimum SNR needed to sustain a data rate of i * 50 Gbps
def gen_prob_dist(link_snrs, snr_thresholds):
    prob_dist = {}
    for snr in link_snrs:
        if snr <= 0.1:
            if 0 not in prob_dist:
                prob_dist[0] = 0
            prob_dist[0] += 1
            continue
        for i in reversed(range(len(snr_thresholds))):
            if snr > snr_thresholds[i]:
                if i * 50 not in prob_dist:
                    prob_dist[i * 50] = 0
                prob_dist[i * 50] += 1
                break
    
    prob_dist = {k: v / len(link_snrs) for k, v in prob_dist.items()}
    return prob_dist

# use the intuitive algorithm described in Section  of the paper to solve the wavelength aggregation problem
def bin_packing_algorithm(capacity_distribution, num_wavelengths, max_capacity, min_capacity, availability_pct):
    scenarios = []
    arg_scenarios = []

    sorted_capacity_dist = sorted(capacity_distribution.items(), reverse=True)
    for tup in sorted_capacity_dist:
        scenarios.append(tup[1])
        arg_scenarios.append(tup[0])
    
    prob_sum = 0
    index = None
    for i in range(len(scenarios)):
        prob_sum += scenarios[i]
        if prob_sum >= availability_pct:
            index = i
            break
    
    assert index is not None 

    # infeasible
    if arg_scenarios[index] == 0:
        return None

    assignments = {}

    assignments[arg_scenarios[index]] = math.ceil(min_capacity / arg_scenarios[index])
    capacity_covered = arg_scenarios[index] * assignments[arg_scenarios[index]]

    if index == 0:
        assignments[arg_scenarios[0]] += math.ceil((max_capacity - capacity_covered) / arg_scenarios[0])
    else:
        assignments[arg_scenarios[0]] = math.ceil((max_capacity - capacity_covered) / arg_scenarios[0])
    
    assert sum(assignments.values()) <= num_wavelengths

    for arg_val in arg_scenarios:
        if arg_val == 0: continue
        if arg_val not in assignments:
            assignments[arg_val] = 0

    return assignments

# use the formal LP in Appendix A.2 to solve the wavelength aggregation problem
def bin_packing_lp(data_rates, num_wavelengths, max_capacity, min_capacity, availability_pct):
    import gurobipy as gp
    model = gp.Model("LAG")
    
    data_rates = dict(sorted(data_rates.items(), reverse=True))
    decision_vars = []
    for data_rate in data_rates:
        decision_vars.append(model.addVar(lb=0, vtype=gp.GRB.INTEGER, name=str(data_rate)))
    
    objective = sum(decision_vars)
    model.setObjective(objective, gp.GRB.MINIMIZE)

    total_data_rate = 0
    for data_rate, var in zip(data_rates, decision_vars):
        total_data_rate += (data_rate * var)
    
    model.addConstr(total_data_rate == max_capacity)
    model.addConstr(sum(decision_vars) <= num_wavelengths)

    # pick the index that corresponds to availability target
    sorted_data_rates = list(data_rates.items())
    scenarios = []

    scenarios.append(np.prod([1 -x[1] for x in sorted_data_rates]))
    for i in range(len(sorted_data_rates)):
        prob = sorted_data_rates[i][1]
        for j in range(i+1, len(sorted_data_rates)):
            prob *= (1 - sorted_data_rates[j][1])
        scenarios.append(prob)
        
    prob_sum = 0
    index = None
    for i in range(len(scenarios)):
        prob_sum += scenarios[i]
        if prob_sum >= availability_pct:
            index = i
            break
    
    assert index is not None

    min_target = 0
    for j in range(index, len(decision_vars)):
        min_target += (sorted_data_rates[j][0] * decision_vars[j])
    
    model.addConstr(min_target >= min_capacity)

    model.optimize()
    model.update()

    return {v.VarName : v.X for v in model.getVars()}