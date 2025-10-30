from typing import Tuple
import numpy as np
from tensorflow import keras
from tensorflow.keras import layers


class LstmPredictor:
    """A minimal LSTM regressor for next-step price prediction."""

    def __init__(self, window: int = 50, units: int = 32):
        self.window = window
        self.units = units
        self.model = keras.Sequential(
            [
                layers.Input(shape=(window, 1)),
                layers.LSTM(units),
                layers.Dense(1),
            ]
        )
        self.model.compile(optimizer="adam", loss="mse")

    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 10, batch_size: int = 32, validation_split: float = 0.1):
        return self.model.fit(X, y, epochs=epochs, batch_size=batch_size, validation_split=validation_split, verbose=0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X, verbose=0).reshape(-1)
