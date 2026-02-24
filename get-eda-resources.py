#!/usr/bin/env -S uv run --with pyyaml python
import argparse
import json
import os
import subprocess
import tarfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml


def run_kubectl(args: list[str]) -> dict:
    result = subprocess.run(
        ["kubectl", *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return json.loads(result.stdout)


def get_eda_crd_resources(group_suffix: str) -> list[str]:
    crds = run_kubectl(["get", "crd", "-o", "json"])
    resources: list[str] = []
    for crd in crds.get("items", []):
        spec = crd.get("spec", {})
        group = spec.get("group")
        if not group or not group.endswith(group_suffix):
            continue
        plural = spec.get("names", {}).get("plural")
        if plural:
            resources.append(f"{plural}.{group}")
    return resources


def write_resources(
    resource: str, namespace: str, out_dir: Path, set_namespace: str | None, split: bool = False
) -> None:
    data = run_kubectl(["get", resource, "-n", namespace, "-o", "json"])
    items = data.get("items", [])
    if not items:
        return

    plural = resource.split(".", 1)[0]
    group = resource.split(".", 1)[1]
    suffix = group.replace("eda.", "", 1)

    filtered_items = []
    for item in items:
        metadata = item.get("metadata") or {}
        labels = metadata.get("labels") or {}
        if labels.get("eda.nokia.com/source") == "derived":
            continue
        item.pop("status", None)
        filtered_metadata = {
            "name": metadata.get("name"),
            "namespace": set_namespace or metadata.get("namespace"),
        }
        if labels:
            filtered_metadata["labels"] = labels
        annotations = metadata.get("annotations")
        if annotations:
            filtered_metadata["annotations"] = annotations
        item["metadata"] = filtered_metadata
        filtered_items.append(item)

    if not filtered_items:
        return

    if split:
        kind_dir = out_dir / f"{plural}.{suffix}"
        kind_dir.mkdir(parents=True, exist_ok=True)
        for item in filtered_items:
            cr_name = item["metadata"]["name"]
            output = kind_dir / f"{cr_name}.yaml"
            with output.open("w", encoding="utf-8") as handle:
                yaml.safe_dump(item, handle, sort_keys=False)
            print(f"Wrote {output}")
    else:
        output = out_dir / f"{plural}.{suffix}.yaml"
        with output.open("w", encoding="utf-8") as handle:
            for index, item in enumerate(filtered_items):
                if index:
                    handle.write("---\n")
                yaml.safe_dump(item, handle, sort_keys=False)
        print(f"Wrote {output}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export eda.nokia.com resources by kind from a namespace",
    )
    parser.add_argument("--namespace", default="eda", help="Kubernetes namespace")
    parser.add_argument("--out-dir", default="eda-resources", help="Output folder")
    parser.add_argument(
        "--set-namespace",
        help="Rewrite resource namespaces to this value",
    )
    parser.add_argument(
        "--group",
        default="eda.nokia.com",
        help="CRD group suffix (matches *.group)",
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Create a tar.gz archive of exported resources",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Write one file per CR (named <cr-name>.yaml) under a folder per group",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir) / args.namespace
    out_dir.mkdir(parents=True, exist_ok=True)

    resources = get_eda_crd_resources(args.group)
    if not resources:
        print(f"No CRDs found for group {args.group}.")
        return 0

    max_workers = os.cpu_count() or 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(
            executor.map(
                lambda r: write_resources(
                    r, args.namespace, out_dir, args.set_namespace, args.split
                ),
                resources,
            )
        )

    if args.archive:
        if any(out_dir.iterdir()):
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            archive_name = f"{args.namespace}-{timestamp}.tar.gz"
            archive_path = Path(args.out_dir) / archive_name
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(out_dir, arcname=args.namespace)
            print(f"Created archive {archive_path}")
        else:
            print(f"No resources written to {out_dir}. Skipping archive.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
