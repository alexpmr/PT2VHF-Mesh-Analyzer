"""Keep only the current complete stable release; never delete tags or git history."""
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

REPOSITORY = 'alexpmr/PT2VHF-Mesh-Analyzer'


def version(tag):
    match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)', str(tag))
    return tuple(map(int, match.groups())) if match else None


def removal_plan(latest, releases, expected_tag):
    keep = version(expected_tag)
    if keep is None or latest.get('tag_name') != expected_tag:
        raise ValueError('Current latest release does not match the build version')
    if latest.get('draft') or latest.get('prerelease'):
        raise ValueError('Protected release must be published and stable')
    # New universal Windows 10/11 packages plus legacy names ensure
    # older v0.6.25 clients can auto-update without losing their known assets.
    required = {f'PT2VHF-Mesh-Analyzer-{expected_tag}-Setup-Win10-Win11-x64.exe',
                f'PT2VHF-Mesh-Analyzer-{expected_tag}-Portable-Win10-Win11-x64.exe',
                f'PT2VHF-Mesh-Analyzer-{expected_tag}-Portable-Win10-Win11-x64.zip',
                f'PT2VHF-Mesh-Analyzer-{expected_tag}-Setup-Win11-x64.exe',
                f'PT2VHF-Mesh-Analyzer-{expected_tag}-Portable-Win11-x64.zip',
                'SHA256SUMS.txt'}
    uploaded = {a['name'] for a in latest.get('assets', [])
                if a.get('state') == 'uploaded' and a.get('size', 0) > 0}
    if not required.issubset(uploaded):
        raise ValueError('Latest release is incomplete; cleanup refused')
    plan = []
    for release in releases:
        candidate = version(release.get('tag_name'))
        if release.get('draft') or release.get('prerelease') or candidate is None:
            continue
        if candidate > keep:
            raise ValueError('A newer stable release exists; cleanup refused')
        if candidate < keep and release['id'] != latest['id']:
            plan.append(release)
    return plan


def api(method, path):
    token = os.environ['GH_TOKEN']
    request = urllib.request.Request(
        'https://api.github.com/repos/' + REPOSITORY + path,
        method=method, headers={'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json', 'User-Agent': 'PT2VHF-release-retention',
            'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
            return json.loads(data) if data else None
    except urllib.error.HTTPError as exc:
        if method == 'DELETE' and exc.code == 404:
            return None  # Concurrent cleanup already removed this release.
        raise


def main():
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('Unexpected repository')
    tag = 'v' + (Path(__file__).resolve().parents[1]/'VERSION').read_text().strip()
    latest = api('GET', '/releases/latest')
    if latest['tag_name'] != tag:
        print('Build is not the current latest release; no deletion.')
        return
    releases = []
    page = 1
    while True:
        batch = api('GET', f'/releases?per_page=100&page={page}')
        releases.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    plan = removal_plan(latest, releases, tag)
    print(f'Keeping {tag}; removing {len(plan)} older releases. Git tags/history unchanged.')
    for release in plan:
        current = api('GET', '/releases/latest')
        # Revalidate completeness and identity immediately before every deletion.
        removal_plan(current, [release], tag)
        if current['id'] != latest['id']:
            raise ValueError('Latest release changed during cleanup')
        api('DELETE', '/releases/' + str(int(release['id'])))
        print('Removed release and downloadable assets:', release['tag_name'])


if __name__ == '__main__':
    main()
