# Labeling Guide for Traffic Event Detection

## Overview
This guide defines how to label posts for training DistilBERT (event detection) and RoBERTa (reliability scoring) models.

## Annotation Rubric: Strict Binary Classification

Your task is to perform a **strict binary classification** on unstructured text data sourced from Social Media (Commuters/Institutions), News API, and GDELT. You must determine the text's reliability as a **valid, actionable traffic event signal** for Metro Manila.

### Scoring Scale (Strict Binary)
- **1 = Reliable**: The text contains trustworthy, factual, and actionable information regarding a traffic-disrupting event (e.g., accidents, floods, road closures, heavy weather).
- **0 = Unreliable**: The text exhibits misinformation, extreme subjectivity, irrelevance, lack of specific geographic details, or acts as "noise."

---

## Annotation Rules by Source & Content Type

### Rule 1: Institutional & Established News Sources (News API / Verified Accounts)

**Guideline:**
Texts originating from verified institutional social media accounts (e.g., MMDA, PNP, PAGASA) or established Philippine news organizations via the News API are **provisionally classified as Reliable (1)**, provided they report a specific traffic-relevant event.

**Example:**
- **[News API - Inquirer]** "BREAKING: Multiple vehicle collision on Commonwealth Ave. causes heavy buildup tailing back to Philcoa." → **Score: 1**
- **[MMDA Official]** "MMDA ALERT: Stalled truck due to mechanical problem at C5 WB Bonny Serrano tunnel as of 11:16 PM. One lane occupied." → **Score: 1**

---

### Rule 2: GDELT Automated Event Records (Evaluate for Accuracy & Relevance)

**Guideline:**
GDELT data is generated via automated global text scraping and can contain redundancies or inaccuracies. **Do not automatically assume GDELT data is reliable.** Evaluate it to ensure the event is genuinely occurring in Metro Manila and directly impacts traffic. Score as Unreliable (0) if the event is miscategorized, metaphorical, or lacks specific local context.

**Example A (Reliable):**
- **[GDELT]** "Transport strike paralyzes jeepney routes in Quezon City and Manila; commuters stranded." → **Score: 1** (Clear traffic disruption event with specific locations)

**Example B (Unreliable):**
- **[GDELT]** "Web traffic jams server during online concert ticket sales in Manila." → **Score: 0** (Metaphorical use of "traffic", irrelevant to physical roads)

---

### Rule 3: Normal Users / Commuters (Social Media - Evaluate for Specificity)

**Guideline:**
A normal user's post is **Reliable (1) ONLY IF** it acts as an objective, factual report containing **specific details** (Location, Incident Type). It is **Unreliable (0)** if it is purely a subjective complaint, an emotional reaction, or lacks geographic context.

**Example A (Reliable):**
- "Avoid C5 Libis northbound right now, there is a stalled truck blocking the middle lane." → **Score: 1** (Provides location, cause, and impact)

**Example B (Unreliable):**
- "Traffic in Metro Manila is the absolute worst, I've been stuck for hours!" → **Score: 0** (Subjective complaint, no specific location or identifiable event)

---

### Rule 4: Handling Taglish / Informal Language

**Guideline:**
The presence of informal language, slang, or Taglish **does NOT automatically make a post unreliable.** Evaluate the semantic meaning of the translated/cleaned text. If a Taglish post contains **specific, factual event data**, score it as Reliable (1).

**Example:**
- **[Taglish/Informal]** "Baha sa Espanya hanggang tuhod, di makadaan mga kotse." (Flooding on Espanya up to knee-level, cars can't pass) → **Score: 1** (Specific location + impact despite informal language)

---

## Label Definitions (Mapped to Training Schema)

### 1. Event Label (Binary: 0 or 1)
**Used for:** DistilBERT training (Is this a real traffic/event signal?)

#### Label = 1: Traffic Event
Mark as **1** if the post describes or references:
- **Road incidents**: crashes, accidents, collisions, hit-and-run
- **Stalled vehicles**: mechanical problems, breakdowns, flat tires (with road/location mentioned)
- **Road closures**: lane closures, temporary blockages, construction impacts
- **Traffic conditions**: heavy congestion, gridlock (with specific location)
- **MMDA alerts**: official traffic advisories, enforcement actions
- **Environmental events affecting traffic**: flooding, landslide, fire (if traffic-related)
- **Public transport disruptions**: bus/jeepney breakdowns affecting traffic flow

#### Label = 0: Non-Event
Mark as **0** if the post is:
- Opinion/commentary about traffic without specific incident
- Promotion or advertisement
- General MMDA admin (hiring, rules, history)
- Unrelated news mentioning MMDA
- Questions/replies without incident information
- Duplicate or retweet of another post
- Personal complaint without actionable signal

#### Examples

✅ Event = 1:
- "MMDA ALERT: Stalled truck due to mechanical problem at C5 WB Bonny Serrano tunnel as of 11:16 PM. One lane occupied."
- "Road crash incident at Julia Vargas EB involving motorcycle and SUV as of 8:35 PM. MMDA enforcers on site."

❌ Event = 0:
- "MMDA is accepting applications for a WRITER."
- "Heavy traffic is the worst thing ever #mmda"
- "@MMDA what's causing the traffic?"

---

### 2. Reliability Label (3-class: 0, 1, or 2)
**Used for:** RoBERTa training (How reliable/actionable is this signal?)

#### Label = 2: High Reliability
Mark as **2** if:
- Post is from official MMDA account or verified source
- Specific location + time stamp + incident type clearly stated
- Actionable information (what to avoid, what route to take)
- Multiple corroborating posts or reports of same incident
- Incident confirmed by the text itself (not hearsay)

#### Label = 1: Medium Reliability (Plausible but Unconfirmed)
Mark as **1** if:
- Location is vague or implied
- Time is not mentioned or unclear
- Information is second-hand ("heard that...", "people say...")
- Incident type is implied but not explicit
- No follow-up confirmation visible
- Single report without corroboration

#### Label = 0: Low/No Reliability (Discard)
Mark as **0** if:
- Not a traffic incident at all
- Completely unrelated to traffic/MMDA
- Spam, joke, or irrelevant mention
- You have zero confidence the signal is useful
- Post quality is too poor to extract meaning

#### Examples

✅ Reliability = 2:
- "MMDA ALERT: Stalled truck due to mechanical problem at C5 Katipunan Ave. before B. Serrano SB as of 6:35 PM. One lane occupied. MMDA enforcers are on site managing traffic." (Official MMDA, specific location/time/action)

⚠️ Reliability = 1:
- "May stalled vehicle po sa flyover Northbound. #mmda" (Location clear but no time; from user, not official)
- "Fire at Navotas Sanitary Landfill, around 80% contained" (Location clear, but traffic impact implied not stated)

❌ Reliability = 0:
- "MMDA Chief appointed as DRRMC head" (Admin news, not traffic incident)
- "@MMDA Thank you for your service" (Appreciation, not actionable)

---

## Labeling Workflow

### For Initial Training Set
1. Open the label stub CSV.
2. Go through each post **in chronological order** (by `created_at`).
3. Read `raw_text` + `translated_text` side by side.
4. Assign `event_label` first (is this an event at all?).
5. If `event_label=1`, then assign `reliability_label` (how strong?).
6. If `event_label=0`, set `reliability_label=0` (no need to assess reliability).
7. Add `annotator_name`, `annotation_time`, and optional `notes`.
8. Save and re-load in the notebook.

### For Ongoing Batches (Every Hour)
1. Export new batch with stub (event_label=NA, reliability_label=NA).
2. Label only uncertain or high-impact posts (use model predictions as pre-filter).
3. Mark clearly correct predictions with a confidence flag, skip detailed review.
4. Append corrected labels to historical labeled data.
5. Re-train periodically (e.g., weekly) with accumulated labels.

---

## Handling Edge Cases

### Duplicate Posts
- If a post is an exact or near-duplicate of an earlier post, label the first one and mark the duplicate as `event_label=0, reliability_label=0, notes="duplicate of post_id:XYZ"`.

### Multi-Event Posts
- If a single post mentions 2+ incidents, treat it as 1 entry with the **primary** incident (first or most prominent).
- Example: "Stalled truck at C5 SB. Separate crash at Ortigas." → Label the stalled truck (listed first), note the crash in `notes` for context.

### Time-Sensitive Updates
- If a post is a status update on an ongoing incident (e.g., "Update: now 80% contained"), label based on the current status at annotation time.
- Note earlier reports in `notes`.

### Ambiguous Location
- If location is vague ("North" instead of "C5 Northbound"), use `reliability_label=1` (plausible but incomplete).

---

## Annotation Template

| Column | Type | Required | Example |
|--------|------|----------|---------|
| `post_id` | string | ✅ | 2052060431494345200 |
| `created_at` | datetime | ✅ | 2026-05-06T16:18:26.000Z |
| `raw_text` | string | ✅ | MMDA ALERT: Stalled dump truck... |
| `translated_text` | string | ✅ | [English version] |
| `event_label` | int (0, 1, NA) | ✅ | 1 |
| `reliability_label` | int (0, 1, 2, NA) | ✅ | 2 |
| `annotator_name` | string | ✅ | Alice |
| `annotation_time` | datetime | ✅ | 2026-05-11T10:30:00Z |
| `notes` | string | ❌ | Confirmed by MMDA official |

---

## Quality Checks

After labeling a batch, verify:
1. **No missing required fields** (except `notes`).
2. **event_label = 0 → reliability_label = 0** (consistency).
3. **Chronological order** preserved (sort by `created_at` if needed).
4. **No duplicate post_ids** (check for accidental re-labeling).
5. **Label distribution**:
   - For DistilBERT: aim for ~50/50 split between event/non-event.
   - For RoBERTa: track imbalance and note in training logs (weights will be auto-adjusted).

---

## Tips for Consistent Labeling

1. **Read both raw and translated text** before deciding. Translation artifacts may affect meaning.
2. **Look for location markers**: street names, landmarks, highway codes (C5, EDSA, etc.).
3. **Check timestamps**: if post is old relative to annotation time, verify still relevant.
4. **Use common sense**: would a commuter find this info useful *right now*?
5. **When unsure, mark `reliability_label=1`** instead of guessing 0 or 2.
6. **Take notes** on ambiguous cases for future review.

---

## File Naming Convention

Save labeled files with timestamp and batch identifier:
```
x_labeled_batch_YYYYMMDD_HHMM_[ANNOTATOR].csv
```

Example:
- `x_labeled_batch_20260511_1000_alice.csv`
- `x_labeled_batch_20260511_1430_bob.csv`

Then merge all batches into a master:
- `x_labeled_master.csv` (cumulative training set)

