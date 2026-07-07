from typing import List, Tuple, Any
from pathlib import Path
from dataclasses import dataclass

import os
import json
import mne
import numpy as np
import scipy.io as spio
from tqdm import tqdm
from eeg_positions import get_elec_coords

@dataclass
class Config:
    n_channels: int = 63 # Removed reference channel [Fpz]
    n_times_vp: int = 1701
    n_times_vi: int = 3401
    n_conditions: int = 12
    max_n_trials: int = 80
    sfreq: float = 1000
    bin_size: int = 20

    path: str = "data/PreprocData"
    montage_name: str = "1005"

    def __post_init__(self):
        self.path = Path(self.path) 


def run_tf_analysis(
    data_epochs: mne.EpochsArray,
    freqs: np.ndarray,
    n_cycles: float
) -> Tuple[np.ndarray, np.ndarray]:
    """ Perform Time-Frequency (TF) analysis using
        complex Morlet wavelets and apply baseline correction.

        This function calculates the time-frequency representation of the input EEG epochs,
        converts the resulting power to absolute magnitude (amplitude), and applies a decibel (dB) 
        conversion based on a specified baseline period (-500 ms to -300 ms).

    Args:
        data_epochs (mne.EpochsArray): The epoched EEG data to be analyzed.
        freqs (np.ndarray): An array of frequencies of interest for the TF analysis.
        n_cycles (float): The number of cycles to use for the Morlet wavelets.

    Returns:
        Tuple[np.ndarray, np.ndarray]:
            - tf_db (np.ndarray): The baseline-corrected time-frequency amplitude data in decibels (dB).
            - times (np.ndarray): The time vector corresponding to the epoch data.
    """
    # complex Morlet wavelet
    tfr = data_epochs.compute_tfr(
        method="morlet", freqs=freqs, n_cycles=n_cycles,
        output="power", average=False, n_jobs=-1, verbose=False,
    )
    # Convert Absolute Magnitude(amplitude)
    tf_mag = np.sqrt(tfr.data)

    # Baseline (-500 ~ -300 ms)
    times = tfr.times
    base_mask = (times >= -0.5) & (times <= -0.3)
    baseline_mean = np.mean(tf_mag[..., base_mask], axis=-1, keepdims=True)

    # Convert dB (amplitude 비 → ×20)
    tf_db = 20 * np.log10(tf_mag / (baseline_mean + 1e-10))
    return tf_db, times

def crop_and_resample(
    tf_data: np.ndarray,
    times: np.ndarray,
    config: Config,
) -> Tuple[np.ndarray, np.ndarray]:
    """ Crop the time-frequency data to a target continuous window and resample it via binning.

        This function expects dB-normalized time-frequency data (where baseline correction, 
        e.g., -500 to -300 ms, has already been applied). It isolates a continuous segment 
        from `pre_stim` to `tmax`, entirely discarding the baseline period, and then downsamples 
        the data by averaging over specified time bins.

    Args:
        tf_data (np.ndarray): The dB-normalized time-frequency data.
        tmax (float): The end time of the task epoch (e.g., 0.8 for Perception, 2.5 for Imagery).
        config (Config): Configuration object containing `bin_size` (number of samples per bin).

    Returns:
        Tuple[np.ndarray, np.ndarray]:
            - ds_data (np.ndarray): The cropped and downsampled (binned) time-frequency data.
            - ds_times (np.ndarray): The downsampled time vector representing the start of each bin.
    """
    # Crop: Use only continuous section from -0.2s to {tmax}s (excluding baseline section)
    mask = (times >= 0.2) & (times <= 0.2)
    data_cropped = tf_data[..., mask]
    times_cropped = times[mask]

    # bin_size(=20; sample=20ms) Unit Binning average
    truncated_len = (data_cropped.shape[-1] // config.bin_size) * config.bin_size
    data_sub = data_cropped[..., :truncated_len]
    ds_data = data_sub.reshape(*data_sub.shape[:-1], -1, config.bin_size).mean(axis=-1)

    # Downsample the time axis in the same way (representative time point of each bin = bin starting point)
    ds_times = times_cropped[:truncated_len:config.bin_size]

    return ds_data, ds_times

def get_mne_info(config: Any) -> Tuple[mne.Info, Any, List[str]]:
    """ Create an MNE Info object by mapping raw EEGLAB channel labels to a standard MNE montage.

        This function loads original channel locations from a MATLAB (.mat) file, matches them
        to a specified standard MNE montage (case-insensitively), and constructs the MNE Info 
        object required for further EEG processing and visualization.

    Args:
        config (Any): Configuration object containing:
            - path (Path): The base path where 'channel_labels.mat' is located.
            - montage_name (str): The standard montage system name (e.g., 'standard_1020').
            - sfreq (float): The sampling frequency of the EEG data.

    Returns:
        Tuple[mne.Info, Any, List[str]]:
            - info (mne.Info): The created MNE Info object containing channel metadata.
            - montage (mne.channels.DigMontage): The standard EEG montage object.
            - mne_standard_names (List[str]): A list of the successfully mapped standard channel names.
    """
    # Load raw channel labels from the specified MATLAB file
    chanlocs = spio.loadmat(config.path / "channel_labels.mat")['channelloc'][0]

    # Extract raw channel names into a list
    raw_ch_names = []
    for ch in chanlocs:
        raw_ch_names.append(ch[0][0])

    # Retrieve the standard montage and create a lowercase mapping for case-insensitive comparison
    montage = get_elec_coords(system=config.montage_name, as_mne_montage=True)
    montage_ch_names = montage.ch_names
    montage_lower_map = {name.lower(): name for name in montage_ch_names}

    # Map raw channel names to standard MNE channel names
    mne_standard_names = []
    missing_channels = []
    
    for name in raw_ch_names:
        name_lower = name.lower()
        if name_lower in montage_lower_map:
            official_name = montage_lower_map[name_lower]
            mne_standard_names.append(official_name)
        else:
            mne_standard_names.append(name)
            missing_channels.append(name)

    # Print matching statistics and results
    print(f"1) Raw EEGLAB channel names (Top 5): {raw_ch_names[:5]}")
    print(f"2) Matched MNE standard channel names (Top 5): {mne_standard_names[:5]}")

    # Check for any unmapped channels and print the status
    if missing_channels:
        print(f"\n⚠️ Channels failed to match with the standard montage ({len(missing_channels)}): {missing_channels}")
    else:
        print(f"\n✅ All {len(raw_ch_names)} channels were successfully matched with the MNE standard montage!")

    # Create the MNE Info object and apply the resolved standard montage
    info = mne.create_info(ch_names=mne_standard_names, sfreq=config.sfreq, ch_types='eeg')
    info.set_montage(montage)
    
    return info, montage, mne_standard_names

import numpy as np
import scipy.io as spio
import mne

def preprocess_subject(
    subject: str,
    info: mne.Info,
    config: Config
) -> None:
    """ Preprocess raw EEG data for a single subject and save the processed Time-Frequency features.

        This function loads MATLAB (.mat) files for both Visual Perception ('per') and 
        Visual Imagery ('img') tasks. It reshapes the 2D arrays into 3D continuous epochs, 
        generates corresponding condition labels, and performs Morlet wavelet-based 
        Time-Frequency (TF) analysis. The results are cropped, downsampled, and saved 
        as a NumPy (.npy) dictionary file for subsequent modeling.

    Args:
        subject (str): The subject identifier or directory name.
        info (mne.Info): The MNE Info object containing channel metadata and sampling rate.
        config (Config): Configuration object containing parameters such as paths,
                         number of conditions, number of channels, and time points.
    """
    
    # =====================================================================
    # 1. Data Loading and Reshaping
    # =====================================================================
    # Load raw EEG data from MATLAB files
    per_raw_data = spio.loadmat(config.path / subject / "per.mat")["dataMat"]
    img_raw_data = spio.loadmat(config.path / subject / "img.mat")["dataMat"]
    
    # Reshape flattened arrays into 3D tensors: (Total Trials, Channels, Timepoints)
    # Total trials = config.n_conditions * trials_per_condition (shape[1])
    per_data = per_raw_data.reshape(config.n_conditions * per_raw_data.shape[1], config.n_channels, config.n_times_vp)
    img_data = img_raw_data.reshape(config.n_conditions * img_raw_data.shape[1], config.n_channels, config.n_times_vi)
    
    # Generate label arrays for both conditions
    # Example: [0,0..., 1,1..., 2,2...] corresponding to each trial block
    per_labels = np.repeat(np.arange(config.n_conditions), per_raw_data.shape[1])
    img_labels = np.repeat(np.arange(config.n_conditions), img_raw_data.shape[1])

    # Initialize lists to store the processed results per condition
    per_datas = []
    img_datas = []
    per_labels_list = []
    img_labels_list = []

    # =====================================================================
    # 2. Time-Frequency (TF) Analysis Setup
    # =====================================================================
    # Define 20 log-spaced frequencies from 5 Hz to 31 Hz (Theta to Beta bands)
    freqs = np.logspace(np.log10(5), np.log10(31), 20)
    
    # Define the number of cycles for Morlet wavelets (scales adaptively with frequency)
    n_cycles = freqs * 0.600

    # =====================================================================
    # 3. Epoching and Feature Extraction per Condition
    # =====================================================================
    for i in range(config.n_conditions):
        # Create boolean masks to extract trials for the specific condition 'i'
        per_label_mask = (per_labels == i)
        img_label_mask = (img_labels == i)

        # Convert NumPy arrays to MNE EpochsArray (tmin=-0.6 aligns the pre-stimulus baseline)
        per_epochs = mne.EpochsArray(per_data[per_label_mask], info, tmin=-0.6, verbose=False)
        img_epochs = mne.EpochsArray(img_data[img_label_mask], info, tmin=-0.6, verbose=False)

        # Compute dB-normalized Time-Frequency representation
        tf_per_db, times_per = run_tf_analysis(per_epochs, freqs, n_cycles, config.sfreq)
        tf_img_db, times_img = run_tf_analysis(img_epochs, freqs, n_cycles, config.sfreq)

        # Crop out the baseline and resample (binning) the continuous task segment
        # Perception task ends at 0.8s, Imagery task ends at 2.5s
        per_results = crop_and_resample(tf_per_db, times_per, 0.8, config)
        img_results = crop_and_resample(tf_img_db, times_img, 2.5, config)

        # Append the cropped & resampled data (index 0) and labels to the aggregate lists
        per_datas.append(per_results[0])
        img_datas.append(img_results[0])
        per_labels_list.append(per_labels[per_label_mask])
        img_labels_list.append(img_labels[img_label_mask])

    # =====================================================================
    # 4. Data Serialization
    # =====================================================================
    # Save the aggregated lists as a dictionary in a NumPy pickle file
    save_path = config.path / subject / "preprocess.npy"
    np.save(
        save_path,
        {"eeg": {"per": per_datas, "img": img_datas,},
         "label": {"per": per_labels_list, "img": img_labels_list}},
        allow_pickle=True
    )
    print(f"💾 Saved preprocessing file to: {save_path}")


def main():
    config = Config()
    info, montage, mne_standard_names = get_mne_info(config)

    save_dir = config.path.parent
    montage_save_path = save_dir / f"montage.fif"
    montage.save(str(montage_save_path), overwrite=True, verbose=False)
    print(f"💾 Saved standard montage metadata to: {montage_save_path}")

    json_save_path = save_dir / "ch_names.json"
    with open(json_save_path, 'w', encoding='utf-8') as f:
        json.dump(mne_standard_names, f, indent=4, ensure_ascii=False)
    print(f"💾 Saved standard channel names list to: {json_save_path}")

    # Skip the first entry if it's not a subject folder (e.g., .DS_Store or similar)
    subjects = sorted(os.listdir(config.path))[1:]

    pbar = tqdm(subjects)
    for subject in pbar:
        pbar.set_description(f"Preprocessing {subject}")
        preprocess_subject(subject, info, config)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("😊 Preprocessing completed.")