# Real-Time Labeling Workflow for Traffic Event Detection

## Overview
This document describes how to label incoming traffic posts every 15 minutes or hourly while building your training set for DistilBERT and RoBERTa.

---

## Workflow Phases

### Phase 1: Initial Seed Labeling (First 2-3 days)
**Goal:** Label 50-100 posts to start training.

#### Steps
1. **Export label stub** from your raw CSV:
   ```bash
   python ml/scripts/label_batch.py stub \
     --input ml/outputs/x_fetch/x_recent_posts_translated.csv \
     --output ml/data/x_label_stub.csv
   ```

2. **Open Labeling Notebook** [ml/notebooks/interactive_labeling.ipynb](ml/notebooks/interactive_labeling.ipynb):
   - Load Cell 1 to load raw data.
   - Run Cell 2 to initialize the labeling session.
   - Run Cell 3 to start interactive labeling (about 15-30 min for 50 posts).
   - Run Cell 4 to save your first batch.

3. **Review your work** using Cell 4 or:
   ```bash
   python ml/scripts/label_batch.py validate --file ml/data/x_labeled_batch_20260511_1430_yourname.csv
   ```

4. **Once you have 20+ labeled posts**: proceed to training in [fuse_traffic_training.ipynb](fuse_traffic_training.ipynb).

---

### Phase 2: Ongoing Labeling (After Initial Training)
**Goal:** Label new hourly batches + uncertain predictions to continuously improve models.

#### 2a. Daily Batch Labeling (Manual)

**Every hour or every 4 hours**, do this:

1. **Export new batch from your ingestion pipeline**:
   ```python
   # In your backend or notebook
   new_df = fetch_latest_posts(lookback_hours=1)  # Last hour
   new_df.to_csv('ml/data/x_batch_20260511_1400.csv', index=False)
   ```

2. **Create label stub for the batch**:
   ```bash
   python ml/scripts/label_batch.py stub \
     --input ml/data/x_batch_20260511_1400.csv \
     --output ml/data/x_batch_20260511_1400_stub.csv
   ```

3. **Label interactively** (5-15 min for 10-20 posts):
   - Open [interactive_labeling.ipynb](ml/notebooks/interactive_labeling.ipynb).
   - Modify Cell 1 to load `x_batch_20260511_1400_stub.csv`.
   - Run Cells 2-3 to annotate.

4. **Merge into master training set**:
   ```bash
   python ml/scripts/label_batch.py merge \
     --batches ml/data/x_batch_20260511_1400_labeled.csv \
     --master ml/data/x_labeled_master.csv
   ```

#### 2b. Selective Review (Using Model Predictions)

Once you have trained models:

1. **Run inference on new batch**:
   ```python
   from transformers import pipeline
   
   # Load trained models
   distil_pipe = pipeline('text-classification', 
                          model='/content/distilbert_event',
                          device=0)
   roberta_pipe = pipeline('text-classification',
                           model='/content/roberta_reliability',
                           device=0)
   
   # Score new posts
   new_posts = pd.read_csv('ml/data/x_batch_20260511_1400.csv')
   distil_scores = [max(d['score'] for d in distil_pipe(text)) 
                    for text in new_posts['translated_text']]
   roberta_scores = [max(r['score'] for r in roberta_pipe(text))
                     for text in new_posts['translated_text']]
   ```

2. **Flag uncertain cases** (where confidence < 0.7):
   ```python
   uncertain = new_posts[
       ((distil_scores < 0.7) & (distil_scores > 0.3)) |
       ((roberta_scores < 0.7) & (roberta_scores > 0.3))
   ]
   ```

3. **Label only the uncertain and high-impact cases**:
   - Review only `uncertain` subset manually.
   - Mark clearly correct model predictions with quick confirmation (y/n).
   - This reduces annotation time by ~70%.

---

### Phase 3: Continuous Retraining (Weekly or Bi-weekly)
**Goal:** Incorporate accumulated labels and improve model performance.

#### Schedule
- **Monday morning**: Merge all labels from past week.
- **Run retraining** on accumulated master dataset.
- **Validate** on held-out test set.
- **Deploy** if performance improves.

#### Steps
1. **Merge all weekly batches**:
   ```bash
   python ml/scripts/label_batch.py merge \
     --batches ml/data/x_batch_*_labeled.csv \
     --master ml/data/x_labeled_master.csv
   ```

2. **Check data quality**:
   ```bash
   python ml/scripts/label_batch.py validate --file ml/data/x_labeled_master.csv
   ```

3. **Sample for review**:
   ```bash
   python ml/scripts/label_batch.py sample \
     --file ml/data/x_labeled_master.csv \
     --size 20
   ```

4. **Retrain models** using [fuse_traffic_training.ipynb](ml/notebooks/fuse_traffic_training.ipynb):
   - Load `x_labeled_master.csv`.
   - Run training cells.
   - Evaluate on test set.
   - Save to `/content/distilbert_event_v2`, etc.

5. **A/B test** new models on production data before switching.

---

## File Organization

```
ml/
├── data/
│   ├── x_labeled_master.csv              # Cumulative training set
│   ├── x_batch_20260511_1400.csv         # Raw hourly batch
│   ├── x_batch_20260511_1400_stub.csv    # Blank template
│   └── x_batch_20260511_1400_labeled.csv # Annotated batch
├── notebooks/
│   ├── fuse_traffic_training.ipynb       # Model training
│   └── interactive_labeling.ipynb        # Annotation tool
├── scripts/
│   └── label_batch.py                    # CLI utility
└── LABELING_GUIDE.md                      # Label definitions
```

---

## Time Estimates

| Task | Time | Frequency |
|------|------|-----------|
| Annotate 1 post | 1-2 min | Hourly batch (10-20 posts) |
| Label hourly batch | 15-30 min | Every 4 hours |
| Validate batch | 2-3 min | Per batch |
| Merge batches | <1 min | Daily |
| Retrain models | 15-30 min | Weekly |

**Total annotation burden**: ~1-2 hours per week after initial setup.

---

## Quality Checkpoints

### Before Merging into Master
```bash
python ml/scripts/label_batch.py validate --file ml/data/x_batch_<batch_id>_labeled.csv
```
Check for:
- No missing required fields.
- No invalid label values (event_label ∈ {0,1}, reliability_label ∈ {0,1,2}).
- Consistency: event_label=0 → reliability_label=0.

### Before Retraining
```bash
python ml/scripts/label_batch.py sample --file ml/data/x_labeled_master.csv --size 30
```
Review random samples for:
- Label accuracy.
- Consistency across annotators.
- Class imbalance (ideal: 40-60% split for binary, balanced multi-class).

---

## Handling Edge Cases

### When New Data Arrives Faster Than You Can Label
- **Solution 1**: Use model predictions to prioritize uncertain or high-impact posts for manual review.
- **Solution 2**: Increase batch size and label once per shift instead of per hour.
- **Solution 3**: Recruit 2nd annotator for parallel labeling (use `annotator_name` field).

### When You Disagree with Your Own Earlier Label
- Edit the label in `x_labeled_master.csv`.
- Rerun validation and retrain.
- Log disagreement in `notes` field for pattern analysis.

### When a Post Requires Real-World Verification
- Example: "Stalled truck at C5 SB" — did it actually happen?
- Use your domain knowledge + context.
- If truly unsure, mark as `reliability_label=1` (medium) instead of guessing.

---

## Next Steps

1. **This week**: Complete Phase 1 (label 50-100 initial posts).
2. **Next week**: Start Phase 2 (hourly batch labeling).
3. **After 1 month**: Transition to Phase 3 (selective review + weekly retraining).

---

## References
- [Labeling Guide](LABELING_GUIDE.md)
- [Training Notebook](ml/notebooks/fuse_traffic_training.ipynb)
- [Annotation Tool](ml/notebooks/interactive_labeling.ipynb)
- [Batch CLI](ml/scripts/label_batch.py)
