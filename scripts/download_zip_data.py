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


url = r'https://drive.google.com/file/d/1s8_UUgCuluLiWl45Ndl7UU0mIy1r-J5j/view?usp=sharing'
output = str(DATA_DIR / 'Stock_data/dl_folder')
download_data_from_drive(url, output)
