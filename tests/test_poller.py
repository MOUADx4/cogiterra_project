"""Tests du module poller.imap_poller (sans connexion IMAP réelle)."""
import sys
import types
from unittest.mock import MagicMock, patch

from poller import ImapPoller


class FakeIMAPClient:
    """Mock minimaliste d'IMAPClient (context manager)."""

    existing_folders = {"INBOX", "Processed"}

    def __init__(self, host, port=993, ssl=True):
        self.host = host
        self.flags = {}     # uid -> list[bytes]
        self.deleted = []
        self.moved = []
        self.copied = []
        self.created_folders = []

    def folder_exists(self, folder):
        return folder in self.existing_folders

    def create_folder(self, folder):
        self.created_folders.append(folder)
        self.existing_folders.add(folder)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        self.user = user

    def select_folder(self, folder):
        self.folder = folder

    def search(self, criteria):
        return list(self._mailbox.keys())

    def fetch(self, uids, fields):
        return {uid: {b"RFC822": self._mailbox[uid]} for uid in uids}

    def add_flags(self, uid, flags):
        self.flags.setdefault(uid, []).extend(flags)

    def move(self, uid, folder):
        self.moved.append((uid, folder))

    def copy(self, uid, folder):
        self.copied.append((uid, folder))

    def delete_messages(self, uid):
        self.deleted.append(uid)

    def expunge(self):
        pass


def _fake_config(**overrides):
    cfg = types.SimpleNamespace(
        BOUNCE_IMAP_HOST="mail.test",
        BOUNCE_IMAP_PORT=993,
        BOUNCE_IMAP_USER="bounces@test",
        BOUNCE_IMAP_PASSWORD="x",
        BOUNCE_IMAP_FOLDER="INBOX",
        BOUNCE_IMAP_PROCESSED_FOLDER="",
        POLL_BATCH_LIMIT=200,
    )
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def _install_fake_imapclient(mailbox):
    """Injecte une fausse classe IMAPClient dans sys.modules.imapclient."""
    fake = FakeIMAPClient
    fake._mailbox = mailbox
    module = types.ModuleType("imapclient")
    module.IMAPClient = fake
    sys.modules["imapclient"] = module
    return fake


def test_poll_marks_seen_on_success():
    mailbox = {1: b"X-Test: msg1\r\n\r\nbody1",
               2: b"X-Test: msg2\r\n\r\nbody2"}
    fake_cls = _install_fake_imapclient(mailbox)
    poller = ImapPoller(_fake_config())

    seen_msgs = []
    def handler(raw): seen_msgs.append(raw); return True

    # Capture l'instance créée
    instances = []
    orig_init = fake_cls.__init__
    def init(self, *a, **kw):
        orig_init(self, *a, **kw); instances.append(self)
    fake_cls.__init__ = init

    ok, ko = poller.poll(handler)
    assert ok == 2 and ko == 0
    assert len(seen_msgs) == 2
    inst = instances[-1]
    assert inst.flags[1] == [b"\\Seen"]
    assert inst.flags[2] == [b"\\Seen"]
    assert inst.moved == []


def test_poll_leaves_unseen_on_failure():
    mailbox = {7: b"X-Test: bad\r\n\r\nbody"}
    fake_cls = _install_fake_imapclient(mailbox)
    poller = ImapPoller(_fake_config())

    instances = []
    orig_init = fake_cls.__init__
    def init(self, *a, **kw):
        orig_init(self, *a, **kw); instances.append(self)
    fake_cls.__init__ = init

    ok, ko = poller.poll(lambda raw: False)
    assert ok == 0 and ko == 1
    inst = instances[-1]
    assert 7 not in inst.flags   # pas marqué \Seen


def test_poll_moves_to_processed_folder():
    mailbox = {9: b"X-Test: x\r\n\r\nbody"}
    fake_cls = _install_fake_imapclient(mailbox)
    poller = ImapPoller(_fake_config(BOUNCE_IMAP_PROCESSED_FOLDER="Processed"))

    instances = []
    orig_init = fake_cls.__init__
    def init(self, *a, **kw):
        orig_init(self, *a, **kw); instances.append(self)
    fake_cls.__init__ = init

    ok, ko = poller.poll(lambda raw: True)
    assert ok == 1
    inst = instances[-1]
    assert inst.moved == [(9, "Processed")]


def test_poll_seen_only_does_not_move():
    """Handler retournant 'seen' → marqué \\Seen mais pas déplacé."""
    mailbox = {11: b"X-Test: contact\r\n\r\nbody"}
    fake_cls = _install_fake_imapclient(mailbox)
    poller = ImapPoller(_fake_config(BOUNCE_IMAP_PROCESSED_FOLDER="Processed"))

    instances = []
    orig_init = fake_cls.__init__
    def init(self, *a, **kw):
        orig_init(self, *a, **kw); instances.append(self)
    fake_cls.__init__ = init

    ok, ko = poller.poll(lambda raw: "seen")
    assert ok == 1 and ko == 0
    inst = instances[-1]
    assert inst.flags[11] == [b"\\Seen"]
    assert inst.moved == []
    assert inst.copied == []


def test_poll_handler_exception_keeps_unseen():
    mailbox = {3: b"X-Test: bug\r\n\r\nbody"}
    fake_cls = _install_fake_imapclient(mailbox)
    poller = ImapPoller(_fake_config())

    instances = []
    orig_init = fake_cls.__init__
    def init(self, *a, **kw):
        orig_init(self, *a, **kw); instances.append(self)
    fake_cls.__init__ = init

    def boom(raw): raise RuntimeError("crash")
    ok, ko = poller.poll(boom)
    assert ok == 0 and ko == 1
    inst = instances[-1]
    assert 3 not in inst.flags
