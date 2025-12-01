import os
import gzip
import shutil


def prepare_csv_state(base_path: str) -> str:
    csv_path = base_path
    gz_path = base_path + ".gz"

    csv_exists = os.path.isfile(csv_path)
    gz_exists = os.path.isfile(gz_path)

    if csv_exists:
        return csv_path

    if gz_exists:
        with gzip.open(gz_path, "rb") as f_in, open(csv_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        return csv_path

    with open(csv_path, "w") as f:
        pass

    return csv_path


def compress_csv(csv_path: str):
    if not os.path.isfile(csv_path):
        return
    
    print(f"Compressing: {csv_path}")

    gz_path = csv_path + ".gz"

    with open(csv_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
        
    os.fsync(os.open(gz_path, os.O_RDONLY))
        
    os.remove(csv_path)


def compare_csv_and_gzip_text(csv_path: str, gz_path: str) -> bool:
    try:
        with open(csv_path, "r", encoding="utf-8", newline=None) as f:
            csv_text = f.read()

        with gzip.open(gz_path, "rt", encoding="utf-8", newline=None) as f:
            gz_text = f.read()

        if csv_text == gz_text:
            return True
        
        for i, (a, b) in enumerate(zip(csv_text, gz_text)):
            if a != b:
                print(f"First difference at index {i!r}: CSV={a!r}, GZ={b!r}")
                break

        if len(csv_text) != len(gz_text):
            print(f"Length mismatch: CSV={len(csv_text)}, GZ={len(gz_text)}")

        print("Finished comparison")
        return False
    except Exception as e:
        print("exception occurred:", type(e).__name__, e)
        return False