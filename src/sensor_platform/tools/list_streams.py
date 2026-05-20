"""List registered MQTT/protobuf streams."""

from __future__ import annotations

import argparse

from sensor_platform.streams import STREAMS


def build_parser() -> argparse.ArgumentParser:
    """Define command-line options for stream registry inspection."""
    parser = argparse.ArgumentParser(description="List registered sensor platform streams.")
    parser.add_argument(
        "--visible-only",
        action="store_true",
        help="Only show streams enabled for monitors by default.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    streams = [stream for stream in STREAMS if stream.default_visible] if args.visible_only else STREAMS

    for index, stream in enumerate(streams):
        if index:
            print()
        print(stream.name)
        print(f"  display: {stream.display_name}")
        print(f"  topic: {stream.topic}")
        print(f"  kind: {stream.kind.value}")
        print(f"  default_visible: {str(stream.default_visible).lower()}")


if __name__ == "__main__":
    main()
