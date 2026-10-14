# Mechanism: ticket
"""Preflight: why a selection must not happen at all, and the proof that nothing moved."""

from __future__ import annotations

import unittest

from repository import RepositoryCase, proves_a_process

import move_doc

TICKET = "docs/tickets/01-0010.0040-install-plan.md"
RFC = "docs/rfc/01-0010.0040-install-plan.md"
CLOSED_TICKET = "docs/tickets/done/01-0010.0040-install-plan.md"
CLOSED_RFC = "docs/rfc/done/01-0010.0040-install-plan.md"


class Refusal(RepositoryCase):
    def setUp(self) -> None:
        super().setUp()
        self.write(TICKET, "# Install /plan\n")
        self.write(RFC, "# Install /plan — plan\n")
        self.write("docs/tickets/README.md", "# Queue\n\n[plan](01-0010.0040-install-plan.md)\n")

    def refused_for(self, pairs: list[tuple[str, str]]) -> str:
        untouched = self.snapshot()
        why = move_doc.refusal(self.root, pairs)
        self.assertIsNotNone(why, f"expected a refusal for {pairs}")
        self.assertEqual(untouched, self.snapshot(), "a refusal must not change a single byte")
        return why

    def test_a_record_that_is_not_there_cannot_move(self) -> None:
        self.assertIn("not a record", self.refused_for([("docs/tickets/absent.md", CLOSED_TICKET)]))

    def test_only_markdown_records_move(self) -> None:
        self.write("docs/diagram.png", "not really a png")
        self.assertIn("markdown", self.refused_for([("docs/diagram.png", "docs/done/diagram.png")]))

    def test_the_same_record_cannot_be_sent_to_two_homes(self) -> None:
        why = self.refused_for([(TICKET, CLOSED_TICKET), (TICKET, "docs/tickets/elsewhere.md")])
        self.assertIn("twice", why)

    def test_two_records_cannot_claim_one_home(self) -> None:
        why = self.refused_for([(TICKET, CLOSED_TICKET), (RFC, CLOSED_TICKET)])
        self.assertIn("claimed twice", why)

    @proves_a_process
    def test_an_ignored_file_still_occupies_its_destination(self) -> None:
        self.write(".gitignore", "docs/tickets/done/\n")
        self.write(CLOSED_TICKET, "# Ignored, but really there\n")
        self.commit()
        self.assertIn("already exists", self.refused_for([(TICKET, CLOSED_TICKET)]))

    def test_a_record_cannot_move_to_where_it_already_is(self) -> None:
        self.assertIn("already there", self.refused_for([(TICKET, TICKET)]))

    def test_one_records_destination_cannot_be_another_records_home(self) -> None:
        why = self.refused_for([(TICKET, "docs/rfc/01-0010.0040-install-plan.md"), (RFC, CLOSED_RFC)])
        self.assertIn("overlap", why)

    def test_a_destination_differing_only_in_case_is_a_collision(self) -> None:
        why = self.refused_for([(TICKET, CLOSED_TICKET), (RFC, CLOSED_TICKET.upper())])
        self.assertIn("claimed twice", why)

    def test_a_destination_outside_the_repository_is_refused(self) -> None:
        why = self.refused_for([(TICKET, "../escaped/01-0010.0040-install-plan.md")])
        self.assertIn("outside the repository", why)


class Coverage(RepositoryCase):
    """A close may only claim complete repair when the whole corpus could actually be read."""

    def setUp(self) -> None:
        super().setUp()
        self.write(TICKET, "# Install /plan\n")

    def test_a_record_the_scan_cannot_read_refuses_the_close(self) -> None:
        (self.root / "docs/notes.md").write_bytes(b"# Notes \xff\xfe with a stray byte\n")
        untouched = self.snapshot()

        why = move_doc.refusal(self.root, [(TICKET, CLOSED_TICKET)])

        self.assertIn("docs/notes.md", why)
        self.assertIn("not utf-8", why.lower())
        self.assertEqual(untouched, self.snapshot())


class Escapes(RepositoryCase):
    """A destination that only looks like it is inside the repository."""

    def setUp(self) -> None:
        super().setUp()
        self.write(TICKET, "# Install /plan\n")

    def test_a_destination_reached_through_a_junction_out_of_the_tree_is_refused(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir()
        self.addCleanup(outside.rmdir)
        if not self._junction("docs/escape", outside):
            self.skipTest("this platform cannot create a directory junction or symlink here")
        untouched = self.snapshot()

        why = move_doc.refusal(self.root, [(TICKET, "docs/escape/01-0010.0040-install-plan.md")])

        self.assertIn("outside the repository", why)
        self.assertEqual(untouched, self.snapshot())

    def _junction(self, name: str, target) -> bool:
        link = self.root / name
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            # Windows refuses a symlink without the privilege and makes a junction without one —
            # through the API CPython's own tests use, so no process is started for it.
            try:
                import _winapi
            except ImportError:
                return False
            try:
                _winapi.CreateJunction(str(target), str(link))
            except OSError:
                return False
        self.addCleanup(self._remove_link, link)
        return True

    @staticmethod
    def _remove_link(link) -> None:
        # A POSIX symlink goes through unlink; a junction or a Windows directory symlink through rmdir.
        try:
            link.unlink()
        except OSError:
            link.rmdir()


if __name__ == "__main__":
    unittest.main()
