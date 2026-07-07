# xie2020-eeg
This repository was created to reproduce experiments in</br>
[Visual Imagery and Perception Share Neural Representations in the Alpha Frequency Band](https://www.sciencedirect.com/science/article/pii/S096098222030590X)

## Environment Setting
1. Create environment
```
conda create neuro python=3.10
conda activate neuro
```
2. Install libraries
```
pip install -r requirements.txt
```

## Data available

### Download
Data is provided at [https://osf.io/ykp9w/](https://osf.io/ykp9w/overview).
To download, run the command below.
```
chmod +x data_download.sh
./data_download.sh
```

### Directory
```
data
├── PreprocData
│   ├── subj01
│   │   ├── img.mat            # Imagery EEG
│   │   ├── info_channel.mat   # EEG Channel Information
│   │   └── per.mat            # Perception EEG
│   ├── subj02
│   ├── ...
│   ├── subj38
│   └── channel_labels.mat
├── RawData
│   ├── subj01
│   │   ├── img   # Imagery
│   │   │   ├── xxx.eeg   # binary data file, containing the voltage values of the EEG
│   │   │   ├── xxx.vhdr  # text header file, containing the meta data
│   │   │   └── xxx.vmrk  # text marker file, containing information about events
│   │   └── per   # Perception
│   │   │   ├── xxx.eeg
│   │   │   ├── xxx.vhdr
│   │   │   └── xxx.vmrk
│   ├── subj02
│   ├── ...
│   └── subj38
└── readme.txt   # Data Description
```


## Data preprocessing
Run the script below for preprocessing. This step operates on `PreprocData` (already filtered/ICA-cleaned),</br>
not raw EEG. `preprocess_data.py` applies Morlet wavelet time-frequency analysis and</br>
baseline dB normalization to the data, then crops and downsamples the result before saving it as a `.npy` file.
```
python preprocess_data.py
```

## Reference
```
Xie, Siying, Daniel Kaiser, and Radoslaw M. Cichy.
"Visual imagery and perception share neural representations in the alpha frequency band."
Current Biology 30.13 (2020): 2621-2627.
```