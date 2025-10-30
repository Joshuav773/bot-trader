from typing import Dict
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch


class SentimentAnalyzer:
    """Financial text sentiment analyzer using the FinBERT model."""

    def __init__(self, model_name: str = "ProsusAI/finbert"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

    @torch.inference_mode()
    def analyze(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of input text.

        Returns a mapping of label -> probability based on model's id2label.
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        outputs = self.model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]

        id2label = self.model.config.id2label
        result: Dict[str, float] = {}
        for idx, p in enumerate(probs.tolist()):
            label = id2label.get(idx, str(idx)).lower()
            result[label] = float(p)
        return result
