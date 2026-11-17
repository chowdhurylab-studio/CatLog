"""The fingerprint of a staged release folder (site_build/release): `catlog.py site stage` records it in
site_build/build.json, and cloudflare/stage.py and publish.py check it before staging or publishing. No dependencies, so
the cloudflare scripts can import it without the rest of tools/."""
import hashlib
from pathlib import Path


def release_tree(folder):
    """(sha256, files, bytes): the sha256 of the folder's sorted 'sha256  path' lines, every file but __pycache__ and
    .DS_Store."""
    folder, lines, total = Path(folder), [], 0
    for path in sorted(folder.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.name != '.DS_Store':
            with open(path, 'rb') as fh:
                digest = hashlib.file_digest(fh, 'sha256').hexdigest()
            lines.append(f'{digest}  {path.relative_to(folder).as_posix()}\n')
            total += path.stat().st_size
    return hashlib.sha256(''.join(lines).encode()).hexdigest(), len(lines), total
