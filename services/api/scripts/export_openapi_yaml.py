from pathlib import Path

import yaml

from app.main import app


def main() -> None:
    spec = app.openapi()
    out = Path(__file__).resolve().parents[1] / "openapi.yaml"
    out.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
