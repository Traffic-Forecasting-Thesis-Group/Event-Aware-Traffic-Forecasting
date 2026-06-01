import sys
from datetime import datetime
from pathlib import Path


def main():
    try:
        import pandas as pd
    except Exception:
        print('pandas is required. Activate the project .venv or install pandas.')
        sys.exit(2)

    root = Path('ml/data')
    files = {
        'master': root / 'x_labeled_master.csv',
        'batch': root / 'x_labeled_batch_20260511_1852_auto_bootstrap.csv',
        'major': root / 'major_event_training_check.csv',
        'flood': root / 'major_event_flood_check.csv',
    }

    official_handles = {'MMDA', 'DPWHph', 'DOTrPH', 'PNP_HPG', 'QCGov', 'Navotas_City', 'officialmunti', 'sanjuancityncr', 'PasayPIO', 'PIOCaloocan', 'valenzuelacity'}
    positive_event_types = {'traffic / road incident', 'weather / flood alert'}
    event_keywords = {'crash', 'collision', 'stalled', 'road closure', 'traffic advisory', 'flood', 'heavy rain', 'habagat', 'roadwork', 'blocked', 'baha', 'reroute', 'lane closure'}

    def label_row(row):
        source_type = str(row.get('source_type', '') or '').lower()
        major_type = str(row.get('major_event_type', '') or '').strip().lower()
        source_name = str(row.get('source_name', '') or row.get('source_handle', '') or '').strip()
        text = str(row.get('raw_text', '') or '').lower()

        is_event = major_type in positive_event_types
        if not is_event and source_type == 'x_timeline':
            is_event = any(term in text for term in event_keywords)

        if not is_event:
            return 0, 0, 'auto: non-traffic or non-weather major event'

        if source_type == 'gdelt':
            return 1, 1, 'auto: gdelt traffic/weather signal'

        if source_name in official_handles:
            return 1, 2, 'auto: official traffic/weather advisory'

        return 1, 1, 'auto: traffic/weather signal'

    def build_labeled_batch(path):
        if not path.exists():
            return None
        df = pd.read_csv(path)
        if df.empty:
            return None

        labeled = df.copy()
        labels = labeled.apply(label_row, axis=1, result_type='expand')
        labeled['event_label'] = labels[0]
        labeled['reliability_label'] = labels[1]
        labeled['annotator_name'] = 'rule_based_major_event_labeler'
        labeled['annotation_time'] = datetime.now().isoformat(timespec='seconds')
        labeled['notes'] = labels[2]

        if 'lang' not in labeled.columns:
            labeled['lang'] = 'en'
        if 'translated_text' not in labeled.columns:
            labeled['translated_text'] = ''
        if 'source_file' not in labeled.columns:
            labeled['source_file'] = path.name

        keep_cols = [
            'post_id', 'created_at', 'lang', 'raw_text', 'translated_text',
            'source_type', 'source_file', 'event_label', 'reliability_label',
            'annotator_name', 'annotation_time', 'notes'
        ]
        for col in keep_cols:
            if col not in labeled.columns:
                labeled[col] = pd.NA

        return labeled[keep_cols]

    dfs = []

    if files['master'].exists():
        dfm = pd.read_csv(files['master'])
        if 'event_label' not in dfm.columns:
            dfm['event_label'] = pd.NA
        dfs.append(dfm)
        print(f'Loaded master: {len(dfm)} rows')
    else:
        print('Master labeled file not found:', files['master'])

    if files['batch'].exists():
        dfb = pd.read_csv(files['batch'])
        if 'reliability_label' in dfb.columns:
            dfb = dfb[dfb['reliability_label'].notna()].copy()
            if 'event_label' not in dfb.columns:
                dfb['event_label'] = pd.NA
            dfs.append(dfb)
            print(f'Loaded batch (with labels): {len(dfb)} rows')
        else:
            print('Batch file exists but has no reliability_label, skipping labeled rows')

    for key in ('major', 'flood'):
        p = files[key]
        labeled = build_labeled_batch(p)
        if labeled is not None:
            dfs.append(labeled)
            print(f'Labeled {key}: {len(labeled)} rows')

    if not dfs:
        print('No dataframes to merge. Exiting.')
        sys.exit(1)

    merged = pd.concat(dfs, ignore_index=True, sort=False)
    merged = merged.drop_duplicates(subset=['post_id'], keep='first')
    merged = merged.sort_values('created_at', na_position='last')

    master_cols = ['post_id', 'created_at', 'lang', 'raw_text', 'translated_text', 'source_type', 'source_file', 'event_label', 'reliability_label', 'annotator_name', 'annotation_time', 'notes']
    for c in master_cols:
        if c not in merged.columns:
            merged[c] = pd.NA

    out = root / 'merged_training_for_model.csv'
    merged[master_cols].to_csv(out, index=False)
    print(f'Merged {len(merged)} rows -> {out}')
    print('Event label counts:')
    print(merged['event_label'].value_counts(dropna=False).to_string())
    print('Reliability label counts:')
    print(merged['reliability_label'].value_counts(dropna=False).to_string())


if __name__ == '__main__':
    main()
