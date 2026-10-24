#!/usr/bin/env python3
"""Inspect local LAN candidates and one known proxy port; no network requests or writes."""
import argparse
from datetime import datetime, timezone
import ipaddress
import json
import platform
import re
import subprocess


def command(argv):
    result = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=15)
    if result.returncode:
        raise RuntimeError('Local command failed: ' + argv[0])
    return result.stdout


def lan_address(value):
    try:
        ip = ipaddress.IPv4Address(value)
        return (ip in ipaddress.IPv4Network('10.0.0.0/8')
                or ip in ipaddress.IPv4Network('172.16.0.0/12')
                or ip in ipaddress.IPv4Network('192.168.0.0/16'))
    except (ValueError, TypeError):
        return False


def physical_candidate(name):
    return not re.search(r'loopback|docker|wsl|vmware|vethernet|hyper-v|mihomo|clash|tun|tap|utun|bridge',
                         name, re.IGNORECASE)


def ps(script, run):
    return run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); " + script])


def rows(raw):
    parsed = json.loads(raw) if raw.strip() else []
    return parsed if isinstance(parsed, list) else [parsed]


def inspect_windows(port, run):
    candidates = rows(ps("@(Get-NetIPConfiguration -ErrorAction Stop | "
        "Where-Object IPv4DefaultGateway | ForEach-Object { "
        "$ifName=$_.InterfaceAlias; $_.IPv4Address | ForEach-Object { "
        "[pscustomobject]@{interface=$ifName;address=$_.IPAddress} } }) | ConvertTo-Json -Compress", run))
    listeners = None
    if port:
        # Enumerate locally, then filter: an empty result is distinct from a cmdlet failure.
        listeners = rows(ps("@(Get-NetTCPConnection -State Listen -ErrorAction Stop | "
            "Where-Object LocalPort -eq " + str(port) + " | ForEach-Object { "
            "[pscustomobject]@{address=$_.LocalAddress;pid=$_.OwningProcess} }) | ConvertTo-Json -Compress", run))
    return candidates, listeners


def inspect_macos(port, run):
    route = run(['/sbin/route', '-n', 'get', 'default'])
    match = re.search(r'^\s*interface:\s*(\S+)', route, re.MULTILINE)
    if not match:
        raise RuntimeError('No IPv4 default route interface found.')
    interface = match.group(1)
    info = run(['/sbin/ifconfig', interface])
    candidates = [dict(interface=interface, address=ip) for ip in
                  re.findall(r'^\s*inet\s+(\d+\.\d+\.\d+\.\d+)', info, re.MULTILINE)]
    listeners = None
    if port:
        try:
            output = run(['/usr/sbin/lsof', '-nP', '-i4TCP:' + str(port), '-sTCP:LISTEN', '-Fpn'])
        except RuntimeError:
            # Retain an explicit inspection failure rather than claiming no listener.
            raise RuntimeError('Cannot inspect proxy listener; verify with lsof in the network guide.') from None
        listeners = []
        pid = None
        for line in output.splitlines():
            if line.startswith('p'):
                pid = int(line[1:])
            if line.startswith('n') and pid is not None:
                endpoint = line[1:].rsplit(':', 1)[0].strip('[]')
                listeners.append(dict(address='0.0.0.0' if endpoint == '*' else endpoint, pid=pid))
    return candidates, listeners


def collect(port=None, system=None, run=command):
    system = system or platform.system()
    checks, candidates, listeners = [], [], None
    def add(name, status, detail, action=''):
        checks.append(dict(id=name, status=status, detail=detail, next_action=action))
    if system not in ('Windows', 'Darwin'):
        add('runtime', 'FAIL', 'Supported local inspection platforms: Windows and macOS.',
            'Use the manual network guide on other systems.')
    else:
        add('runtime', 'PASS', system)
        try:
            raw, listeners = (inspect_windows if system == 'Windows' else inspect_macos)(port, run)
            candidates = [r for r in raw if lan_address(r.get('address'))
                          and physical_candidate(r.get('interface', ''))]
            add('lan_ipv4', 'PASS' if candidates else 'USER_ACTION', candidates,
                'Confirm the physical LAN shared with the device; VPN/isolation may affect reachability.')
            if port:
                addresses = {r['address'] for r in candidates}
                usable = [r for r in listeners if r['address'] == '0.0.0.0' or r['address'] in addresses]
                add('proxy_listener', 'PASS' if usable else 'USER_ACTION',
                    dict(port=port, listeners=listeners),
                    'Confirm HTTP/Mixed port and Allow LAN; this does not test the protocol or device access.')
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
            add('local_inspection', 'FAIL', 'Could not read routing or selected listener information.',
                'Run the platform commands in docs/NETWORK.zh-CN.md and check permissions.')
    if not port:
        add('proxy_listener', 'NOT_RUN', 'No proxy port selected; direct device connection may need no proxy.',
            'If a proxy is needed, read its HTTP/Mixed port in the existing app, then use --proxy-port.')
    pending = [dict(id='device_network', action='Confirm Wi-Fi and device cloud readiness.'),
               dict(id='token_pairing', action='User enters Token locally and confirms phone pairing.'),
               dict(id='real_reply', action='User speaks; confirm first/second reply and reopen test.')]
    return dict(schema_version=1, application='muse',
                checked_at=datetime.now(timezone.utc).isoformat(), platform=system,
                overall='NEEDS_ATTENTION' if any(c['status'] in ('FAIL', 'USER_ACTION') for c in checks)
                else 'LOCAL_CHECKS_PASSED', checks=checks, pending_user_actions=pending,
                cloud_connection='NOT_RUN', device_configuration='NOT_RUN', real_reply='NOT_RUN')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Emit one structured JSON report.')
    parser.add_argument('--proxy-port', type=int, help='Inspect this known HTTP/Mixed TCP port, without scanning.')
    args = parser.parse_args(argv)
    if args.proxy_port is not None and not 1 <= args.proxy_port <= 65535:
        parser.error('--proxy-port must be from 1 to 65535')
    report = collect(args.proxy_port)
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        for item in report['checks']:
            print('[{status}] {id}: {detail}'.format(**item))
            if item['next_action']:
                print('  Next:', item['next_action'])
        print(report['overall'], '- cloud connection and real reply remain NOT_RUN.')
    return 1 if report['overall'] == 'NEEDS_ATTENTION' else 0


if __name__ == '__main__':
    raise SystemExit(main())
