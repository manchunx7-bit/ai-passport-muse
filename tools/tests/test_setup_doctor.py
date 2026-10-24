"""Local network inspection regressions; no Internet, device or Token is used."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import setup_doctor as d


def windows_run(listeners):
    def run(argv):
        if 'Get-NetIPConfiguration' in argv[-1]:
            return json.dumps([dict(interface='Wi-Fi', address='192.168.50.10'),
                               dict(interface='Mihomo', address='198.18.0.1'),
                               dict(interface='vEthernet', address='172.22.0.1')])
        return json.dumps(listeners)
    return run


class NetworkDoctorTest(unittest.TestCase):
    def test_direct_mode_does_not_require_or_inspect_proxy(self):
        run = mock.Mock(wraps=windows_run([]))
        report = d.collect(system='Windows', run=run)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(report['overall'], 'LOCAL_CHECKS_PASSED')
        self.assertEqual(report['cloud_connection'], 'NOT_RUN')
        self.assertEqual(report['real_reply'], 'NOT_RUN')
        self.assertEqual(report['checks'][-1]['status'], 'NOT_RUN')
        self.assertEqual(report['checks'][1]['detail'], [dict(interface='Wi-Fi', address='192.168.50.10')])

    def test_loopback_and_ipv6_only_are_not_lan_success(self):
        for address in ('127.0.0.1', '::1', '::'):
            with self.subTest(address=address):
                report = d.collect(7900, 'Windows', windows_run([dict(address=address, pid=10)]))
                self.assertEqual(report['overall'], 'NEEDS_ATTENTION')

    def test_ipv4_all_and_matching_interface_are_candidates_only(self):
        for address in ('0.0.0.0', '192.168.50.10'):
            with self.subTest(address=address):
                report = d.collect(7900, 'Windows', windows_run([dict(address=address, pid=10)]))
                self.assertEqual(report['overall'], 'LOCAL_CHECKS_PASSED')
                self.assertEqual(report['device_configuration'], 'NOT_RUN')

    def test_inspection_error_never_claims_success(self):
        report = d.collect(7900, 'Windows', mock.Mock(side_effect=RuntimeError('denied')))
        self.assertEqual(report['overall'], 'NEEDS_ATTENTION')
        self.assertEqual(report['checks'][-1]['status'], 'FAIL')

    def test_macos_uses_default_interface_and_only_specified_ipv4_port(self):
        def run(argv):
            if argv[0].endswith('route'):
                return '  interface: en7\n'
            if argv[0].endswith('ifconfig'):
                self.assertEqual(argv[-1], 'en7')
                return '\tinet 192.168.50.10 netmask 0xffffff00\n'
            self.assertIn('-i4TCP:7900', argv)
            return 'p123\nn*:7900\n'
        report = d.collect(7900, 'Darwin', run)
        self.assertEqual(report['overall'], 'LOCAL_CHECKS_PASSED')
        self.assertEqual(report['checks'][-1]['detail']['listeners'][0]['pid'], 123)

    def test_macos_tunnel_is_not_physical_lan(self):
        def run(argv):
            return '  interface: utun3\n' if argv[0].endswith('route') else '\tinet 10.0.0.1\n'
        report = d.collect(system='Darwin', run=run)
        self.assertEqual(report['overall'], 'NEEDS_ATTENTION')

    def test_macos_listener_inspection_failure_is_not_success(self):
        def run(argv):
            if argv[0].endswith('route'):
                return '  interface: en0\n'
            if argv[0].endswith('ifconfig'):
                return '\tinet 192.168.50.10\n'
            raise RuntimeError('No visible matching listener')
        report = d.collect(7900, 'Darwin', run)
        self.assertEqual(report['overall'], 'NEEDS_ATTENTION')
        self.assertEqual(report['real_reply'], 'NOT_RUN')

    def test_json_contract_and_exit_code(self):
        report = d.collect(7900, 'Windows', windows_run([]))
        with mock.patch.object(d, 'collect', return_value=report), \
             mock.patch('sys.stdout', new_callable=io.StringIO) as stream:
            self.assertEqual(d.main(['--proxy-port', '7900', '--json']), 1)
        self.assertEqual(json.loads(stream.getvalue())['schema_version'], 1)
        with mock.patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
            d.main(['--proxy-port', '0', '--json'])
        self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
