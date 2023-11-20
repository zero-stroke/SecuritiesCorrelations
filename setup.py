import gdown
import zipfile
import os
from config import DATA_DIR


def download_data_from_drive(zip_url, output_path):
    try:
        # Download the zip file from Google Drive
        gdown.download(zip_url, output_path, quiet=False)

        # Extract the zip file
        with zipfile.ZipFile(output_path, 'r') as zip_ref:
            zip_ref.extractall(os.path.dirname(output_path))

        # Remove the zip file after extraction
        os.remove(output_path)

        print("Download and extraction completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    url = r'https://drive.google.com/uc?id=1jZSSNTLwt_0ChQmmBaZ2dVMsH7XDprJP'
    # url = r'https://drive.google.com/uc?id=1mzSDgkoVM_LLogmINCVcFv7YRPUYP3Zx'   # Example data
    output = str(DATA_DIR / 'Stock_data/yahoo_daily/parquets_data.zip')
    download_data_from_drive(url, output)
