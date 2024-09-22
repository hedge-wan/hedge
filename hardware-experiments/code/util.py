import csv
import os

def parse_transponder_data(file_path):
    timestamps = []
    bit_error_rates = {}
    powers = {}
    fec_counters = {}

    with open(file_path, 'r') as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            channel = int(row[1])
            if float(row[0]) not in timestamps:
                timestamps.append(float(row[0]))
            if channel not in bit_error_rates:
                bit_error_rates[channel] = []
                fec_counters[channel] = []
                powers[channel] = []
            bit_error_rates[channel].append(float(row[2]))
            fec_counters[channel].append(float(row[3]))
            powers[channel].append(float(row[4]))
    
    sorted_bers = {}
    for channel in bit_error_rates:
        assert len(bit_error_rates[channel]) == len(timestamps)
        sorted_bers[channel] = [x[1] for x in sorted(zip(timestamps, bit_error_rates[channel]))]
    sorted_fecs = {}
    for channel in fec_counters:
        assert len(fec_counters[channel]) == len(timestamps)
        sorted_fecs[channel] = [x[1] for x in sorted(zip(timestamps, fec_counters[channel]))]
    sorted_powers = {}
    for channel in powers:
        assert len(powers[channel]) == len(timestamps)
        sorted_powers[channel] = [x[1] for x in sorted(zip(timestamps, powers[channel]))]
    return sorted(timestamps), sorted_bers, sorted_fecs, sorted_powers

def get_bw_lists(log_file_path):
    times = []
    bw = []
    log_idx = 0
    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            if 'Initial timestamp:' in line:
                parts = line.split()
                continue
            if 'SUM' in line:
                parts = line.split('|')
                time_val = float(parts[0])
                data_parts = parts[1].split()
                bw_val = float(data_parts[5])
                if data_parts[6] == 'Mbits/sec':
                    bw_val /= 1000
                times.append(time_val / 1000)
                bw.append(bw_val)
                log_idx += 1
    
    return times, bw

def get_layer3_data(directory):
    layer3_files = ['server1.log', 'server2.log', 'server3.log', 'server4.log']
    bw_lists = []
    time_lists = []

    for layer3_file in layer3_files:
        layer3_file_path = os.path.join('../data', directory, layer3_file)
        times, bw = get_bw_lists(layer3_file_path)
        time_lists.append(times)
        bw_lists.append(bw)
    
    layer3_list_len = min([len(bw_list) for bw_list in bw_lists])
    
    link_states = []
    link_state_times = []

    for idx in range(layer3_list_len):
        total_bw = 0
        for bw_list in bw_lists:
            total_bw += bw_list[idx]
        if total_bw > 0:
            link_states.append(1)
        else:
            link_states.append(0)
        link_state_times.append(time_lists[0][idx])

    return link_state_times, link_states