import pandas as pd
import sys
import os
import argparse

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Remove noEnergy/noise and merge segments for a specific file.')
    parser.add_argument('--date', type=str, required=True, help='Date in YYMMDD format, e.g. 240615')
    parser.add_argument('--station', type=str, required=True, help='Station name, e.g. kbs')
    parser.add_argument('--time', type=str, required=True, help='Time string, e.g. 0900')
    args = parser.parse_args()

    # base_dir = os.path.join(os.getcwd(), "processed", args.date, f"{args.station}-{args.time}", "segments")
    base_dir = os.path.join(os.getcwd(), "processed", f"{args.date}-music", f"{args.station}-{args.time}", "segments")
    input_file = os.path.join(base_dir, f"{args.date}{args.time}.csv")
    output_file = os.path.join(base_dir, f"{args.date}{args.time}-noenergy.csv")

    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist.")
        sys.exit(1)

    print(f"Processing {input_file}...")
    process_file(input_file, output_file)
    print(f"Saved processed file to {output_file}")
