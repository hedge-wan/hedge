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
- `snr_thresholds.pkl` contains the SNR cutoff thresholds to sustain different data rates for 50 GHz spectral width and 32 GBaud baud rate. The file contains a list in which the value at index $i$ is the minimum SNR needed to sustain a data rate of $50 * i Gbps$.

## HEDGE-TE
