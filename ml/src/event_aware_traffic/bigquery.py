from __future__ import annotations
from typing import Sequence

import pandas as pd

DEFAULT_TABLE = "gdelt-bq.gdeltv2.events"
DEFAULT_COLUMNS = [
    "SQLDATE",
    "EventRootCode",
    "NumMentions",
    "SOURCEURL",
    "ActionGeo_Lat",
    "ActionGeo_Long",
    "ActionGeo_CountryCode",
]

def build_gdelt_query(
        table_name: str = DEFAULT_TABLE,
        lookback_minutes: int = 60,
        country_code: str = "RP",
        root_codes: Sequence[str] = ("14", "15", "16", "17", "18"),
) -> str: 
    root_code_list = ",".join(f" '{code}'" for code in root_codes)
    return f"""
    SELECT
        SQLDATE,
        EventRootCode,
        NumMentions,
        SOURCEURL,
        ActionGeo_Lat,
        ActionGeo_Long,
        ActionGeo_CountryCode
    FROM `{table_name}`
    WHERE _PARTITIONTIME >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @lookback_minutes MINUTE)
        AND ActionGeo_CountryCode = @country_code
        AND EventRootCode IN ({root_code_list})
        AND SOURCEURL IS NOT NULL
        ORDER BY NumMentions DESC
    """

def query_recent_gdelt_events(
        project_id: str,
        table_name: str = DEFAULT_TABLE,
        lookback_minutes: int = 60,
        country_code: str = "RP",
        root_codes: Sequence[str] = ("14", "15", "16", "17", "18"),
) -> pd.DataFrame:
    try: 
        from google.cloud import bigquery
    except ImportError as exception:
        raise RuntimeError("Install Google Cloud BigQuery client library to query BigQuery") from exception
    
    client = bigquery.Client(project=project_id)
    query = build_gdelt_query(
        table_name = table_name,
        lookback_minutes = lookback_minutes,
        country_code = country_code,
        root_codes = root_codes
    )

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("lookback_minutes", "INT64", lookback_minutes),
            bigquery.ScalarQueryParameter("country_code", "STRING", country_code),
        ]
    )

    try: 
        job = client.query(query, job_config=job_config)
        frame = job.to_dataframe(create_bqstorage_client=False)
    except Exception as exception:
        raise RuntimeError("Failed to query BigQuery for GDELT events") from exception
    
    if frame.empty:
        return pd.DataFrame(columns=DEFAULT_COLUMNS)
    
    return frame.loc[:,[col for col in DEFAULT_COLUMNS if col in frame.columns]].copy()