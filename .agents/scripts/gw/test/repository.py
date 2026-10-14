# Mechanism: mechanism-shape
"""A disposable tree the maintenance scripts can be exercised against, never this one.

A case builds a real repository only when Git, or a child process, is what it proves, and says so
with `proves_a_process`. Every other case gets a plain folder, the scripts' Git listing of it
answered from the folder itself, and a guard that fails it on any process start — which is also
what proves it changes no Git index. Nothing here may be imported by runtime code.
"""

from __future__ import annotations

import atexit
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import docs_corpus  # noqa: E402  (path set just above)

_TEMPLATE: Path | None = None


def proves_a_process(test: Callable) -> Callable:
    """Marks one test whose subject is a process — Git's listing, a clone, a child — so it gets
    a real repository and may start what it proves; a class marks all its tests with the
    attribute of the same name."""
    test.proves_a_process = True
    return test


def _template() -> Path:
    """The `.git` every case is stamped from, built once per process.

    `git init` and its two identity settings are three process spawns — some 320ms on Windows —
    and every case paid them, which was most of the suite's wall clock. Copying this directory
    gives the same repository for a twenty-fifth of that. Git builds it, with an empty init
    template so no sample hook joins the copy, so a case still receives a real repository rather
    than a hand-rolled imitation of one.
    """
    global _TEMPLATE
    if _TEMPLATE is None:
        workspace = tempfile.TemporaryDirectory()
        atexit.register(workspace.cleanup)
        no_hooks = Path(workspace.name) / "no-hooks"
        no_hooks.mkdir()
        seed = Path(workspace.name) / "seed"
        subprocess.run(
            ["git", "init", "--initial-branch", "main", "--template", str(no_hooks), str(seed)],
            capture_output=True,
            encoding="utf-8",
            check=True,
        )
        with (seed / ".git" / "config").open("a", encoding="utf-8") as handle:
            handle.write("[user]\n\temail = harness@example.invalid\n\tname = Harness\n")
        _TEMPLATE = seed / ".git"
    return _TEMPLATE


class RepositoryCase(unittest.TestCase):
    """A test whose subject is a fresh tree at `self.root`: a real repository when the case
    proves a process, a plain folder with every process refused when it does not."""

    proves_a_process = False

    def setUp(self) -> None:
        self.root = self._fresh_tree()
        if not self._proves_a_process():
            self._refuse_processes()
            self._answer_listings_from_the_folder()

    def another_repository(self) -> Path:
        """A second fresh tree beside `self.root`, for a case whose subject acts across two
        trees — an install of core from one into the other. Cleaned up with the case."""
        return self._fresh_tree()

    def _proves_a_process(self) -> bool:
        test = getattr(self, self._testMethodName)
        return getattr(test, "proves_a_process", False) or type(self).proves_a_process

    def _fresh_tree(self) -> Path:
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        tree = Path(workspace.name).resolve()
        if self._proves_a_process():
            shutil.copytree(_template(), tree / ".git")
        return tree

    def _refuse_processes(self) -> None:
        """Any process start fails the case, naming what it tried: `run`, `check_output` and the
        rest all start through `Popen`."""
        case = type(self).__name__

        def refused(arguments, *_, **__):
            raise AssertionError(f"{case} starts {arguments!r} but is not marked as proving a process")

        self._patch(subprocess, "Popen", refused)

    def _answer_listings_from_the_folder(self) -> None:
        """Every module holding the scripts' Git listing gets the folder's own instead: the
        scripts import it by name, so each binding is replaced where it was made, `docs_corpus`
        included — which a script first imported during the case binds from. When the case ends,
        every binding to the folder's listing gets Git's back, so none outlives it into a case
        that proves the real one."""
        git_listing = docs_corpus.corpus

        def rebound(listing, to) -> None:
            for module in list(sys.modules.values()):
                if getattr(module, "corpus", None) is listing:
                    module.corpus = to

        rebound(git_listing, folder_listing)
        self.addCleanup(rebound, folder_listing, git_listing)

    def _patch(self, owner: object, name: str, value: object) -> None:
        patcher = mock.patch.object(owner, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, *arguments: str) -> str:
        done = subprocess.run(
            ["git", *arguments], cwd=self.root, capture_output=True, encoding="utf-8", check=True
        )
        return done.stdout

    def write(self, name: str, text: str) -> Path:
        """Place a record at a root-relative name, byte-exact — no newline translation."""
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return path

    def read(self, name: str) -> str:
        with (self.root / name).open(encoding="utf-8", newline="") as handle:
            return handle.read()

    def commit(self, message: str = "records") -> None:
        self.git("add", "-A")
        self.git("commit", "-m", message)

    def snapshot(self) -> dict[str, bytes]:
        """Every working-tree byte, so a refusal can be shown to change nothing — and the index
        too where the case may start a process; elsewhere the guard is what proves it untouched."""
        files = {name: (self.root / name).read_bytes() for name in folder_listing(self.root)}
        if not self._proves_a_process():
            return files
        return {**files, "<index>": self.git("ls-files", "--stage").encode()}


def folder_listing(root: Path) -> list[str]:
    """What the scripts' Git listing names for a tree nothing is ignored in: every file beneath
    the root, `.git` aside, root-relative and in Git's order."""
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    )
