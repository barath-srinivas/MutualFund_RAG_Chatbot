"""CLI entrypoint: python -m src.ingest --manifest corpus/urls.yaml"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.config.settings import get_settings
from src.ingest.pipeline import format_dry_run_summary, run_ingest
from src.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Ingest official AMC/AMFI/SEBI corpus into Chroma.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=settings.corpus_urls_path,
        help="Path to corpus urls.yaml manifest",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse only; report chunk counts per scheme (no embed/store)",
    )
    parser.add_argument(
        "--no-save-raw",
        action="store_true",
        help="Do not write fetched bytes under corpus/raw/",
    )
    parser.add_argument(
        "--source-id",
        action="append",
        dest="source_ids",
        metavar="ID",
        help="Process only the given manifest source id (repeatable)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-index even when content hash is unchanged (e.g. after chunker updates)",
    )
    parser.add_argument(
        "--log-level",
        default=settings.log_level,
        help="Logging level (default from env)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        report = run_ingest(
            manifest_path=args.manifest,
            dry_run=args.dry_run,
            save_raw=not args.no_save_raw,
            source_ids=args.source_ids,
            force=args.force,
        )
    except Exception as exc:
        logger.exception("Ingest failed: %s", exc)
        return 1

    if args.dry_run:
        print(format_dry_run_summary(report))
    else:
        print(
            f"Ingest complete: {report.total_chunks} chunks indexed, "
            f"{report.sources_skipped} skipped (unchanged), "
            f"{report.sources_failed} failed."
        )
        print(f"Run manifest: corpus/manifests/{report.run_id}.json")

    return 1 if report.sources_failed else 0


if __name__ == "__main__":
    sys.exit(main())
