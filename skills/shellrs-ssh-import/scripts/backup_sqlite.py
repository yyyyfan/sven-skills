"""Create and validate a consistent SQLite snapshot without overwriting files."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3


def backup_database(source, destination):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve()
    if source == destination:
        raise ValueError('Backup destination must differ from the source.')
    # Exclusive creation also protects against destination races.
    with destination.open('xb'):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as reader:
            with closing(sqlite3.connect(str(destination))) as writer:
                reader.backup(writer)
                integrity = writer.execute('PRAGMA integrity_check').fetchall()
                if integrity != [('ok',)]:
                    raise RuntimeError('Snapshot integrity check failed.')
                if writer.execute('PRAGMA foreign_key_check').fetchall():
                    raise RuntimeError('Snapshot contains broken foreign keys.')
    except Exception:
        # Keep any failed snapshot for diagnosis and never report it as valid.
        raise
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    result = backup_database(args.db, args.destination)
    print('Validated SQLite backup:', result)


if __name__ == '__main__':
    main()
