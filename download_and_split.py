import os
import sys
import requests
import zipfile
import shutil
import time
from urllib.parse import urlparse, unquote

LINK_FILE = 'link.txt'
DOWNLOAD_DIR = 'downloads'
CHUNK_SIZE = 99 * 1024 * 1024
FILE_SIZE_THRESHOLD = 100 * 1024 * 1024

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def sanitize_filename(filename):
    return os.path.basename(filename)

def download_file(url, dest_path, retries=2):
    for attempt in range(retries+1):
        try:
            print(f'Downloading (attempt {attempt+1}): {url}')
            resp = requests.get(url, stream=True, headers=HEADERS, timeout=(10, 60))
            resp.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f'Downloaded to {dest_path}, size: {os.path.getsize(dest_path)} bytes')
            return True
        except Exception as e:
            print(f'Error on attempt {attempt+1}: {e}')
            if attempt < retries:
                time.sleep(5)
    return False

def split_file(filepath, chunk_size, output_prefix):
    part_num = 1
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            part_name = f"{output_prefix}.part{part_num:03d}"
            with open(part_name, 'wb') as part_file:
                part_file.write(chunk)
            print(f'Created part: {part_name}')
            part_num += 1
    return part_num - 1

def main():
    if not os.path.exists(LINK_FILE):
        print(f'ERROR: {LINK_FILE} not found in current directory!')
        sys.exit(1)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    with open(LINK_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print('WARNING: No URLs found in link.txt')
        sys.exit(0)

    for url in urls:
        print(f'\n--- Processing: {url}')
        # چک اولیه که URL قابل دسترس باشه
        try:
            head_resp = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
            print(f'HEAD status: {head_resp.status_code}')
        except Exception as e:
            print(f'HEAD request failed: {e}. Will still try GET.')

        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = sanitize_filename(path) if path else 'downloaded_file'
        if not filename or filename.endswith('/'):
            filename = 'downloaded_file'

        tmp_file = os.path.join('/tmp', filename)
        if download_file(url, tmp_file):
            try:
                file_size = os.path.getsize(tmp_file)
                print(f'File size: {file_size} bytes')

                if file_size <= FILE_SIZE_THRESHOLD:
                    dest = os.path.join(DOWNLOAD_DIR, filename)
                    shutil.move(tmp_file, dest)
                    print(f'Stored directly: {dest}')

                else:
                    zip_path = os.path.join('/tmp', filename + '.zip')
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(tmp_file, arcname=filename)
                    zip_size = os.path.getsize(zip_path)
                    if zip_size > FILE_SIZE_THRESHOLD:
                        print(f'Zip size {zip_size} > threshold, splitting...')
                        prefix = os.path.join(DOWNLOAD_DIR, filename + '.zip')
                        num_parts = split_file(zip_path, CHUNK_SIZE, prefix)
                        print(f'Split into {num_parts} parts')
                        os.remove(zip_path)
                    else:
                        dest = os.path.join(DOWNLOAD_DIR, filename + '.zip')
                        shutil.move(zip_path, dest)
                        print(f'Compressed and stored: {dest}')
            except Exception as e:
                print(f'Error during processing: {e}')
            finally:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
        else:
            print(f'Failed to download {url} after retries.')

    print('\nAll done.')

if __name__ == '__main__':
    main()
