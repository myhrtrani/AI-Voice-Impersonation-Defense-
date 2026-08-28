import os

src_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "official_AASIST_source.py"))
dst_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "app", "models", "aasist.py"))

with open(src_file, "r", encoding="utf-8") as f:
    code = f.read()

extra = '''

AASIST_L = Model


def pad_to_aasist_length(x: np.ndarray, max_len: int = 64600) -> np.ndarray:
    """
    Official AASIST variable-length input padding/truncation protocol.
    Repeats short chunks cyclically up to 64,600 samples; truncates longer audio.
    """
    x_len = x.shape[0]
    if x_len >= max_len:
        return x[:max_len]
    num_repeats = int(max_len / x_len) + 1
    padded_x = np.tile(x, num_repeats)[:max_len]
    return padded_x


def load_aasist_model(weights_path: str = None):
    """
    Instantiates the exact official AASIST-L model (85,306 trainable params)
    and loads official pretrained weights using strict=True.
    """
    if weights_path is None or not os.path.exists(weights_path):
        candidate_paths = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "weights", "AASIST-L.pth")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "weights", "AASIST-L.pth")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "weights", "AASIST-L.pth")),
            weights_path
        ]
        for p in candidate_paths:
            if p and os.path.exists(p):
                weights_path = p
                break

    if not weights_path or not os.path.exists(weights_path):
        raise FileNotFoundError(f"AASIST-L weights not found at: {weights_path}")

    d_args = {
        "architecture": "AASIST",
        "nb_samp": 64600,
        "first_conv": 128,
        "filts": [70, [1, 32], [32, 32], [32, 24], [24, 24]],
        "gat_dims": [24, 32],
        "pool_ratios": [0.4, 0.5, 0.7, 0.5],
        "temperatures": [2.0, 2.0, 100.0, 100.0]
    }

    model = Model(d_args)
    param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)

    state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
    cleaned_state = {k.replace("module.", "").replace("model.", ""): v for k, v in state_dict.items()}

    # Strict loading
    model.load_state_dict(cleaned_state, strict=True)
    model.eval()

    file_size = os.path.getsize(weights_path)
    return model, param_count, file_size
'''

with open(dst_file, "w", encoding="utf-8") as f:
    f.write(code + "\n" + extra)

print(f" Successfully wrote exact official AASIST-L source to {dst_file}")
