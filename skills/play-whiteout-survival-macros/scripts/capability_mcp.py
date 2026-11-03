#!/usr/bin/env python3
"""Read-only WOS capability discovery. No device/backend imports or execution tools."""
import argparse
import json
import sys
from pathlib import Path
from macro_package import ROOT, digest, load_actions, load_manifest, read

VERSION = '0.1.0'
PROTOCOL = '2025-03-26'
EMPTY = {'type': 'object', 'properties': {}, 'additionalProperties': False}
TOOLS = [
    {'name': 'wos_capabilities', 'description': 'Validate package hashes and list declared WOS actions; no device access.', 'inputSchema': EMPTY},
    {'name': 'wos_shift_plan', 'description': 'Validate a public shift/profile plan. This is not evidence of execution or native acceptance.',
     'inputSchema': {'type': 'object', 'properties': {'shift': {'type': 'integer', 'enum': [1, 2, 3]}, 'profile': {'type': 'string', 'enum': ['main', 'mature-test', 'under30-test']}}, 'required': ['shift', 'profile'], 'additionalProperties': False}},
]
for tool in TOOLS:
    tool['annotations'] = {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}


class Discovery:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()

    @staticmethod
    def acceptance():
        return {'device_access': False, 'execution_tools_available': False,
                'native_wos_acceptance': 'pending',
                'note': 'Declarations and historical verification notes are not a native runtime acceptance certificate.'}

    def call(self, name, arguments):
        if not isinstance(arguments, dict):
            raise ValueError('arguments must be an object')
        if name == 'wos_capabilities':
            if arguments:
                raise ValueError('This tool accepts no arguments')
            catalog, flows = load_actions(self.root)
            actions = []
            for task, item in catalog['actions'].items():
                flow = flows[task]
                actions.append({'task': task, 'action_id': item['action_id'],
                                'action_version': item['action_version'], 'sha256': item['sha256'],
                                'period': item.get('period'), 'utility': item.get('utility', False),
                                'name': flow.get('name'),
                                'declared_verification_scope': item.get('verification_scope', '')})
            return {'package_version': catalog['package_version'], 'catalog_sha256': digest(catalog),
                    'executor_min_version': catalog['executor_min_version'], 'actions': actions,
                    'acceptance': self.acceptance()}
        if name == 'wos_shift_plan':
            if set(arguments) != {'shift', 'profile'}:
                raise ValueError('Exactly shift and profile are required')
            shift, profile = arguments['shift'], arguments['profile']
            if type(shift) is not int or shift not in (1, 2, 3):
                raise ValueError('shift must be 1, 2 or 3')
            if profile not in ('main', 'mature-test', 'under30-test'):
                raise ValueError('Unknown public profile')
            path = self.root / 'macros' / f'shift-{shift}.json'
            tasks, identity = load_manifest(path, profile, self.root)
            manifest = read(path)
            return {'identity': identity, 'shift': shift,
                    'actions': manifest['profiles'][profile]['actions'],
                    'excluded': manifest['profiles'][profile]['excluded'],
                    'dependencies': manifest.get('dependencies', {}),
                    'action_count': len(tasks), 'acceptance': self.acceptance()}
        raise ValueError('Unknown tool; execution is not exposed')


def error(rid, code, message):
    return {'jsonrpc': '2.0', 'id': rid, 'error': {'code': code, 'message': message}}


class Server:
    def __init__(self, discovery):
        self.discovery = discovery
        self.initialized = False
        self.ready = False

    def handle(self, message):
        if isinstance(message, list):
            if not message or any(isinstance(m, dict) and m.get('method') == 'initialize' for m in message):
                return error(None, -32600, 'Invalid batch')
            replies = [self.handle(m) for m in message]
            return [r for r in replies if r is not None] or None
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0' or not isinstance(message.get('method'), str):
            return error(None, -32600, 'Invalid request')
        rid, method = message.get('id'), message['method']
        notification = 'id' not in message
        if notification:
            if method == 'notifications/initialized' and self.initialized:
                self.ready = True
            return None
        params = message.get('params', {})
        if not isinstance(params, dict):
            return error(rid, -32602, 'params must be an object')
        if method == 'initialize':
            if self.initialized:
                return error(rid, -32600, 'Already initialized')
            if not isinstance(params.get('protocolVersion'), str) or not isinstance(params.get('clientInfo'), dict) or not isinstance(params.get('capabilities'), dict):
                return error(rid, -32602, 'Initialization fields missing')
            self.initialized = True
            result = {'protocolVersion': PROTOCOL, 'capabilities': {'tools': {'listChanged': False}},
                      'serverInfo': {'name': 'wos-readonly-capabilities', 'version': VERSION},
                      'instructions': 'Offline discovery only. No role identities, device access, execution, or production migration.'}
        elif method == 'ping':
            result = {}
        elif not self.ready:
            return error(rid, -32002, 'Initialize and send notifications/initialized first')
        elif method == 'tools/list':
            if params:
                return error(rid, -32602, 'No pagination cursor or other parameters supported')
            result = {'tools': TOOLS}
        elif method == 'tools/call':
            if set(params) - {'name', 'arguments'} or not isinstance(params.get('name'), str):
                return error(rid, -32602, 'Invalid tool call')
            try:
                data = self.discovery.call(params['name'], params.get('arguments', {}))
                result = {'content': [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False)}], 'isError': False}
            except (ValueError, KeyError, OSError, TypeError):
                # Do not expose machine paths or arbitrary private file contents in errors.
                result = {'content': [{'type': 'text', 'text': 'Invalid arguments or package validation failed; no device operation performed.'}], 'isError': True}
        else:
            return error(rid, -32601, 'Method not found')
        return {'jsonrpc': '2.0', 'id': rid, 'result': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Owner-configured public capability package; not a tool argument')
    args = parser.parse_args()
    server = Server(Discovery(args.root))
    for line in sys.stdin:
        try:
            reply = server.handle(json.loads(line))
        except (ValueError, TypeError):
            reply = error(None, -32700, 'Parse error')
        if reply is not None:
            print(json.dumps(reply, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
