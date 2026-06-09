import json
from pathlib import Path

FEATURES_DIR = Path("data/features")


def save(company: str, stem: str, features: dict):
    folder = FEATURES_DIR / company
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stem}.features.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(features, f, indent=2, ensure_ascii=False)


def load_all(insurer_filter: str = None) -> list[dict]:
    results = []
    for path in FEATURES_DIR.rglob("*.features.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if insurer_filter:
            meta_company = data.get("_meta", {}).get("company", "")
            if insurer_filter.lower() not in meta_company.lower():
                continue
        results.append(data)
    return results


def load_one(company: str, stem: str) -> dict | None:
    path = FEATURES_DIR / company / f"{stem}.features.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def exists(company: str, stem: str) -> bool:
    return (FEATURES_DIR / company / f"{stem}.features.json").exists()


def list_all_paths() -> list[Path]:
    return list(FEATURES_DIR.rglob("*.features.json"))
