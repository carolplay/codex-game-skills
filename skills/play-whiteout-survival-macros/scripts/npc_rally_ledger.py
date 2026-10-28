"""Offline polar-terror quota accounting. No UI, model, or execution imports.

Events are supplied by an evidence-producing caller. This module checks their
meaning and daily scope; it cannot authenticate screenshots or certify a run.
"""
from datetime import datetime, timezone

LEDGER_VERSION = "0.1.1"


def utc_day(timestamp):
    value = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('Evidence timestamp must include a timezone')
    return value.astimezone(timezone.utc).date().isoformat()


def summarize(events, *, day, role, target=10):
    if not isinstance(target, int) or isinstance(target, bool) or target <= 0:
        raise ValueError('Target must be a positive integer')
    starts, victories, seen, rejected = {}, {}, set(), []
    for event in events:
        event_id = event.get('event_id')
        reason = None
        if not event_id or not event.get('evidence'):
            reason = 'missing_id_or_evidence'
        elif event.get('role') != role or utc_day(event['observed_at']) != day:
            reason = 'different_role_or_utc_day'
        elif event.get('activity') != 'polar_terror':
            reason = 'different_activity'
        elif event_id in seen:
            reason = 'duplicate'
        elif event.get('kind') == 'initiated':
            if event.get('actual_dispatch_verified') is not True:
                reason = 'dispatch_not_verified'
            else:
                starts[event_id] = event
        elif event.get('kind') == 'victory':
            if event.get('own_initiator_verified') is not True or event.get('victory_verified') is not True:
                reason = 'not_verified_own_initiator_victory'
            else:
                victories[event_id] = event
        else:
            reason = 'not_a_start_or_victory'
        if reason:
            rejected.append({'event_id': event_id, 'reason': reason})
        else:
            seen.add(event_id)
    settled = {e['start_event_id'] for e in victories.values() if e.get('start_event_id')}
    pending = [key for key in starts if key not in settled]
    return {'ledger_version': LEDGER_VERSION, 'day': day, 'role': role, 'target': target,
            'actual_starts': len(starts), 'confirmed_own_victories': len(victories),
            'pending_start_ids': pending, 'remaining_victories': max(0, target - len(victories)),
            'quota_completed': len(victories) >= target, 'rejected_events': rejected,
            'verification_boundary': 'Caller evidence flags are not screenshot authentication.'}


def events_from_report_list(ocr, *, own_name, role, local_timezone, evidence, own_tag=None):
    """Extract explicit own-initiator victories from a saved report-list OCR.

    The caller supplies the verified current role name and UI timezone. Target
    and local report time form a stable key across repeated screenshots. This
    only recognizes the sampled Sabertooth/Dragon Turtle labels. It does not
    claim a reward quantity or link a victory to a particular dispatch.
    """
    import hashlib
    import re
    import unicodedata
    from zoneinfo import ZoneInfo

    def compact(text):
        return ''.join(unicodedata.normalize('NFKC', text).split())

    name = compact(own_name)
    if not name or not evidence:
        raise ValueError('Verified own name and saved evidence are required')
    lines = [compact(line['text']) for line in ocr['lines']]
    prefix = r'(?:\[[^\]]+\])?'
    if own_tag:
        # Tolerate only sampled closing-bracket OCR glyphs after the exact
        # caller-verified guild tag; do not turn a partial player name into an owner.
        prefix = r'(?:\[' + re.escape(compact(own_tag)) + r'(?:\]|J|I|1)?)?'
    pattern = re.compile(prefix + re.escape(name) + r'集结攻击(\d+级(?:剑齿虎|深渊龙龟))获胜')
    zone = ZoneInfo(local_timezone)
    events = []
    for i, line in enumerate(lines):
        match = pattern.fullmatch(line)
        if not match:
            continue
        # Report rows may put a date on a separate line. Stop at another row.
        stamp = None
        for following in lines[i+1:i+3]:
            if '集结攻击' in following or '大获全胜' in following:
                break
            date = re.search(r'(\d{4}-\d{2}-\d{2})[T ]?(\d{2}:\d{2}:\d{2})', following)
            if date:
                stamp = datetime.fromisoformat(date[1] + 'T' + date[2]).replace(tzinfo=zone)
                break
        if stamp is None:
            continue
        observed = stamp.astimezone(timezone.utc).isoformat()
        target = match[1]
        key = hashlib.sha256((role + '\n' + target + '\n' + observed).encode()).hexdigest()[:24]
        events.append({'event_id': 'report-' + key, 'role': role,
                       'activity': 'polar_terror', 'kind': 'victory',
                       'observed_at': observed, 'target': target,
                       'own_initiator_verified': True, 'victory_verified': True,
                       'evidence': evidence, 'source': 'explicit_own_report_list_row'})
    return events
