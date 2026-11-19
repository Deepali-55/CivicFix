"""Educational TF-IDF + Logistic Regression complaint category classifier.

The small built-in dataset is a demonstration seed, not a production training corpus.
Replace/expand it with reviewed, consented and representative local complaint examples.
"""
from functools import lru_cache
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

TRAINING_EXAMPLES = {
    "Road Damage": [
        "There is a deep pothole on the main road",
        "Road surface is broken and damaged",
        "Many potholes are causing trouble for vehicles",
        "The street has cracks and uneven pavement",
        "Please repair the damaged road near the bus stop",
        "A portion of the road has collapsed",
        "The road is full of holes after the rain",
        "Footpath tiles and road pavement are broken",
        "The junction road needs resurfacing",
        "A pothole is creating traffic problems",
    ],
    "Garbage": [
        "Garbage is not collected from our street",
        "Waste is piled up near the market",
        "Dustbins are overflowing with rubbish",
        "There is litter and plastic waste on the road",
        "Please clean the garbage dump near our house",
        "The municipal waste collection vehicle has not arrived",
        "Bad smell is coming from accumulated waste",
        "Trash is scattered around the public park",
        "The bin is full and waste is spilling out",
        "Garbage has been dumped beside the school",
    ],
    "Streetlight": [
        "Street light is not working at night",
        "The road is dark because the lamp is broken",
        "Several streetlights are switched off",
        "Please repair the electric street lamp",
        "The streetlight near the crossing is flickering",
        "There is no lighting on our street",
        "The public lamp post bulb has failed",
        "Street lighting is unavailable near the bus stop",
        "The road lamp is damaged",
        "The street light does not turn on after sunset",
    ],
    "Water Leakage": [
        "Water is leaking from the pipeline",
        "A water pipe has burst near our street",
        "Clean drinking water is being wasted due to leakage",
        "There is continuous water leakage near the house",
        "The public water supply pipe is damaged",
        "Water is flowing from a broken underground pipe",
        "Please fix the leaking tap in the public area",
        "A pipeline leak is flooding the road",
        "Water is coming out of the damaged main pipe",
        "There is a leak in the municipal water line",
    ],
    "Other": [
        "A public park bench is broken",
        "Please repair the damaged playground equipment",
        "There is an obstruction on the footpath",
        "A public signboard has fallen down",
        "The community hall needs maintenance",
        "An animal is trapped in a public place",
        "The drainage cover is missing",
        "A tree branch is blocking the footpath",
        "The public toilet needs attention",
        "There is a damaged public property item",
    ],
}

@lru_cache(maxsize=1)
def _model():
    texts, labels = [], []
    for label, examples in TRAINING_EXAMPLES.items():
        texts.extend(examples)
        labels.extend([label] * len(examples))
    classifier = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True)),
        ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    classifier.fit(texts, labels)
    return classifier

def suggest_category(description):
    model = _model()
    probabilities = model.predict_proba([description])[0]
    best_index = probabilities.argmax()
    category = model.classes_[best_index]
    confidence = float(probabilities[best_index])
    # Low-confidence text is not force-classified; keep citizen choice.
    if confidence < 0.30:
        return {"suggestion": None, "confidence": round(confidence, 2),
                "message": "The description is unclear. Please choose the category yourself."}
    return {"suggestion": category, "confidence": round(confidence, 2),
            "message": "AI suggestion only — please review and choose the correct category."}
