# Mechanism: mechanism-shape
"""The test base itself: a case that is not marked as proving a process cannot start one, the
scripts' Git listing it answers from the folder never outlives the case, and no script runs
without being told the tree it works in."""

from __future__ import annotations

import importlib
import inspect
import subprocess
import sys
import types
import unittest

from repository import RepositoryCase, proves_a_process

import docs_corpus


def outcome(case: type[unittest.TestCase]) -> unittest.TestResult:
    """Runs a planted case on its own and returns what it did."""
    result = unittest.TestResult()
    unittest.TestLoader().loadTestsFromTestCase(case).run(result)
    return result


class TheGuard(unittest.TestCase):
    def test_a_case_not_marked_fails_when_it_starts_a_process_and_names_it(self) -> None:
        class Unmarked(RepositoryCase):
            def test_starts_git(self) -> None:
                subprocess.run(["git", "--version"], capture_output=True)

        result = outcome(Unmarked)

        self.assertEqual(1, len(result.failures))
        self.assertIn("not marked as proving a process", result.failures[0][1])
        self.assertIn("'git', '--version'", result.failures[0][1])

    def test_a_marked_test_may_start_what_it_proves_in_a_real_repository(self) -> None:
        class Marked(RepositoryCase):
            @proves_a_process
            def test_reads_its_repository(self) -> None:
                self.assertTrue((self.root / ".git").is_dir())
                subprocess.run(["git", "status"], cwd=self.root, capture_output=True, check=True)

        result = outcome(Marked)

        self.assertEqual([], result.failures + result.errors)
        self.assertEqual(1, result.testsRun)

    def test_a_case_not_marked_gets_a_plain_folder(self) -> None:
        class Unmarked(RepositoryCase):
            def test_has_no_repository(self) -> None:
                self.assertFalse((self.root / ".git").exists())

        result = outcome(Unmarked)

        self.assertEqual([], result.failures + result.errors)


class AScriptGivenNoRoot(unittest.TestCase):
    """A script's `main()` takes the tree it works in as a required argument, so a test that forgets
    its own tree fails at the call rather than writing into this one (the user, 2026-10-12)."""

    SCRIPTS = ("edges", "inject_rules", "maintain", "mechanisms", "move_doc", "questions", "straw_dogs", "tickets")

    def test_every_script_s_main_has_no_default_root(self) -> None:
        for name in self.SCRIPTS:
            with self.subTest(script=name):
                root = inspect.signature(importlib.import_module(name).main).parameters["root"]

                self.assertIs(inspect.Parameter.empty, root.default)

    def test_a_call_without_a_root_fails_before_it_reads_anything(self) -> None:
        import questions

        with self.assertRaisesRegex(TypeError, "root"):
            questions.main(["--check"])


class TheFolderListing(unittest.TestCase):
    def test_answers_the_scripts_listing_with_every_file_in_gits_order(self) -> None:
        listed: list[str] = []

        class Unmarked(RepositoryCase):
            def test_lists(self) -> None:
                self.write("b.md", "b\n")
                self.write("a/z.md", "z\n")
                self.write("a.md", "a\n")
                listed.extend(docs_corpus.corpus(self.root))

        result = outcome(Unmarked)

        self.assertEqual([], result.failures + result.errors)
        self.assertEqual(["a.md", "a/z.md", "b.md"], listed)

    def test_gives_git_back_when_the_case_ends_even_to_a_module_imported_during_it(self) -> None:
        git_listing = docs_corpus.corpus
        late = types.ModuleType("imported_during_the_case")
        self.addCleanup(sys.modules.pop, late.__name__, None)
        bound: list[object] = []

        class Unmarked(RepositoryCase):
            def test_imports(self) -> None:
                # What an import made inside a case does: the module lands in `sys.modules`
                # and binds the listing `docs_corpus` holds at that moment.
                sys.modules[late.__name__] = late
                late.corpus = docs_corpus.corpus
                bound.append(late.corpus)

        result = outcome(Unmarked)

        self.assertEqual([], result.failures + result.errors)
        self.assertIsNot(git_listing, bound[0])
        self.assertIs(git_listing, docs_corpus.corpus)
        self.assertIs(git_listing, late.corpus)


if __name__ == "__main__":
    unittest.main()
