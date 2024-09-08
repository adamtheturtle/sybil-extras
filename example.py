#!/usr/bin/env python3

"""Example."""

from __future__ import annotations

import argparse
import base64
import io
import json
import os.path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

_VERSION = "v1.0.2"

_GIT = (
    "git",
    "-c",
    "user.name=does-not-matter",
    "-c",
    "user.email=does-not-matter@example.com",
    "-c",
    "protocol.version=2",
)


def _has_changes(*, src_repo: str) -> bool:
    """Example."""
    cmd = (
        *_GIT,
        "-C",
        src_repo,
        "diff-index",
        "--quiet",
        "--no-ext-diff",
        "HEAD",
        "--",
    )
    return subprocess.call(cmd) == 1


def _rev_parse(*, repo: str, ref: str) -> str:
    """Example."""
    cmd = (*_GIT, "-C", repo, "rev-parse", ref)
    return subprocess.check_output(cmd).strip().decode()


def _fetch_pr(*, src_repo: str, pr: int) -> str:
    """Example."""
    subprocess.check_call(
        (
            *_GIT,
            "-C",
            src_repo,
            "fetch",
            "--quiet",
            "--depth=1",
            "origin",
            f"+refs/pull/{pr}/head",
        )
    )
    return _rev_parse(repo=src_repo, ref="FETCH_HEAD")


def _make_commit(*, src_repo: str, head: str, clone: str) -> str:
    """Example."""
    os.makedirs(clone, exist_ok=True)

    # ~essentially make a work tree and commit what's currently modified
    git_dir = os.path.join(clone, ".git")
    shutil.copytree(os.path.join(src_repo, ".git"), git_dir)

    subprocess.check_call(
        (
            *_GIT,
            "-C",
            src_repo,
            "commit",
            "--all",
            "--quiet",
            "--no-edit",
            "--no-verify",
            "--message=hi",
        ),
        env={**os.environ, "GIT_DIR": os.path.join(clone, ".git")},
    )
    commit = _rev_parse(repo=clone, ref="HEAD")

    # need to clean out deletes
    subprocess.check_call((*_GIT, "-C", clone, "checkout", "--", "."))
    subprocess.check_call((*_GIT, "-C", clone, "clean", "-qfxfd"))

    subprocess.check_call((*_GIT, "-C", clone, "checkout", head, "--quiet"))
    cmd = (*_GIT, "-C", clone, "cherry-pick", "--quiet", "--no-edit", commit)
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
    return _rev_parse(repo=clone, ref="HEAD")


def _changed_files(*, repo: str, commit: str) -> list[str]:
    """Example."""
    out = subprocess.check_output(
        (
            *_GIT,
            "-C",
            repo,
            "show",
            "--name-only",
            "-z",
            "--no-renames",
            "--format=",
            commit,
        )
    )
    if not out:
        return []
    return out.rstrip(b"\0").decode().split("\0")


class Index(NamedTuple):
    """Example."""

    mode: str
    path: str
    oid: str


class Object(NamedTuple):
    """Example."""

    oid: str
    tp: str
    data: bytes

    def as_index(self) -> list[Index]:
        """Example."""
        ret: list[Index] = []

        bts = self.data
        while True:
            try:
                pt1, bts = bts.split(b"\0", 1)
            except ValueError:
                break
            else:
                mode, _, path = pt1.decode().partition(" ")
                oid_bts, bts = bts[:20], bts[20:]

                ret.append(Index(mode=mode, path=path, oid=oid_bts.hex()))

        return ret


def _read_obj(bio: io.BytesIO) -> Object | None:
    """Example."""
    line = bio.readline().strip().decode()
    if line.endswith(" missing"):
        return None

    oid, tp, sz = line.split()
    data = bio.read(int(sz))
    bio.read(1)  # discard newline
    return Object(oid=oid, tp=tp, data=data)


def _query_objects(
    *,
    repo: str,
    objects: Sequence[str],
) -> dict[str, Object | None]:
    """Example."""
    stdin = ("\n".join(objects) + "\n").encode()
    res = subprocess.run(
        (*_GIT, "-C", repo, "cat-file", "--batch"),
        input=stdin,
        stdout=subprocess.PIPE,
        check=True,
    )
    bio = io.BytesIO(res.stdout)
    return {obj: _read_obj(bio) for obj in objects}


def _structure_for(
    *,
    repo: str,
    ref: str,
    files: Iterable[str],
) -> dict[str, dict[str, Index]]:
    """Example."""
    trees = tuple({f"{ref}:{os.path.dirname(f)}" for f in files})
    objs = _query_objects(repo=repo, objects=trees)
    return {
        k.partition(":")[2]: {idx.path: idx for idx in v.as_index()}
        for k, v in objs.items()
        if v is not None
    }


def _get_data(
    *,
    msg: str,
    clone: str,
    head: str,
    commit: str,
) -> dict[str, Any]:
    """Example."""
    files = _changed_files(repo=clone, commit=commit)

    dir_structure = _structure_for(repo=clone, ref=commit, files=files)
    deletes: list[str] = []
    entries: list[tuple[str, Index]] = []
    for filename in files:
        dirname, basename = os.path.split(filename)
        try:
            entries.append((filename, dir_structure[dirname][basename]))
        except KeyError:
            deletes.append(filename)

    binary: list[tuple[str, str, str]] = []
    text: list[tuple[str, str, str]] = []
    file_oids = [idx.oid for _, idx in entries]
    file_objects = _query_objects(repo=clone, objects=file_oids)
    for (filename, entry), obj in zip(
        entries, file_objects.values(), strict=False
    ):
        assert obj is not None
        try:
            contents = obj.data.decode()
        except UnicodeDecodeError:
            b64: str = base64.b64encode(obj.data).decode()
            binary.append((filename, entry.mode, b64))
        else:
            text.append((filename, entry.mode, contents))

    return {
        "action_version": _VERSION,
        "msg": msg,
        "base_tree": _rev_parse(repo=clone, ref=f"{head}:"),
        "delete": deletes,
        "binary": binary,
        "text": text,
    }


def _save_artifact(
    data: dict[str, Any],
    run_id: int,
    url: str,
    token: str,
) -> None:
    """Example."""
    contents = json.dumps(data, separators=(",", ":")).encode()

    artifact_name = f"pre-commit-ci-lite-{run_id}"

    headers = {
        "Accept": "application/json;api-version=6.0-preview",
        "Authorization": f"Bearer {token}",
    }

    base_url = f"{url}_apis/pipelines/workflows/{run_id}/artifacts?api-version=6.0-preview"  # noqa: E501

    req_create = urllib.request.Request(
        base_url,
        method="POST",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps(
            {
                "type": "actions_storage",
                "name": artifact_name,
                "retentionDays": 1,
            }
        ).encode(),
    )
    resp_create = json.load(urllib.request.urlopen(req_create))

    req_upload = urllib.request.Request(
        f'{resp_create["fileContainerResourceUrl"]}?itemPath={artifact_name}/data.json',
        method="PUT",
        headers={
            **headers,
            "Content-Type": "application/octet-stream",
            "Content-Range": f"bytes 0-{len(contents) - 1}/{len(contents)}",
        },
        data=contents,
    )
    urllib.request.urlopen(req_upload)

    req_finish = urllib.request.Request(
        f"{base_url}&artifactName={artifact_name}",
        method="PATCH",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps({"size": len(contents)}).encode(),
    )
    urllib.request.urlopen(req_finish)


def main(argv: Sequence[str] | None = None) -> int:
    """Example."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--src-repo", default=".")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--msg", required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--runtime-token", required=True)
    parser.add_argument("--runtime-url", required=True)
    args = parser.parse_args(argv)

    if not _has_changes(src_repo=args.src_repo):
        sys.stdout.write("nothing to do: no changes!")
        return 0

    sys.stdout.write("fetching pr...")
    head = _fetch_pr(src_repo=args.src_repo, pr=args.pr)

    with tempfile.TemporaryDirectory() as clone:
        commit = _make_commit(src_repo=args.src_repo, head=head, clone=clone)

        data = _get_data(
            msg=args.msg,
            clone=clone,
            head=head,
            commit=commit,
        )

    if args.dry_run:
        sys.stdout.write("would create artifact with data:")
        sys.stdout.write(json.dumps(data, indent=2))
    else:
        sys.stdout.write("saving artifact...")
        _save_artifact(
            data=data,
            run_id=args.run_id,
            url=args.runtime_url,
            token=args.runtime_token,
        )
        with Path(os.environ["GITHUB_ENV"]).open(mode="a+") as f:
            f.write("PRE_COMMIT_CI_LITE_ARTIFACT=true\n")
        sys.stdout.write("artifact published!")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
