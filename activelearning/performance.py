import numpy as np
import torch


class ModelPerformance:
    def __init__(self, df):
        self.df = df

    def analyze(self):

        self.probs = self.predict()
        self.y = self.df["y"].values

        predicted_labels = torch.argmax(self.probs, dim=1).detach().numpy()

        self.TP = ((predicted_labels == 1) & (self.y == 1)).sum()
        self.TN = ((predicted_labels == 0) & (self.y == 0)).sum()
        self.FP = ((predicted_labels == 1) & (self.y == 0)).sum()
        self.FN = ((predicted_labels == 0) & (self.y == 1)).sum()

        self.MCC = self.compute_MCC()
        self.recall = self.compute_recall()
        self.precision = self.compute_precision()
        self.accuracy = self.compute_accuracy()

        self.metric_dict = {"MCC": self.MCC, "Precision": self.precision, "Recall": self.recall, "Accuracy": self.accuracy}

    def compute_accuracy(self):
        """Compute overall accuracy from label predictions"""

        return self._accuracy(self.probs, self.y)

    def _accuracy(self, prob_labels, y):

        return (torch.argmax(prob_labels, dim=1).detach().numpy() == y).sum() / len(y)

    def compute_MCC(self):
        """Matthews correlation coefficient"""

        nominator = self.TP * self.TN - self.FP * self.FN
        denominator_squared = (self.TP + self.FP) * (self.TP + self.FN) * (self.TN + self.FP) * (self.TN + self.FN)

        return nominator / np.sqrt(denominator_squared)

    def compute_recall(self):
        """Fraction of true class 1 and all class 1"""

        return self.TP / (self.TP + self.FN)

    def compute_precision(self):
        """Fraction of true class 1 and predicted class 1"""

        return self.TP / (self.TP + self.FP)

    def print_metrics(self):

        print("MCC:", self.MCC, ", Precision:", self.precision, ", Recall:", self.recall, ", Accuracy:", self.accuracy)


    