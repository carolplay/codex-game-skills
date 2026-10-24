import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from capability_mcp import Discovery, Server, ROOT, PROTOCOL


class DiscoveryTests(unittest.TestCase):
    def test_every_public_profile_plan_validates_and_excludes_upgrades(self):
        d = Discovery()
        caps = d.call('wos_capabilities', {})
        self.assertFalse(caps['acceptance']['execution_tools_available'])
        for shift in (1, 2, 3):
            for profile in ('main', 'mature-test', 'under30-test'):
                p = d.call('wos_shift_plan', {'shift': shift, 'profile': profile})
                tasks = [a['task'] for a in p['actions']]
                self.assertEqual(tasks[-1], 'daily')
                self.assertNotIn('construction', tasks)
                self.assertNotIn('research', tasks)
                self.assertEqual(p['action_count'], len(tasks))

    def test_tampered_action_cannot_be_discovered_or_planned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'package'
            shutil.copytree(ROOT, root)
            catalog = json.loads((root / 'catalog.json').read_text())
            action = root / next(iter(catalog['actions'].values()))['path']
            flow = json.loads(action.read_text()); flow['name'] = 'tampered'
            action.write_text(json.dumps(flow))
            for name, args in [('wos_capabilities', {}), ('wos_shift_plan', {'shift': 2, 'profile': 'main'})]:
                with self.assertRaises(ValueError):
                    Discovery(root).call(name, args)

    def test_arguments_cannot_inject_paths_execution_or_private_roles(self):
        d = Discovery()
        for name, args in [('execute', {}), ('wos_capabilities', {'root': '/tmp'}),
                           ('wos_shift_plan', {'shift': True, 'profile': 'main'}),
                           ('wos_shift_plan', {'shift': 2, 'profile': '../local-data'}),
                           ('wos_shift_plan', {'shift': 2, 'profile': 'main', 'execute': True})]:
            with self.assertRaises(ValueError):
                d.call(name, args)

    def test_lifecycle_and_no_execution_tool(self):
        s = Server(Discovery())
        def req(method, params=None):
            return s.handle({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})
        self.assertIn('error', req('tools/list'))
        self.assertEqual(req('initialize', {'protocolVersion': PROTOCOL, 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}})['result']['protocolVersion'], PROTOCOL)
        self.assertIsNone(s.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'}))
        tools = req('tools/list')['result']['tools']
        self.assertEqual({t['name'] for t in tools}, {'wos_capabilities', 'wos_shift_plan'})
        self.assertTrue(all(t['annotations']['readOnlyHint'] for t in tools))
        self.assertTrue(req('tools/call', {'name': 'execute'})['result']['isError'])

    def test_real_stdio_stdout_only_protocol_and_no_notification_response(self):
        messages = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': PROTOCOL, 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}},
                    {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                    {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'wos_shift_plan', 'arguments': {'shift': 2, 'profile': 'under30-test'}}}]
        p = subprocess.run([sys.executable, str(SCRIPTS / 'capability_mcp.py')], input='\n'.join(map(json.dumps, messages))+'\n', text=True, capture_output=True, check=True)
        lines = [json.loads(x) for x in p.stdout.splitlines()]
        self.assertEqual([x['id'] for x in lines], [1, 2])
        data = json.loads(lines[1]['result']['content'][0]['text'])
        self.assertEqual(data['acceptance']['native_wos_acceptance'], 'pending')
        self.assertNotIn('local-data', p.stdout)


if __name__ == '__main__':
    unittest.main()
