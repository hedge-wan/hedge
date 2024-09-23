# HEDGE
## Hardware Experiments
Code and data for hardware experiments are available in the `hardware-experiments/` folder. The only requirements are `numpy` and `matplotlib`. 
- `fiber_bend_wavelengths.ipynb` generates Figures 4a and 4b. The data for this experiment can be found in the `hardware-experiments/data/wdl/` folder.
- `fiber_bend_modulation_formats.ipynb` generates Figure 4c. The data for this experiment can be found in the `hardware-experiments/data/mod_formats/` folder.
- `prototype.ipynb` generates Figure 7b and 7c. The data for this experiment can be found in the `hardware-experiments/data/prototype/` folder.

Note: All `transponder_data.csv` files are in `timestamp, channel, ber, fec, input_power` format.

## HEDGE-AGG Software
Code and data for the software evaluation of HEDGE-AGG are available in the `hedge-agg/` folder. The requirements are `pickle`, `matplotlib`, and `numpy`.
- `analysis.ipynb` generates all subplots for Figure 6.
- `snr_data.pkl` contains real SNR data collected over 15 minute intervals for several months in an ISP WAN. This file contains a dictionary in which each key is an anonymized wavelength identifier and each value is a list of SNR values for that wavelength (in chronological order).
- `snr_thresholds.pkl` contains the SNR cutoff thresholds to sustain different data rates for 50 GHz spectral width and 32 GBaud baud rate. The file contains a list in which the value at index $i$ is the minimum SNR needed to sustain a data rate of $50 * i$ Gbps.

## HEDGE-TE
Code and data for the evaluation of HEDGE-TE are available in the `hedge-te/` folder. The requirements are `gurobipy` (Python API for the Gurobi Optimizer), `pickle`, `matplotlib`, and `numpy`. Our results for the B4 and ATT topologies can be visualized easily by running the `analyze_results.ipynb` notebook. For more advanced users, we delineate the following:
- Raw results from our evaluations on B4 and ATT are available in the `hedge-te/data/results/<topology>` folders (`analyze_results.ipynb` directly queries these). There are 10 results files for each topology since we ran the 1000 simulations for each of the 10 random permutations (of the capacity distribution-to-link mapping) for each topology.
- To run our extensive experiments from scratch yourself, you can run the `run_experiments.py` script, which has the usage: `python run_experiments.py <path_to_stochastic_topology_file> <path_to_demand_file> <path_to_results_file>`. The demand matrix and fixed topology (just showing the network structure, without link capacity distributions) files for B4 and ATT are available in the `hedge-te/data/inputs/<topology>` folders. `<path_to_results_file>` is completely up to your choosing.

Unfortunately, we are not yet able to provide data for CloudWAN due to confidentiality requirements, so we cannot provide the link capacity distributions for all topologies, since these are directly matched from CloudWAN data for link capacity fluctuations. To create your own stochastic topology (i.e., the first command-line argument for `run_experiments.py` script), you can create a `pickle` file containing a `dict` with format `{<directed_edge>: {<capacity1>: <prob1>, <capacity2>, <prob2>,...}, ...}` where the `<directed_edge>` key is a `(str, str)` tuple for a WAN link and the value is a `dict` mapping capacities (in Gbps) to probabilities for that link. For example, `{('1', '2'): {1000: 0.99, 800: 0.009, 0: 0.001}, ('2', '1'): {1000: 0.995, 500: 0.005}}`.

Demands and topologies for ATT and B4 are directly sourced from the [TeaVaR repository](https://github.com/manyaghobadi/teavar/tree/master).
