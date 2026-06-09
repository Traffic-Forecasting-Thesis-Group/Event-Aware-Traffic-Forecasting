"""Taglish -> English translation utility using MarianMT (Helsinki-NLP/opus-mt-tl-en).

Usage:
  - Install dependencies:
      pip install transformers torch sentencepiece

  - Example:
      from backend.app.preprocessing.taglish_translator import TaglishTranslator
      t = TaglishTranslator()
      english = t.translate_texts(["Accident sa EDSA! traffic heavy", "Bagong update: flooding @area com "]) 

Design notes:
  - Uses batch tokenization and model.generate to avoid per-text latency.
  - Dynamically maps to GPU (CUDA/MPS) when available, otherwise CPU.
  - Pre-translation regex cleaning to strip URLs, mentions, and noise.
  - Safe for lists or pandas DataFrame columns.
"""
from __future__ import annotations

import logging
import re
from typing import Iterable, List, Optional

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, MarianMTModel, MarianTokenizer, pipeline

logger = logging.getLogger(__name__)


class TaglishTranslator:
    """Translate Tagalog / Taglish text to English using MarianMT.

    Features:
    - Batch processing using tokenizer to avoid per-text overhead.
    - Dynamic device selection (CUDA, MPS, CPU).
    - Pre-translation regex cleaning to strip URLs, mentions, and noise.
    - Methods for translating lists and pandas DataFrame columns.
    """

    CLEAN_RE = re.compile(
        r"(https?://\S+)|(@\w+)|([^\w\s\u00C0-\u017F,.!?'-])", re.UNICODE
    )

    # Entity type mappings: preserve tokens that are LOC, ORG, PER, MISC
    PRESERVE_ENTITY_TYPES = {"LOC", "ORG", "PER", "MISC", "PERSON", "LOCATION", "ORGANIZATION"}

    # Manila-centric place-name gazetteer (fallback for NER)
    MANILA_GAZETTEER = {
        # --- The Original LGU & Broad Locations ---
        "quezon city", "qc", "mandaluyong", "pasig", "marikina", "las pinas", 
        "paranaque", "muntinlupa", "makati", "pateros", "taguig", "navotas", 
        "malabon", "caloocan", "valenzuela", "pasay", "manila", "ncr", "mmda", "lgu",
    
        # --- Major Highways & Tollways (Crucial Additions) ---
        "edsa", "c5", "c-5", "c3", "c4", "slex", "nlex", "skyway", "cavitex", 
        "naiax", "mcx", "commonwealth", "marcos highway", "roxas blvd", "macapagal",
    
        # --- Notorious Traffic Avenues & Boulevards ---
        "espana", "españa", "recto", "taft", "taft ave", "quezon ave", "q ave", "q. ave",
        "buendia", "gil puyat", "shaw", "shaw blvd", "ortigas", "ortigas ave", 
        "katipunan", "quirino", "quirino ave", "ayala", "ayala ave", "kalayaan",
        "boni", "pioneer", "timog", "tomas morato", "east ave", "lawton", "boso-boso",
    
        # --- Specific EDSA Choke Points / Intersections ---
        # (MMDA tweets heavily rely on these node names)
        "balintawak", "monumento", "munoz", "muñoz", "roosevelt", "north ave", 
        "kamuning", "cubao", "santolan", "boni", "guadalupe", "guada", "magallanes",
    
        # --- South / Alabang Traffic Nodes ---
        "alabang", "alabang-zapote", "zapote", "sucat", "bicutan", "bf homes",

        # --- Manila Districts & Specific Hubs ---
        "sta. mesa", "stametesa", "quiapo", "divisoria", "ermita", "sampaloc", 
        "malate", "paco", "santa cruz", "santacruz", "bagumbayan", "pandacan", 
        "intramuros", "tondo", "binondo", "san nicolas",

        # --- Major Landmarks / Commercial Hubs ---
        "bgc", "fort bonifacio", "mckinley", "sm", "robinsons", "mall of asia", "moa", 
        "megamall", "trinoma", "greenhills", "eastwood", "cubao expo"
    }

    def __init__(
        self,
        model_name: str = "Helsinki-NLP/opus-mt-tl-en",
        device: Optional[torch.device] = None,
        max_length: int = 256,
    ) -> None:
        """Load tokenizer and model, map to device.

        Args:
            model_name: HF model id for MarianMT tl->en.
            device: optional torch.device override. If None the class will detect GPU.
            max_length: generation max length per sample (used to truncate tokens).
        """
        # device mapping: prefer CUDA, then MPS (mac), else CPU
        if device is None:
            if torch.cuda.is_available():
                device = torch.device("cuda")
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                device = torch.device("mps")
            else:
                device = torch.device("cpu")

        self.device = device
        self.model_name = model_name
        self.max_length = max_length
        self.ner_pipeline = None

        # Load tokenizer and model once; keep in memory for repeated calls
        try:
            # Some transformers versions fail to resolve Marian via AutoTokenizer.
            # Prefer explicit Marian classes and fallback to Auto* for compatibility.
            try:
                self.tokenizer = MarianTokenizer.from_pretrained(model_name)
                self.model = MarianMTModel.from_pretrained(model_name)
            except Exception:
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            # move model to device for fast inference
            self.model.to(self.device)
        except Exception as e:
            raise RuntimeError(f"Failed to load model {model_name}: {e}")

        # Lazy-load NER pipeline on first use to avoid startup latency
        self._ner_initialized = False

    def _init_ner(self):
        """Lazy initialization of NER pipeline."""
        if self._ner_initialized:
            return
        try:
            # Use XLM-RoBERTa based multilingual NER model (widely available)
            self.ner_pipeline = pipeline(
                "ner",
                model="xlm-roberta-large-finetuned-conll03-english",
                device=0 if self.device.type == "cuda" else -1,
                aggregation_strategy="simple",
            )
            self._ner_initialized = True
            logger.info("NER pipeline initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize NER pipeline: {e}. Using gazetteer-based fallback only.")
            self.ner_pipeline = None
            self._ner_initialized = True

    def _gazetteer_mask_entities(self, text: str) -> tuple:
        """Gazetteer-based entity masking for place names and org names.
        Fallback when NER is unavailable.

        Args:
            text: raw input text

        Returns:
            (masked_text, entity_mapping) where mapping is {placeholder: original_text}
        """
        entity_mapping = {}
        masked_text = text
        placeholder_idx = 0

        # Find all tokens in text and check against gazetteer
        import re
        tokens = re.findall(r"\b[\w'-]+\b", text, re.UNICODE)
        unique_tokens = {t.lower(): t for t in tokens}  # preserve original case

        # Sort by length (longest first) to avoid partial replacements
        sorted_tokens = sorted(unique_tokens.items(), key=lambda x: len(x[0]), reverse=True)

        for lower_token, orig_token in sorted_tokens:
            if lower_token in self.MANILA_GAZETTEER:
                placeholder = f"<LOC_{placeholder_idx}>"
                entity_mapping[placeholder] = orig_token
                # Use word boundary replacement to avoid partial matches
                masked_text = re.sub(
                    rf"\b{re.escape(orig_token)}\b", placeholder, masked_text, flags=re.IGNORECASE
                )
                placeholder_idx += 1

        return masked_text, entity_mapping

    def _mask_entities(self, text: str) -> tuple:
        """Detect entities in text using NER and mask them with placeholders.
        Falls back to gazetteer-based masking if NER is unavailable.

        Args:
            text: raw input text

        Returns:
            (masked_text, entity_mapping) where mapping is {placeholder: original_text}
        """
        # Prefer NER if available
        if self.ner_pipeline:
            try:
                truncated = text[: self.max_length * 2]
                entities = self.ner_pipeline(truncated)

                if not entities:
                    # Fall back to gazetteer if NER found nothing
                    return self._gazetteer_mask_entities(text)

                entity_spans = []
                for ent in entities:
                    ent_type = ent.get("entity_group", "").upper()
                    if ent_type in self.PRESERVE_ENTITY_TYPES:
                        entity_spans.append((ent["start"], ent["end"], ent["word"], ent_type))

                if not entity_spans:
                    return text, {}

                entity_spans.sort(key=lambda x: x[0], reverse=True)
                masked_text = text
                entity_mapping = {}
                placeholder_idx = 0

                for start, end, word, ent_type in entity_spans:
                    placeholder = f"<{ent_type}_{placeholder_idx}>"
                    entity_mapping[placeholder] = word
                    masked_text = masked_text[:start] + placeholder + masked_text[end:]
                    placeholder_idx += 1

                return masked_text, entity_mapping

            except Exception as e:
                logger.warning(f"NER masking failed: {e}. Falling back to gazetteer.")
                return self._gazetteer_mask_entities(text)
        else:
            # Use gazetteer fallback directly if NER not initialized
            return self._gazetteer_mask_entities(text)

    def _unmask_entities(self, text: str, entity_mapping: dict) -> str:
        """Restore masked entities back into translated text.

        Args:
            text: translated text with placeholders
            entity_mapping: {placeholder: original_entity}

        Returns:
            text with entities restored
        """
        if not entity_mapping:
            return text

        for placeholder, entity in entity_mapping.items():
            text = text.replace(placeholder, entity)

        return text

    def _clean_text(self, text: str) -> str:
        """Lightweight regex-based cleaner applied before translation.

        - Removes URLs
        - Removes @mentions
        - Strips unusual special characters while preserving punctuation
        """
        if not isinstance(text, str):
            return ""
        text = text.strip()
        if not text:
            return ""
        # Remove urls and mentions and undesirable chars
        cleaned = self.CLEAN_RE.sub(lambda m: "" if (m.group(1) or m.group(2)) else m.group(0), text)
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _batches(self, iterable: List[str], batch_size: int):
        for i in range(0, len(iterable), batch_size):
            yield iterable[i : i + batch_size]

    def translate_texts(self, texts: Iterable[str], batch_size: int = 32, use_ner: bool = True) -> List[str]:
        """Translate a list/iterable of Taglish/Tagalog strings to English.

        Args:
            texts: iterable of raw strings
            batch_size: number of items to process per generation call
            use_ner: if True, use NER masking to preserve named entities

        Returns:
            List of translated English strings in the same order as input.
        """
        if use_ner:
            self._init_ner()

        texts_list = list(texts)
        if not texts_list:
            return []

        # Pre-clean all texts (fast regex) and remember indexes to preserve order
        cleaned_texts: List[str] = [self._clean_text(t) for t in texts_list]

        # Apply NER masking if enabled
        entity_mappings = []
        if use_ner:
            masked_texts = []
            for text in cleaned_texts:
                masked, mapping = self._mask_entities(text)
                masked_texts.append(masked)
                entity_mappings.append(mapping)
            cleaned_texts = masked_texts
        else:
            entity_mappings = [{} for _ in cleaned_texts]

        translations: List[str] = ["" for _ in cleaned_texts]

        # Process in batches to avoid per-item tokenization overhead
        for batch_idx, batch in enumerate(self._batches(cleaned_texts, batch_size)):
            # Skip empty batch
            if not any(batch):
                # preserve empty strings
                continue

            try:
                # Tokenize the batch together (padding/truncation for uniform tensor sizes)
                inputs = self.tokenizer(
                    batch,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                )

                # Move tensors to the model device
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                # Generate translations with beam search for quality
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs, max_length=self.max_length, num_beams=4, early_stopping=True
                    )

                decoded = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
                # Put back into the translations list
                start = batch_idx * batch_size
                for i, dec in enumerate(decoded):
                    translations[start + i] = dec.strip()

            except Exception:
                # If a batch fails (e.g., OOM or tokenization issue), process items individually
                start = batch_idx * batch_size
                for i, item in enumerate(batch):
                    try:
                        if not item:
                            translations[start + i] = ""
                            continue
                        single_inputs = self.tokenizer(
                            item,
                            return_tensors="pt",
                            truncation=True,
                            max_length=self.max_length,
                        )
                        single_inputs = {k: v.to(self.device) for k, v in single_inputs.items()}
                        with torch.no_grad():
                            out = self.model.generate(**single_inputs, max_length=self.max_length)
                        translations[start + i] = self.tokenizer.decode(out[0], skip_special_tokens=True).strip()
                    except Exception:
                        # Last resort: return the cleaned source text to avoid pipeline crash
                        translations[start + i] = batch[i] or ""

        # Restore entities in translated texts
        if use_ner:
            for i, mapping in enumerate(entity_mappings):
                translations[i] = self._unmask_entities(translations[i], mapping)

        return translations

    def translate_dataframe(self, df, column: str, out_column: Optional[str] = None, batch_size: int = 32, use_ner: bool = True):
        """Translate a pandas DataFrame column in batches and add results as a new column.

        Args:
            df: pandas DataFrame
            column: name of the column containing raw text
            out_column: name of the column to write translations to (defaults to column + '_en')
            batch_size: batch size for translation
            use_ner: if True, use NER masking to preserve named entities

        Returns:
            DataFrame with new column added (mutates in place and returns df)
        """
        try:
            import pandas as pd
        except Exception:
            raise RuntimeError("pandas is required for translate_dataframe")

        if out_column is None:
            out_column = f"{column}_en"

        texts = df[column].fillna("").astype(str).tolist()
        translations = self.translate_texts(texts, batch_size=batch_size, use_ner=use_ner)
        df[out_column] = translations
        return df


__all__ = ["TaglishTranslator"]
