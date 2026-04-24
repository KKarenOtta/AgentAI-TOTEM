from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import json

def train():
    model = SentenceTransformer("all-MiniLM-L6-v2")

    data = json.load(open("data/training_dataset.json"))

    train_examples = [
        InputExample(texts=[d["input"], d["output"]])
        for d in data
    ]

    loader = DataLoader(train_examples, shuffle=True, batch_size=8)
    loss = losses.CosineSimilarityLoss(model)

    model.fit(train_objectives=[(loader, loss)], epochs=1)

    model.save("models/semantic")

if __name__ == "__main__":
    train()
