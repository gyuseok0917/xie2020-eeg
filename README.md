# xie2020-eeg
This repository was created to reproduce experiments in</br>
[Visual Imagery and Perception Share Neural Representations in the Alpha Frequency Band](https://www.sciencedirect.com/science/article/pii/S096098222030590X)

## Environment Setting
1. Create virtual environment
```
conda create neuro python=3.10
conda activate neuro
```
2. Install libraries
```
pip install -r requirements.txt
```

## Data Download
Data is provided at [https://osf.io/ykp9w/](https://osf.io/ykp9w/overview).
To download, run the command below.
```
chmod +x data_download.sh
./data_download.sh
```

## Data Preprocessing
Run the script below for preprocessing. `preprocess_data.py` applies Morlet wavelet time-frequency analysis</br>
and baseline dB normalization to raw EEG data, then crops and downsamples the result before saving it as a `.npy` file.
```
python preprocess_data.py
```

## Reference
```
Xie, Siying, Daniel Kaiser, and Radoslaw M. Cichy.
"Visual imagery and perception share neural representations in the alpha frequency band."
Current Biology 30.13 (2020): 2621-2627.
```
