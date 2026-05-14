import os
import sys
import requests
import zipfile
import shutil
from urllib.parse import urlparse, unquote

LINK_FILE = 'link.txt'
DOWNLOAD_DIR = 'downloads'
CHUNK_SIZE = 99 * 1024 * 1024       # ۹۹ مگابایت
FILE_SIZE_THRESHOLD = 100 * 1024 * 1024  # ۱۰۰ مگابایت، اگر بیشتر بود تقسیم کن

def sanitize_filename(filename):
    return os.path.basename(filename)

def download_file(url, dest_path):
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

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
            part_num += 1
    return part_num - 1

def main():
    if not os.path.exists(LINK_FILE):
        print(f'{LINK_FILE} not found.')
        sys.exit(1)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    with open(LINK_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        print(f'Processing: {url}')
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = sanitize_filename(path) if path else 'downloaded_file'
        if not filename:
            filename = 'downloaded_file'

        tmp_file = os.path.join('/tmp', filename)
        try:
            download_file(url, tmp_file)
            file_size = os.path.getsize(tmp_file)

            if file_size <= FILE_SIZE_THRESHOLD:
                # زیر ۱۰۰ مگ: مستقیم کپی کن
                dest = os.path.join(DOWNLOAD_DIR, filename)
                shutil.move(tmp_file, dest)
                print(f'Stored directly: {dest}')

            else:
                # بالای ۱۰۰ مگ: فشرده‌سازی و تقسیم
                zip_path = os.path.join('/tmp', filename + '.zip')
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(tmp_file, arcname=filename)

                zip_size = os.path.getsize(zip_path)
                if zip_size > FILE_SIZE_THRESHOLD:
                    print(f'Zip size {zip_size} > threshold, splitting...')
                    prefix = os.path.join(DOWNLOAD_DIR, filename + '.zip')
                    num_parts = split_file(zip_path, CHUNK_SIZE, prefix)
                    print(f'Split into {num_parts} parts in {DOWNLOAD_DIR}/')
                    os.remove(zip_path)   # فایل zip اصلی حذف میشه
                else:
                    dest = os.path.join(DOWNLOAD_DIR, filename + '.zip')
                    shutil.move(zip_path, dest)
                    print(f'Compressed and stored: {dest}')

        except Exception as e:
            print(f'Error downloading {url}: {e}')
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    print('All done.')

if __name__ == '__main__':
    main()