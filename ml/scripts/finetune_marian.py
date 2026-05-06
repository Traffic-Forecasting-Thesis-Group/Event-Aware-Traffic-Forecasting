#!/usr/bin/env python3
"""
Fine-tune MarianMT on Taglish→English parallel corpus.

Usage:
    python ml/scripts/finetune_mariaNMT.py \\
        --corpus data/corpus/taglish_english_parallel.jsonl \\
        --output ml/models/mariannt-tl-en-finetuned \\
        --epochs 3 \\
        --batch_size 16

The script:
1. Loads parallel Taglish↔English corpus
2. Splits into train/validation/test sets
3. Fine-tunes Helsinki-NLP/opus-mt-tl-en
4. Saves fine-tuned model
5. Evaluates on test set and reports BLEU/METEOR
"""
import json
import logging
from pathlib import Path
from typing import Optional
import argparse

import numpy as np
import torch
from datasets import Dataset
from torch.utils.data import DataLoader
from transformers import (
    MarianMTModel,
    MarianTokenizer,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)
from sacrebleu import corpus_bleu

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaglishCorpusLoader:
    """Load and split Taglish↔English parallel corpus."""

    def __init__(self, corpus_path: str):
        self.corpus_path = Path(corpus_path)
        self.data = self._load_corpus()

    def _load_corpus(self) -> list[dict]:
        """Load JSONL corpus."""
        data = []
        with open(self.corpus_path) as f:
            for line in f:
                data.append(json.loads(line))
        logger.info(f"Loaded {len(data)} parallel sentences from {self.corpus_path}")
        return data

    def to_huggingface_dataset(self, train_size: float = 0.8, val_size: float = 0.1):
        """Split corpus into train/val/test and return HF datasets."""
        # Shuffle
        indices = np.random.permutation(len(self.data))
        data_shuffled = [self.data[i] for i in indices]

        # Split
        n_train = int(len(data_shuffled) * train_size)
        n_val = int(len(data_shuffled) * val_size)

        train_data = data_shuffled[:n_train]
        val_data = data_shuffled[n_train : n_train + n_val]
        test_data = data_shuffled[n_train + n_val :]

        logger.info(f"Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}")

        # Convert to HF Dataset format
        def to_hf_format(data_list):
            return Dataset.from_dict(
                {
                    "translation": [{"tl": item["tl"], "en": item["en"]} for item in data_list]
                }
            )

        return to_hf_format(train_data), to_hf_format(val_data), to_hf_format(test_data)


class MarianFineTuner:
    """Fine-tune MarianMT on Taglish↔English corpus."""

    def __init__(
        self,
        model_name: str = "Helsinki-NLP/opus-mt-tl-en",
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        logger.info(f"Loading model {model_name} on device {self.device}")
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name)
        self.model.to(self.device)

    def preprocess_batch(self, batch):
        """Tokenize batch."""
        inputs = self.tokenizer(
            batch["translation"],
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )

        # Force BOS token for decoder (MarianMT specific)
        labels = inputs["input_ids"].clone()
        labels[labels == self.tokenizer.pad_token_id] = -100

        return {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
            "labels": labels,
        }

    def fine_tune(
        self,
        train_dataset: Dataset,
        val_dataset: Dataset,
        output_dir: str,
        num_epochs: int = 3,
        batch_size: int = 16,
        learning_rate: float = 5e-5,
        warmup_steps: int = 500,
        max_grad_norm: float = 1.0,
    ):
        """Fine-tune model."""
        # Preprocess datasets
        logger.info("Preprocessing datasets...")
        train_dataset = train_dataset.map(
            self.preprocess_batch,
            batched=True,
            remove_columns=["translation"],
        )
        val_dataset = val_dataset.map(
            self.preprocess_batch,
            batched=True,
            remove_columns=["translation"],
        )

        # Training arguments
        training_args = Seq2SeqTrainingArguments(
            output_dir=output_dir,
            overwrite_output_dir=True,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            weight_decay=0.01,
            max_grad_norm=max_grad_norm,
            save_strategy="epoch",
            evaluation_strategy="epoch",
            logging_steps=10,
            logging_dir=f"{output_dir}/logs",
            predict_with_generate=True,
            generation_max_length=256,
            gradient_accumulation_steps=2,
            fp16=torch.cuda.is_available(),  # Mixed precision on GPU
        )

        # Trainer
        trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=self.tokenizer,
        )

        # Fine-tune
        logger.info("Starting fine-tuning...")
        trainer.train()

        # Save
        logger.info(f"Saving fine-tuned model to {output_dir}")
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)

        return self.model

    def evaluate(self, test_dataset: Dataset, model_output_dir: str) -> dict:
        """Evaluate on test set."""
        logger.info("Evaluating on test set...")

        # Load fine-tuned model
        model = MarianMTModel.from_pretrained(model_output_dir)
        tokenizer = MarianTokenizer.from_pretrained(model_output_dir)
        model.to(self.device)
        model.eval()

        references = []
        predictions = []

        for item in test_dataset:
            src = item["translation"]["tl"]
            ref = item["translation"]["en"]

            # Tokenize
            inputs = tokenizer(src, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate
            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=256, num_beams=4)

            pred = tokenizer.decode(outputs[0], skip_special_tokens=True)

            references.append([ref])  # sacrebleu expects list of reference lists
            predictions.append(pred)

        # Compute BLEU
        bleu = corpus_bleu(predictions, references)

        logger.info(f"BLEU Score: {bleu.score:.2f}")
        logger.info(f"Sample predictions:")
        for i in range(min(5, len(predictions))):
            logger.info(f"  REF: {references[i][0]}")
            logger.info(f"  PRED: {predictions[i]}")

        return {"bleu": bleu.score, "predictions": predictions, "references": references}


def main():
    parser = argparse.ArgumentParser(description="Fine-tune MarianMT on Taglish corpus")
    parser.add_argument("--corpus", required=True, help="Path to parallel corpus JSONL")
    parser.add_argument("--output", required=True, help="Output directory for fine-tuned model")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--warmup", type=int, default=500, help="Warmup steps")
    parser.add_argument("--no_eval", action="store_true", help="Skip evaluation")

    args = parser.parse_args()

    # Load corpus
    loader = TaglishCorpusLoader(args.corpus)
    train_dataset, val_dataset, test_dataset = loader.to_huggingface_dataset()

    # Fine-tune
    finetuner = MarianFineTuner()
    finetuner.fine_tune(
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        output_dir=args.output,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        warmup_steps=args.warmup,
    )

    # Evaluate
    if not args.no_eval:
        results = finetuner.evaluate(test_dataset, args.output)
        logger.info(f"Evaluation results: {results}")


if __name__ == "__main__":
    main()
