#!/usr/bin/env python3
"""Separate a private material library without copying images or breaking old links."""
import argparse
import collections
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]


def write_portable_manifest(library, index, destination, verify_content=False):
    """Paths in this manifest are relative to its parent, never the skill repo."""
    groups = collections.defaultdict(list)
    for sample in index['samples'].values():
        digest = sample['sha256']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid material digest')
        blob = Path(sample['blob'])
        # Legacy indexes use repo-relative paths. Only their validated blob suffix
        # is used for the portable store; arbitrary source paths are never followed.
        parts = blob.parts
        if len(parts) < 3 or parts[-3] != 'blobs' or parts[-2] != digest[:2]:
            raise ValueError('Unexpected material blob path')
        if Path(parts[-1]).stem != digest or Path(parts[-1]).suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
            raise ValueError('Unexpected material blob filename')
        groups[Path(*parts[-3:])].append(sample)
    temporary = destination.with_name(destination.name + '.new')
    total_bytes = 0
    try:
        with temporary.open('w') as out:
            for relative, samples in sorted(groups.items()):
                blob = library / relative
                if blob.is_symlink() or not blob.is_file():
                    raise ValueError('Missing or symlinked material blob: ' + str(relative))
                blob.resolve().relative_to(library.resolve())
                size = blob.stat().st_size
                if verify_content:
                    digest = hashlib.sha256()
                    with blob.open('rb') as source:
                        for chunk in iter(lambda: source.read(1024 * 1024), b''):
                            digest.update(chunk)
                    if digest.hexdigest() != samples[0]['sha256']:
                        raise ValueError('Material content mismatch: ' + str(relative))
                versions = sorted({str((s.get('workflow') or {}).get('action_id') or 'unclassified') + '@' +
                                   str((s.get('workflow') or {}).get('action_version') or 'unknown') for s in samples})
                row = dict(sha256=samples[0]['sha256'], file='legacy-library/' + relative.as_posix(),
                           bytes=size, references=len(samples), action_versions=versions,
                           privacy='private_unreviewed')
                out.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
                total_bytes += size
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return dict(blob_files=len(groups), sample_references=len(index['samples']),
                blob_logical_bytes=total_bytes, content_verified=verify_content)


def prepare(root, apply=False):
    root = Path(root).resolve()
    alias = root / 'local-data/macro-materials'
    store = root / 'local-data/material-store/wos'
    library = store / 'private/legacy-library'
    lock_path = root / 'local-data/crossmacro/v2/visit.lock'
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return dict(status='skipped_active_executor', input_sent=False)
        already = alias.is_symlink()
        if already and alias.resolve() != library.resolve():
            raise ValueError('Existing material alias points elsewhere')
        if not already and library.exists():
            raise ValueError('Destination already exists; source untouched')
        source = library if already else alias
        if not source.is_dir():
            raise ValueError('Material source missing')
        index = json.loads((source / 'index.json').read_text())
        if not apply:
            return dict(status='planned', sample_references=len(index['samples']),
                        destination=str(store), copies_images=False, deletes_images=False)
        (store / 'private').mkdir(parents=True, exist_ok=True)
        (store / 'public').mkdir(exist_ok=True)
        # Validate every indexed blob before changing the directory entry. The
        # manifest is small; all image bytes and existing hard links stay in place.
        stats = write_portable_manifest(source, index, store / 'private/assets.jsonl', True)
        if not already:
            source.rename(library)
            try:
                alias.symlink_to(os.path.relpath(library, alias.parent), target_is_directory=True)
            except Exception:
                library.rename(source)
                raise
        report = dict(schema_version=1, status='completed', **stats,
                      compatibility_alias='local-data/macro-materials',
                      private_manifest='private/assets.jsonl', public_assets=0,
                      raw_data_public=False, images_copied=0, images_deleted=0,
                      old_report_links_preserved=True, input_sent=False,
                      retention_policy_changed=False, updated_unix=time.time())
        (store / 'store.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        if not (store / 'README.md').exists():
            (store / 'README.md').write_text('# WOS reusable materials\n\nFollow local-data/macro-materials/README.md for the current consumer whitelist. Migration never expands retention.\n')
        (store / 'public/README.md').write_text('''# 公开样本候选

当前无公开图片，也未上传。候选样本须裁剪并检查角色名、角色ID、联盟、聊天、坐标、余额及文件元数据。生成脱敏副本，原图保持私有；只发布与复现任务相关的少量样本，并附动作版本及校验值。只保留明确消费者需要的模板或测试图，不再归档大量运行图片。
''')
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, args.apply), ensure_ascii=False))
