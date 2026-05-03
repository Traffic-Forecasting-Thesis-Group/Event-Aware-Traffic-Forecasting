from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from event_aware_traffic.module3_fusion import fuse_structured_and_text_events

def demo() -> None:
    structured = pd.DataFrame(
        [
            {
                "SQLDATE": 20260501,
                "EventRootCode": "18",
                "ActionGeo_Lat": 14.5995,
                "ActionGeo_Long": 120.9842,
                "NumMentions": 24,
                "SOURCEURL": "https://www.gmanetwork.com/news/topstories/metro/traffic-on-edsa/story",
            }
        ]
    )

    articles = [
        {
            "url": "https://www.gmanetwork.com/news/topstories/metro/traffic-on-edsa/story",
            "domain": "gmanetwork.com",
            "text_snippet": "Traffic on EDSA worsens after accident | 2026-05-01 08:15:00",
        }
    ]

    def mock_distilbert_score(text: str) -> float:
        lowered = text.lower()
        if "accident" in lowered or "traffic" in lowered:
            return 0.91
        return 0.10

    fused = fuse_structured_and_text_events(
        structured,
        articles,
        severity_scorer=mock_distilbert_score,
    )

    print(fused[["SOURCEURL", "Trust_Score", "DistilBERT_Raw_Severity_Score", "Fused_Severity_Weight"]])

if __name__ == "__main__":
    demo()