#!/usr/bin/env python3
"""
Batch labeling and merging utility for continuous data streams.

Usage:
  python label_batch.py --input x_recent_posts_translated.csv --output x_label_stub.csv
  python label_batch.py --merge x_labeled_batch_*.csv --master x_labeled_master.csv
"""

import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

def create_label_stub(input_csv: str, output_csv: str) -> None:
    """Create a blank label stub from raw CSV."""
    df = pd.read_csv(input_csv)
    
    # Map columns
    if 'x_post_id' in df.columns:
        df = df.rename(columns={'x_post_id': 'post_id'})
    
    # Select relevant columns
    selected_cols = [
        c for c in ['post_id', 'created_at', 'raw_text', 'translated_text', 'lang']
        if c in df.columns
    ]
    
    label_stub = df[selected_cols].copy()
    label_stub['event_label'] = pd.NA
    label_stub['reliability_label'] = pd.NA
    label_stub['annotator_name'] = ''
    label_stub['annotation_time'] = pd.NA
    label_stub['notes'] = ''
    
    label_stub.to_csv(output_csv, index=False)
    print(f"✓ Created label stub: {output_csv}")
    print(f"  Posts to label: {len(label_stub)}")


def merge_labeled_batches(batch_files: list, master_csv: str, dedup=True) -> None:
    """Merge multiple labeled batch CSVs into a master file."""
    dfs = []
    
    for batch_file in batch_files:
        if Path(batch_file).exists():
            df = pd.read_csv(batch_file)
            # Only include rows that are labeled (event_label is not NA)
            df_labeled = df[df['event_label'].notna()]
            dfs.append(df_labeled)
            print(f"  Loaded {len(df_labeled)} labeled rows from {batch_file}")
    
    if not dfs:
        print("No labeled rows found in batch files.")
        return
    
    merged = pd.concat(dfs, ignore_index=True)
    
    if dedup:
        # Remove duplicates by post_id, keep most recent
        merged = merged.sort_values('annotation_time', ascending=False)
        merged = merged.drop_duplicates(subset=['post_id'], keep='first')
        merged = merged.sort_values('created_at')
    
    # Load existing master if present
    if Path(master_csv).exists():
        master = pd.read_csv(master_csv)
        # Remove rows that are being re-labeled
        master = master[~master['post_id'].isin(merged['post_id'])]
        merged = pd.concat([master, merged], ignore_index=True)
        merged = merged.sort_values('created_at')
        print(f"\n✓ Updated master: {master_csv} ({len(merged)} total rows)")
    else:
        print(f"\n✓ Created new master: {master_csv} ({len(merged)} rows)")
    
    merged.to_csv(master_csv, index=False)
    
    # Summary stats
    events = (merged['event_label'] == 1).sum()
    non_events = (merged['event_label'] == 0).sum()
    print(f"\nClass distribution:")
    print(f"  Events (label=1): {events}")
    print(f"  Non-events (label=0): {non_events}")
    
    if events > 0:
        event_rows = merged[merged['event_label'] == 1]
        high_rel = (event_rows['reliability_label'] == 2).sum()
        med_rel = (event_rows['reliability_label'] == 1).sum()
        low_rel = (event_rows['reliability_label'] == 0).sum()
        print(f"\nReliability distribution (events only):")
        print(f"  High (2): {high_rel}")
        print(f"  Medium (1): {med_rel}")
        print(f"  Low (0): {low_rel}")


def validate_labels(csv_file: str) -> None:
    """Check label quality and consistency."""
    df = pd.read_csv(csv_file)
    
    print(f"Validating {csv_file}...")
    errors = []
    
    # Check for non-labeled rows
    unlabeled = df[df['event_label'].isna()].shape[0]
    if unlabeled > 0:
        print(f"  ⚠ {unlabeled} unlabeled rows")
    
    # Check event_label consistency
    invalid_event = df[~df['event_label'].isin([0, 1, float('nan')])].shape[0]
    if invalid_event > 0:
        errors.append(f"Invalid event_label in {invalid_event} rows")
    
    # Check reliability_label consistency
    invalid_rel = df[~df['reliability_label'].isin([0, 1, 2, float('nan')])].shape[0]
    if invalid_rel > 0:
        errors.append(f"Invalid reliability_label in {invalid_rel} rows")
    
    # Check: if event_label=0, reliability_label should be 0
    inconsistent = df[(df['event_label'] == 0) & (df['reliability_label'] != 0)].shape[0]
    if inconsistent > 0:
        errors.append(f"{inconsistent} rows with event_label=0 but reliability_label≠0")
    
    # Check duplicate post_ids
    dupes = df['post_id'].duplicated().sum()
    if dupes > 0:
        errors.append(f"{dupes} duplicate post_ids")
    
    if errors:
        print("✗ Validation errors:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("✓ All validations passed")


def sample_for_review(master_csv: str, sample_size=10, label=None) -> None:
    """Show random sample of labeled data for quality review."""
    df = pd.read_csv(master_csv)
    
    if label is not None:
        df = df[df['event_label'] == label]
    
    if len(df) == 0:
        print("No data to sample.")
        return
    
    sample = df.sample(min(sample_size, len(df)))
    
    for _, row in sample.iterrows():
        print(f"\n--- POST: {row['post_id']} ---")
        print(f"Created: {row['created_at']}")
        print(f"Event: {row['event_label']}, Reliability: {row['reliability_label']}")
        print(f"Annotator: {row['annotator_name']}")
        print(f"Raw: {str(row['raw_text'])[:150]}...")
        if row['notes']:
            print(f"Notes: {row['notes']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Labeling utility for traffic posts.')
    
    subparsers = parser.add_subparsers(dest='command')
    
    # Create stub
    stub_parser = subparsers.add_parser('stub', help='Create a label stub from raw CSV')
    stub_parser.add_argument('--input', required=True, help='Input CSV file')
    stub_parser.add_argument('--output', required=True, help='Output stub CSV file')
    
    # Merge batches
    merge_parser = subparsers.add_parser('merge', help='Merge labeled batches into master')
    merge_parser.add_argument('--batches', nargs='+', required=True, help='Batch CSV files to merge')
    merge_parser.add_argument('--master', required=True, help='Master CSV file (output)')
    
    # Validate
    val_parser = subparsers.add_parser('validate', help='Validate label consistency')
    val_parser.add_argument('--file', required=True, help='CSV file to validate')
    
    # Sample
    sample_parser = subparsers.add_parser('sample', help='Sample for QA review')
    sample_parser.add_argument('--file', required=True, help='Master CSV file')
    sample_parser.add_argument('--size', type=int, default=10, help='Sample size')
    sample_parser.add_argument('--label', type=int, help='Filter by event_label (0 or 1)')
    
    args = parser.parse_args()
    
    if args.command == 'stub':
        create_label_stub(args.input, args.output)
    elif args.command == 'merge':
        merge_labeled_batches(args.batches, args.master)
    elif args.command == 'validate':
        validate_labels(args.file)
    elif args.command == 'sample':
        sample_for_review(args.file, args.size, args.label)
    else:
        parser.print_help()
