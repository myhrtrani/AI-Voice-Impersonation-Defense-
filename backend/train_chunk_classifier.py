from pathlib import Path

import numpy as np
import librosa
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report


# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATASET_1 = Path(
    r"C:\Users\srekh\OneDrive\Desktop\HACKATHON_SIH_2_TESTING_PHASE_1"
)

DATASET_2 = Path(
    r"C:\Users\srekh\OneDrive\Desktop\HACKATHON_VOICE_SAMPLES_TESTING"
)

MODEL_PATH = (
    PROJECT_DIR
    / "backend"
    / "models"
    / "hackathon_voice_classifier_chunked.joblib"
)


# ============================================================
# SETTINGS
# ============================================================

SAMPLE_RATE = 16000

CHUNK_DURATION = 2.5
CHUNK_SAMPLES = int(
    SAMPLE_RATE * CHUNK_DURATION
)

MIN_CHUNK_SAMPLES = int(
    SAMPLE_RATE * 0.2
)

AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
}


# ============================================================
# DATASET
# ============================================================

DATASET_FOLDERS = [
    (DATASET_1 / "human_recording_tests", 0),
    (DATASET_1 / "ai_voice_records", 1),
    (DATASET_2 / "HUMAN_VOICES", 0),
    (DATASET_2 / "AI_VOICES", 1),
]


# ============================================================
# FEATURE EXTRACTION
# EXACTLY 189 FEATURES
# ============================================================

def extract_features(y, sr):

    features = []

    # --------------------------------------------------------
    # MFCC
    # 20 × 4 = 80
    # --------------------------------------------------------

    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=20
    )

    features.extend(np.mean(mfcc, axis=1))
    features.extend(np.std(mfcc, axis=1))
    features.extend(np.min(mfcc, axis=1))
    features.extend(np.max(mfcc, axis=1))

    # --------------------------------------------------------
    # MFCC DELTA
    # 20 × 4 = 80
    # --------------------------------------------------------

    delta = librosa.feature.delta(mfcc)

    features.extend(np.mean(delta, axis=1))
    features.extend(np.std(delta, axis=1))
    features.extend(np.min(delta, axis=1))
    features.extend(np.max(delta, axis=1))

    # --------------------------------------------------------
    # SPECTRAL FEATURES
    # 5 × 4 = 20
    # --------------------------------------------------------

    spectral_features = [
        librosa.feature.spectral_centroid(
            y=y,
            sr=sr
        ),

        librosa.feature.spectral_bandwidth(
            y=y,
            sr=sr
        ),

        librosa.feature.spectral_rolloff(
            y=y,
            sr=sr
        ),

        librosa.feature.spectral_flatness(
            y=y
        ),

        librosa.feature.zero_crossing_rate(
            y=y
        ),
    ]

    for feature in spectral_features:

        features.append(float(np.mean(feature)))
        features.append(float(np.std(feature)))
        features.append(float(np.min(feature)))
        features.append(float(np.max(feature)))

    # --------------------------------------------------------
    # PITCH
    # 4
    # --------------------------------------------------------

    try:

        pitch = librosa.yin(
            y,
            fmin=50,
            fmax=500,
            sr=sr
        )

        pitch = pitch[np.isfinite(pitch)]

        if len(pitch) > 0:

            features.extend([
                float(np.mean(pitch)),
                float(np.std(pitch)),
                float(np.min(pitch)),
                float(np.max(pitch)),
            ])

        else:

            features.extend([
                0.0,
                0.0,
                0.0,
                0.0,
            ])

    except Exception:

        features.extend([
            0.0,
            0.0,
            0.0,
            0.0,
        ])

    # --------------------------------------------------------
    # RMS
    # 4
    # --------------------------------------------------------

    rms = librosa.feature.rms(y=y)

    features.extend([
        float(np.mean(rms)),
        float(np.std(rms)),
        float(np.min(rms)),
        float(np.max(rms)),
    ])

    # --------------------------------------------------------
    # PEAK
    # 1
    # --------------------------------------------------------

    features.append(
        float(np.max(np.abs(y)))
    )

    features = np.asarray(
        features,
        dtype=np.float32
    )

    if features.shape != (189,):

        raise RuntimeError(
            f"Expected 189 features, got {features.shape}"
        )

    if not np.all(np.isfinite(features)):

        raise RuntimeError(
            "Feature vector contains NaN or infinity."
        )

    return features


# ============================================================
# FIND RECORDINGS
# ============================================================

def find_recordings():

    recordings = []

    for folder, label in DATASET_FOLDERS:

        if not folder.exists():

            raise FileNotFoundError(
                f"Dataset folder not found:\n{folder}"
            )

        for file_path in sorted(folder.iterdir()):

            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue

            recordings.append(
                {
                    "path": file_path,
                    "label": label,
                    "group": str(file_path.resolve()),
                }
            )

    return recordings


# ============================================================
# EXTRACT CHUNKS
# ============================================================

def build_chunk_dataset(recordings):

    X = []
    y_labels = []
    groups = []

    total_chunks = 0

    for index, recording in enumerate(recordings, start=1):

        file_path = recording["path"]
        label = recording["label"]
        group = recording["group"]

        print(
            f"[{index:02d}/{len(recordings)}] "
            f"Processing {file_path.name}"
        )

        audio, sr = librosa.load(
            str(file_path),
            sr=SAMPLE_RATE,
            mono=True
        )

        if len(audio) == 0:

            raise RuntimeError(
                f"Empty audio file:\n{file_path}"
            )

        num_chunks = int(
            np.ceil(
                len(audio) / CHUNK_SAMPLES
            )
        )

        valid_chunks = 0

        for chunk_index in range(num_chunks):

            start = (
                chunk_index
                * CHUNK_SAMPLES
            )

            end = min(
                start + CHUNK_SAMPLES,
                len(audio)
            )

            chunk = audio[start:end]

            # Ignore fragments shorter than 200 ms
            if len(chunk) < MIN_CHUNK_SAMPLES:
                continue

            # Pad final chunk to 2.5 seconds
            if len(chunk) < CHUNK_SAMPLES:

                chunk = np.pad(
                    chunk,
                    (
                        0,
                        CHUNK_SAMPLES - len(chunk)
                    )
                )

            feature_vector = extract_features(
                chunk,
                sr
            )

            X.append(feature_vector)
            y_labels.append(label)

            # IMPORTANT:
            # Every chunk from the SAME recording
            # gets the SAME group identifier.
            groups.append(group)

            valid_chunks += 1
            total_chunks += 1

        print(
            f"    chunks used: {valid_chunks}"
        )

    X = np.asarray(
        X,
        dtype=np.float32
    )

    y_labels = np.asarray(
        y_labels,
        dtype=np.int64
    )

    groups = np.asarray(
        groups
    )

    return X, y_labels, groups


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("CORRECTED CHUNK-LEVEL VOICE CLASSIFIER TRAINING")
    print("=" * 70)

    # --------------------------------------------------------
    # Find recordings
    # --------------------------------------------------------

    recordings = find_recordings()

    human_count = sum(
        r["label"] == 0
        for r in recordings
    )

    ai_count = sum(
        r["label"] == 1
        for r in recordings
    )

    print()
    print(
        f"Recordings found : {len(recordings)}"
    )

    print(
        f"HUMAN recordings : {human_count}"
    )

    print(
        f"AI recordings    : {ai_count}"
    )

    if len(recordings) != 32:
        raise RuntimeError(
            f"Expected exactly 32 recordings, "
            f"found {len(recordings)}."
        )

    if human_count != 17:
        raise RuntimeError(
            f"Expected 17 HUMAN recordings, "
            f"found {human_count}."
        )

    if ai_count != 15:
        raise RuntimeError(
            f"Expected 15 AI recordings, "
            f"found {ai_count}."
        )

    print()
    print("Dataset check PASSED.")

    # --------------------------------------------------------
    # Build chunk dataset
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("EXTRACTING 2.5-SECOND CHUNKS")
    print("=" * 70)

    X, y_labels, groups = build_chunk_dataset(
        recordings
    )

    print()
    print(
        f"Feature matrix : {X.shape}"
    )

    print(
        f"Labels         : {y_labels.shape}"
    )

    print(
        f"Unique groups  : {len(np.unique(groups))}"
    )

    if X.shape[1] != 189:

        raise RuntimeError(
            f"Expected 189 features, "
            f"got {X.shape[1]}."
        )

    # --------------------------------------------------------
    # GROUP-AWARE LEAVE-ONE-RECORDING-OUT VALIDATION
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("GROUP-AWARE VALIDATION")
    print("=" * 70)

    print()
    print(
        "Each recording is kept entirely in either"
    )
    print(
        "training OR testing for every validation fold."
    )

    logo = LeaveOneGroupOut()

    predictions = np.zeros_like(
        y_labels
    )

    probabilities = np.zeros(
        len(y_labels),
        dtype=np.float32
    )

    fold_number = 0

    for train_index, test_index in logo.split(
        X,
        y_labels,
        groups
    ):

        fold_number += 1

        train_X = X[train_index]
        train_y = y_labels[train_index]

        test_X = X[test_index]

        model = RandomForestClassifier(
            n_estimators=500,
            class_weight="balanced",
            max_features="sqrt",
            random_state=42,
            n_jobs=-1
        )

        model.fit(
            train_X,
            train_y
        )

        predictions[test_index] = model.predict(
            test_X
        )

        probabilities[test_index] = (
            model.predict_proba(test_X)[:, 1]
        )

        print(
            f"Fold {fold_number:02d}/32 complete"
        )

    # --------------------------------------------------------
    # VALIDATION RESULTS
    # --------------------------------------------------------

    accuracy = accuracy_score(
        y_labels,
        predictions
    )

    cm = confusion_matrix(
        y_labels,
        predictions
    )

    print()
    print("=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    print()
    print(
        f"Chunk-level accuracy: {accuracy * 100:.2f}%"
    )

    print()
    print("Confusion matrix:")
    print(cm)

    print()
    print("Classification report:")

    print(
        classification_report(
            y_labels,
            predictions,
            target_names=[
                "HUMAN",
                "AI"
            ],
            digits=4
        )
    )

    # --------------------------------------------------------
    # RECORDING-LEVEL VALIDATION
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RECORDING-LEVEL VALIDATION")
    print("=" * 70)

    recording_results = []

    for recording in recordings:

        group = recording["group"]

        mask = groups == group

        recording_probability = float(
            np.mean(
                probabilities[mask]
            )
        )

        actual = recording["label"]

        predicted = (
            1
            if recording_probability >= 0.50
            else 0
        )

        recording_results.append(
            predicted == actual
        )

        print(
            f"{recording['path'].name:40s} "
            f"Actual={'AI' if actual else 'HUMAN':5s} "
            f"MeanAI={recording_probability * 100:6.2f}% "
            f"{'CORRECT' if predicted == actual else 'WRONG'}"
        )

    recording_accuracy = (
        np.mean(recording_results)
        * 100.0
    )

    print()
    print(
        f"Recording-level accuracy: "
        f"{recording_accuracy:.2f}%"
    )

    # --------------------------------------------------------
    # FINAL MODEL
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("TRAINING FINAL MODEL")
    print("=" * 70)

    final_model = RandomForestClassifier(
        n_estimators=1000,
        class_weight="balanced",
        max_features="sqrt",
        random_state=42,
        n_jobs=-1
    )

    final_model.fit(
        X,
        y_labels
    )

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(
        final_model,
        MODEL_PATH
    )

    print()
    print(
        "FINAL MODEL SAVED:"
    )

    print(
        MODEL_PATH
    )

    print()
    print(
        f"Trees    : {final_model.n_estimators}"
    )

    print(
        f"Features : {final_model.n_features_in_}"
    )

    print(
        f"Classes  : {final_model.classes_}"
    )

    print()
    print("=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()