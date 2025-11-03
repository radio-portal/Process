import pandas as pd
import sys
import os

def merge_no_energy_first(df):
    merged_data = []
    i = 0
    while i < len(df):
        current_row = df.iloc[i].copy()
        if current_row['labels'] == 'noEnergy' or current_row['labels'] == 'noise':
            if i < len(df) - 1:
                next_row = df.iloc[i + 1].copy()
                next_row['start'] = current_row['start']
                merged_data.append(next_row)
                i += 2
            else:
                merged_data.append(current_row)
                i += 1
        else:
            merged_data.append(current_row)
            i += 1
    return pd.DataFrame(merged_data)

def merge_rows(df):
    merged_data = []
    current_row = df.iloc[0].copy()
    for i in range(1, len(df)):
        next_row = df.iloc[i]
        if current_row['stop'] - current_row['start'] <= 0:
            if current_row['labels'] != next_row['labels']:
                continue
            current_row['stop'] = max(current_row['stop'], next_row['stop'])
            current_row['labels'] = next_row['labels']
        else:
            merged_data.append(current_row.copy())
            current_row = next_row.copy()
    merged_data.append(current_row)
    return pd.DataFrame(merged_data)

def process_file(input_file, output_file):
    df = pd.read_csv(input_file, sep='\t')
    df = merge_no_energy_first(df)
    merged_df = merge_rows(df)
    merged_df.to_csv(output_file, sep=',', index=False)

def process_directory(output_dir):
    stations = ["kbs", "mbc", "sbs"]
    for root, dirs, files in os.walk(output_dir):
        for dir_name in dirs:
            if any(dir_name.startswith(station) for station in stations):
                date = os.path.basename(root)
                time = dir_name.split('-')[1]
                input_dir = os.path.join(root, dir_name, "segments")
                input_file = os.path.join(input_dir, f"{date}{time}.csv")
                output_file = os.path.join(input_dir, f"{date}{time}-noenergy.csv")
                if os.path.exists(input_file):
                    print(f"Processing {input_file}...")
                    process_file(input_file, output_file)
                    print(f"Saved processed file to {output_file}")
                else:
                    print(f"Input file {input_file} does not exist, skipping.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <output_directory>")
        sys.exit(1)
    output_directory = sys.argv[1]
    if not os.path.exists(output_directory):
        print(f"Error: Output directory {output_directory} does not exist.")
        sys.exit(1)
    process_directory(output_directory)
