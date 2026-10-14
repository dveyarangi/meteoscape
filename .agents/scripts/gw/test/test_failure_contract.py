# Mechanism: ticket
"""What a close does when it cannot finish: stop, say what happened, and change nothing further."""

from __future__ import annotations

import os
import stat
import unittest

from repository import RepositoryCase

import move_doc

TICKET = "docs/tickets/01-0010.0040-install-plan.md"
RFC = "docs/rfc/01-0010.0040-install-plan.md"
CLOSED_TICKET = "docs/tickets/done/01-0010.0040-install-plan.md"
CLOSED_RFC = "docs/rfc/done/01-0010.0040-install-plan.md"
QUEUE = "docs/tickets/README.md"


class InterruptedClose(RepositoryCase):
    def setUp(self) -> None:
        super().setUp()
        self.write(TICKET, "# Install /plan\n\n[the RFC](../rfc/01-0010.0040-install-plan.md)\n")
        self.write(RFC, "# Install /plan — plan\n\n[the ticket](../tickets/01-0010.0040-install-plan.md)\n")
        self.write(QUEUE, "# Queue\n\n[plan](01-0010.0040-install-plan.md)\n")
        self.pairs = [(TICKET, CLOSED_TICKET), (RFC, CLOSED_RFC)]

    def test_a_failure_on_the_second_record_stops_and_reports_both_halves(self) -> None:
        self.write("docs/rfc/done", "a file where the archive folder should be")
        rfc_before, queue_before = self.read(RFC), self.read(QUEUE)

        with self.assertRaises(move_doc.CloseInterrupted) as stopped:
            move_doc.perform(self.root, self.pairs)

        self.assertEqual([f"{TICKET} -> {CLOSED_TICKET}"], stopped.exception.completed)
        self.assertIn(f"{RFC} -> {CLOSED_RFC}", stopped.exception.pending)
        self.assertEqual(CLOSED_RFC, stopped.exception.failed)
        self.assertTrue((self.root / CLOSED_TICKET).exists(), "the first record did move")
        self.assertEqual(rfc_before, self.read(RFC))
        self.assertEqual(queue_before, self.read(QUEUE))

    def test_a_record_whose_write_is_refused_keeps_its_content(self) -> None:
        os.chmod(self.root / QUEUE, stat.S_IREAD)
        self.addCleanup(os.chmod, self.root / QUEUE, stat.S_IWRITE | stat.S_IREAD)
        if not self._write_is_refused():
            self.skipTest("this platform lets a read-only record be replaced")
        queue_before = self.read(QUEUE)

        with self.assertRaises(move_doc.CloseInterrupted) as stopped:
            move_doc.perform(self.root, self.pairs)

        self.assertEqual(queue_before, self.read(QUEUE), "a failed write must not cost content")
        self.assertEqual(QUEUE, stopped.exception.failed)

    def _write_is_refused(self) -> bool:
        """Whether this platform's read-only bit actually stops a write — POSIX ignores it here."""
        guarded = self.root / "probe-read-only.md"
        guarded.write_text("probe", encoding="utf-8")
        os.chmod(guarded, stat.S_IREAD)
        self.addCleanup(os.chmod, guarded, stat.S_IWRITE | stat.S_IREAD)
        staging = self.root / "probe.tmp"
        staging.write_text("replacement", encoding="utf-8")
        try:
            staging.replace(guarded)
        except OSError:
            staging.unlink()
            return True
        return False

    def test_a_destination_that_appears_mid_run_is_a_failure_not_an_overwrite(self) -> None:
        interference = "# written by somebody else, mid-run\n"

        def intrude(_: str) -> None:
            self.write(CLOSED_RFC, interference)

        with self.assertRaises(move_doc.CloseInterrupted) as stopped:
            move_doc.perform(self.root, self.pairs, announce=intrude)

        self.assertEqual(CLOSED_RFC, stopped.exception.failed)
        self.assertEqual(interference, self.read(CLOSED_RFC))

    def test_a_record_edited_mid_run_is_not_overwritten_with_stale_text(self) -> None:
        edited = "# Queue\n\n[plan](01-0010.0040-install-plan.md)\n\nA note added mid-run.\n"

        def intrude(_: str) -> None:
            self.write(QUEUE, edited)

        with self.assertRaises(move_doc.CloseInterrupted) as stopped:
            move_doc.perform(self.root, self.pairs, announce=intrude)

        self.assertEqual(edited, self.read(QUEUE))
        self.assertEqual(QUEUE, stopped.exception.failed)

    def test_a_record_edited_mid_move_keeps_its_edit_where_it_was(self) -> None:
        # The edit lands after the change set was derived, the interleaving the 2026-09-30 audit
        # showed losing it; a source changed before the run would pass for the wrong reason.
        edited = "# Install /plan — plan\n\n[the ticket](../tickets/01-0010.0040-install-plan.md)\n\nA decision added mid-run.\n"

        def intrude(said: str) -> None:
            if said == f"moved {TICKET} -> {CLOSED_TICKET}":
                self.write(RFC, edited)

        with self.assertRaises(move_doc.CloseInterrupted) as stopped:
            move_doc.perform(self.root, self.pairs, announce=intrude)

        self.assertEqual(edited, self.read(RFC), "the edit stands in the source")
        self.assertFalse((self.root / CLOSED_RFC).exists(), "nothing stale is written in its place")
        self.assertEqual([f"{TICKET} -> {CLOSED_TICKET}"], stopped.exception.completed)
        self.assertIn(RFC, str(stopped.exception.cause), "the failure names the source")


if __name__ == "__main__":
    unittest.main()
