from __future__ import annotations

from pathlib import Path

from grpc_tools import protoc


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROTO_DIR = PROJECT_ROOT / "proto"
OUTPUT_DIR = PROJECT_ROOT / "src" / "sensor_platform" / "generated"
PROTO_FILE = PROTO_DIR / "sensor_platform.proto"


def main() -> None:
    """Generate Python protobuf code from the project schema."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    init_file = OUTPUT_DIR / "__init__.py"
    init_file.touch(exist_ok=True)

    result = protoc.main(
        [
            "grpc_tools.protoc",
            f"--proto_path={PROTO_DIR}",
            f"--python_out={OUTPUT_DIR}",
            str(PROTO_FILE),
        ]
    )
    if result != 0:
        raise SystemExit(result)

    print(f"Generated protobuf Python code in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
