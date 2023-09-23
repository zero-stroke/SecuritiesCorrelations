from config import DATA_DIR
import gdown

import zipfile
import os


def download_data_from_drive(zip_url, output_path):
    # Download the zip file from Google Drive
    gdown.download(zip_url, output_path, quiet=False)

    # Extract the zip file
    with zipfile.ZipFile(output_path, 'r') as zip_ref:
        zip_ref.extractall(os.path.dirname(output_path))
    os.remove(output_path)  # Remove the zip file after extraction

# Using the direct download link format provided by gdown's warning
url = r'https://drive.google.com/uc?id=1jZSSNTLwt_0ChQmmBaZ2dVMsH7XDprJP'
output = str(DATA_DIR / 'Stock_data/yahoo_daily/parquets_data.zip')
download_data_from_drive(url, output)
