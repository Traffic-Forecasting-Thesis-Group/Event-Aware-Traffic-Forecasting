from __future__ import annotations

import math
from  typing import Callable, Iterable
from urllib.parse import urlparse, urlunparse

import pandas as pd

TRUST_SCORE_SCALE: dict[str, float] = {
    "gmanetwork.com": 0.94,
    "inquirer.net": 0.93,
    "rappler.com": 0.92,
    "philstar.com": 0.90,
    "abs-cbn.com": 0.90,
    "news.abs-cbn.com": 0.90,
    "pna.gov.ph": 0.89,
    "mb.com.ph": 0.86,
    "manilatimes.net": 0.84,
    "dost.gov.ph": 0.88,
    "pagasa.dost.gov.ph": 0.88,
    "cnnphilippines.com": 0.87,
}

def normalize_url(url: str | None) -> str:
    if not url: 
        return ""
    parsed = urlparse(url.strip())
    if not parsed.scheme: 
        parsed = urlparse("http://" + url.strip())
    cleaned = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower().lstrip("www.", ""),
        params="",
        query="",
        fragment="",
    )
    return urlunparse(cleaned)

def normalize_domain(domain: str | None) -> str:
    if not domain:
        return ""
    domain = domain.strip().lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def extract_domain_from_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def trust_score_for_domain(domain: str | None) -> float:
    cleaned = normalize_domain(domain)
    if not cleaned:
        return 0.35

    if cleaned in TRUST_SCORES:
        return TRUST_SCORES[cleaned]

    for trusted_domain, score in TRUST_SCORES.items():
        if cleaned.endswith(trusted_domain):
            return score

    return 0.35

def mention_multiplier(num_mentions: float | int | None) -> float:
    mentions = max(float(num_mentions or 0), 0.0)
    return 1.0 + min(math.log1p(mentions) / 4.0, 0.75)

def default_distilbert_severity_score(text: str) -> float:
    return 0.0
    
def fuse_structured_and_unstructured_events(
    structured_frame: pd.DataFrame,
    article_records: Iterable[dict[str, object]],
    severity_scorer: Callable[[str], float] = None,
    min_raw_severity: float = 0.35,
    min_trust_score: float = 0.55,
) -> pd.DataFrame:
    structured_frame = structured_frame.copy()
    if "SOURCEURL" not in structured.columns:
        raise ValueError("Structured DataFrame must contain 'SOURCEURL' column")
    if "NumMentions" not in structured.columns:
        structured_frame["NumMentions"] = 0
        
    structured["normalized_url"] = structured["SOURCEURL"].astype(str).map(normalize_url)

    articles = pd.DataFrame(list(article_records))
    if articles.empty:
        articles = pd.DataFrame(columns=["url", "domain", "text_snippet"])
    if "url" not in articles.columns:
        articles["url"] = ""
    if "domain" not in articles.columns:
        articles["domain"] = ""
    if "text_snippet" not in articles.columns:
        articles["text_snippet"] = ""

    articles["normalized_url"] = articles["url"].astype(str).map(normalize_url)

    merged = structured.merge(
        articles[["normalized_url", "url", "domain", "text_snippet"]],
        on="normalized_url",
        how="left",
        suffixes=("_bq", "_doc"),
    )

    merged["resolved_domain"] = merged["domain"].fillna(
        merged["SOURCEURL"].astype(str).map(extract_domain_from_url)
    )
    merged["Trust_Score"] = merged["resolved_domain"].map(trust_score_for_domain)

    scorer = severity_scorer or default_distilbert_severity_score
    merged["DistilBERT_Raw_Severity_Score"] = merged["text_snippet"].fillna("").map(
        lambda text: float(scorer(str(text)))
    )
    merged["Mention_Multiplier"] = merged["NumMentions"].map(mention_multiplier)
    
    merged["Verification_Passed"] = (
        (merged["DistilBERT_Raw_Severity_Score"] >= min_raw_severity)
        & (merged["Trust_Score"] >= min_trust_score)
        & merged["text_snippet"].fillna("").ne("")
    )

    merged["Fused_Severity_Weight"] = merged.apply(
        lambda row: round(
            row["DistilBERT_Raw_Severity_Score"]
            * row["Trust_Score"]
            * row["Mention_Multiplier"],
            4,
        )
        if row["Verification_Passed"]
        else 0.0,
        axis=1,
    )

    return merged.sort_values(
        by=["Fused_Severity_Weight", "NumMentions"],
        ascending=[False, False],
        kind="mergesort",
    ).reset_index(drop=True)