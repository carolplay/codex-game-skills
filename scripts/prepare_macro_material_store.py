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
        (store / 'README.md').write_text('''# WOS独立本地素材库

本目录可整体迁移到选定的私有存储；当前全部私有，没有上传。

- `private/assets.jsonl`：可迁移清单，文件路径相对于private目录；含SHA256、字节数和动作版本，不依赖技能仓库位置。
- `private/legacy-library/blobs/`：原图，未重编码、未复制、未删除。
- `private/legacy-library/index.json`及`actions/`：保留原始来源、历史证据与保留原因；其中旧仓库路径仅用于追溯。
- `public/`：公开样本候选区域，当前为空；未经脱敏检查的原图不得移入。
- `store.json`：本地整理结果，不代表已上传或已做公开脱敏。

运行截图和日志仍在原运行目录，兼容入口`local-data/macro-materials`指向这里，旧报告路径不变。当前保留策略见兼容入口README，72小时和全部日志保留规则未改变。本次整理不会释放原图占用的空间。

以后迁移时，先复制整个目录到目标私有存储，逐项验证assets.jsonl中的SHA256及字节数，再切换兼容入口；确认远端完整且可取回后，另行处理本地副本。不能直接删除运行目录中仍被报告引用的硬链接。公开样本、私有原图和必要运行模板分别管理；不将素材目录加入技能Git。
''')
        (store / 'public/README.md').write_text('''# 公开样本候选

当前无公开图片，也未上传。候选样本须裁剪并检查角色名、角色ID、联盟、聊天、坐标、余额及文件元数据。生成脱敏副本，原图保持私有；只发布与复现任务相关的少量样本，并附动作版本及校验值。大量样本使用独立素材存储，技能Git只维护索引或必要小型测试图。
''')
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, args.apply), ensure_ascii=False))
