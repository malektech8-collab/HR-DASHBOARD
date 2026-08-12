"""Upload staging (Phase 2 P0-2).

A staged file is INERT. It has been received and nothing else has happened to
it: no validation has been applied, no types inferred, no table replaced, and
crucially no pipeline run will pick it up.

That last property is why staging is its own directory and not one of the
existing ones:

  data/silver/   is what dbt reads. A file there is SERVED.
  data/raw/      is the real-mode resolver's input. A file there is INGESTED on
                 the next run.
  data/staging/  is read by nothing but the upload endpoints.

Before this, upload wrote a compiled parquet straight into data/silver, so a
file was served the moment it arrived - having passed no contract check, no
derivation, and no declaration. Every safeguard built since cycle 1b-i applied
to the other path.

Layout, one directory per upload:

    data/staging/<uuid>/
        data.csv          the bytes exactly as received
        manifest.json     table, original filename, size, sha256, timestamps

The manifest is what makes an upload reviewable between arriving and being
committed - which file, for which domain, and whether the bytes changed.
"""
import datetime
import hashlib
import json
import os
import shutil
import uuid

STAGING_DIR = os.path.join("data", "staging")
CONTAINER_STAGING_DIR = "/app/data/staging"

DATA_FILENAME = "data.csv"
# The canonical form, produced by applying a mapping profile. The
# original is never modified, so a re-map costs no re-upload and the
# client can always be shown their own headers.
MAPPED_FILENAME = "mapped.csv"
MANIFEST_FILENAME = "manifest.json"


class StagingError(RuntimeError):
    """The staged upload is missing, unreadable, or not what was claimed."""


def staging_root():
    if os.path.isdir(os.path.dirname(CONTAINER_STAGING_DIR)):
        return CONTAINER_STAGING_DIR
    return STAGING_DIR


def _upload_dir(upload_id):
    """Resolve an id to its directory, refusing anything that escapes the root.

    The id comes from a URL. `..%2f..%2fsilver` would otherwise be a path.
    """
    root = os.path.abspath(staging_root())
    resolved = os.path.abspath(os.path.join(root, str(upload_id)))
    if os.path.commonpath([root, resolved]) != root or resolved == root:
        raise StagingError("invalid upload id")
    return resolved


def stage(table, filename, stream):
    """Write received bytes to a new staging directory. Validates nothing."""
    upload_id = str(uuid.uuid4())
    directory = _upload_dir(upload_id)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, DATA_FILENAME)
    with open(path, "wb") as handle:
        shutil.copyfileobj(stream, handle)

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    manifest = {
        "upload_id": upload_id,
        "table": table,
        "original_filename": os.path.basename(filename or ""),
        "size_bytes": os.path.getsize(path),
        "sha256": digest.hexdigest(),
        "staged_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "committed_at": None,
    }
    with open(os.path.join(directory, MANIFEST_FILENAME), "w",
              encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest


def load(upload_id):
    directory = _upload_dir(upload_id)
    path = os.path.join(directory, MANIFEST_FILENAME)
    if not os.path.exists(path):
        raise StagingError("no staged upload '{}'".format(upload_id))
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def data_path(upload_id):
    path = os.path.join(_upload_dir(upload_id), DATA_FILENAME)
    if not os.path.exists(path):
        raise StagingError("staged upload '{}' has no data file".format(upload_id))
    return path


def mapped_path(upload_id):
    return os.path.join(_upload_dir(upload_id), MAPPED_FILENAME)


def mark_committed(upload_id):
    manifest = load(upload_id)
    manifest["committed_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(os.path.join(_upload_dir(upload_id), MANIFEST_FILENAME), "w",
              encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest


def discard(upload_id):
    """Staging is disposable by construction - nothing downstream reads it."""
    directory = _upload_dir(upload_id)
    if os.path.isdir(directory):
        shutil.rmtree(directory)
        return True
    return False


def listing():
    root = staging_root()
    if not os.path.isdir(root):
        return []
    found = []
    for name in sorted(os.listdir(root)):
        try:
            found.append(load(name))
        except StagingError:
            continue
    return found
