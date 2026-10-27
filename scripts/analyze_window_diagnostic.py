"""Interpret read-only macos_window_metadata.swift output; never recover or input.

Missing session keys are unknown. A process being alive, a screenshot, or a
visible AX tree alone cannot establish that the host can route input.
"""
import argparse
import json
from pathlib import Path


def contains(bounds, point):
    x, y = point
    return (bounds['x'] <= x < bounds['x'] + bounds['w']
            and bounds['y'] <= y < bounds['y'] + bounds['h'])


def analyze(snapshot, failed_point=None, previous=None):
    findings = []
    session = snapshot.get('session')
    locked = session.get('CGSSessionScreenIsLocked') if isinstance(session, dict) else None
    if locked is True:
        findings.append('session_reports_locked')
    if session is None:
        findings.append('session_query_unavailable')
    if not snapshot.get('targetApps'):
        findings.append('target_process_not_listed')
    windows = snapshot.get('targetWindowsAll')
    onscreen = snapshot.get('targetWindowsOnScreen')
    if windows is None or onscreen is None:
        findings.append('window_query_unavailable')
    elif not windows:
        findings.append('no_target_window_in_query')
    elif not onscreen:
        findings.append('target_windows_exist_but_none_onscreen')
    displays = snapshot.get('displays', [])
    if failed_point is not None:
        if snapshot.get('activeDisplayQueryError') != 0:
            findings.append('display_query_unavailable_for_failed_point')
        elif not any(contains(d['bounds'], failed_point) for d in displays):
            findings.append('failed_point_outside_current_displays')
    def topology(d):
        return sorted((x['id'], tuple(x['bounds'][k] for k in ('x', 'y', 'w', 'h')))
                      for x in d.get('displays', []))
    if previous is not None and topology(previous) != topology(snapshot):
        findings.append('display_topology_changed_between_snapshots')
    sizes = sorted({(w['kCGWindowBounds']['Width'], w['kCGWindowBounds']['Height'])
                    for w in onscreen or [] if w.get('kCGWindowLayer') == 0
                    and w['kCGWindowBounds']['Height'] > 100})
    return dict(findings=findings, lock_state=locked,
                onscreen_content_sizes=sizes, input_authorized=None,
                note='Diagnostic evidence only; no automatic retry, unlock, resize or input.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--failed-point', nargs=2, type=float)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(json.loads(args.snapshot.read_text()), args.failed_point,
                            json.loads(args.previous.read_text()) if args.previous else None),
                     ensure_ascii=False, indent=2))
