# Mechanism: ticket
"""Which citations a move may change, and which it must leave exactly as written."""

from __future__ import annotations

import unittest

from repository import RepositoryCase, proves_a_process

import move_doc

TICKET = "docs/tickets/01-0010.0040-install-plan.md"
CLOSED = "docs/tickets/done/01-0010.0040-install-plan.md"


class CitationRepair(RepositoryCase):
    def setUp(self) -> None:
        super().setUp()
        self.write(TICKET, "# Install /plan\n")

    def close_the_ticket(self) -> None:
        move_doc.perform(self.root, [(TICKET, CLOSED)])

    def test_a_historical_record_is_repaired_and_keeps_the_facts_it_records(self) -> None:
        session = "docs/sessions/0002-20260905-the-harness-gets-a-home.md"
        self.write(
            session,
            "# Session 2\n\n**2026-09-05:** minted [the plan ticket](../tickets/01-0010.0040-install-plan.md).\n",
        )

        self.close_the_ticket()

        self.assertEqual(
            "# Session 2\n\n**2026-09-05:** minted [the plan ticket](../tickets/done/01-0010.0040-install-plan.md).\n",
            self.read(session),
        )

    def test_a_fragment_and_a_title_survive_the_repair(self) -> None:
        self.write(
            "docs/process.md",
            '# Process\n\nSee [criteria](tickets/01-0010.0040-install-plan.md#acceptance-criteria "The plan ticket").\n',
        )

        self.close_the_ticket()

        self.assertEqual(
            '# Process\n\nSee [criteria](tickets/done/01-0010.0040-install-plan.md#acceptance-criteria "The plan ticket").\n',
            self.read("docs/process.md"),
        )

    def test_an_external_reference_is_never_treated_as_a_repository_path(self) -> None:
        self.write(
            "docs/notes.md",
            "# Notes\n\n[home](https://example.invalid/01-0010.0040-install-plan.md) and [anchor](#section).\n",
        )
        before = self.read("docs/notes.md")

        self.close_the_ticket()

        self.assertEqual(before, self.read("docs/notes.md"))

    def test_an_illustration_of_the_syntax_is_not_a_citation(self) -> None:
        shelf = "docs/format.md"
        self.write(
            shelf,
            "# Format\n\nCite as `[title](tickets/01-0010.0040-install-plan.md)`:\n\n"
            "```md\n[title](tickets/01-0010.0040-install-plan.md)\n```\n",
        )
        before = self.read(shelf)

        self.close_the_ticket()

        self.assertEqual(before, self.read(shelf))

    def test_a_records_own_line_endings_and_unrelated_bytes_are_left_alone(self) -> None:
        self.write("docs/queue.md", "# Queue\r\n\r\n- [plan](tickets/01-0010.0040-install-plan.md)\r\n- trailing  \r\n")
        self.write("docs/unrelated.md", "# Unrelated\r\n\r\nNo citations here.\r\n")

        self.close_the_ticket()

        self.assertEqual(
            "# Queue\r\n\r\n- [plan](tickets/done/01-0010.0040-install-plan.md)\r\n- trailing  \r\n",
            self.read("docs/queue.md"),
        )
        self.assertEqual("# Unrelated\r\n\r\nNo citations here.\r\n", self.read("docs/unrelated.md"))

    @proves_a_process
    def test_a_record_minted_this_session_is_repaired_before_it_is_ever_staged(self) -> None:
        self.commit()
        self.write("docs/fresh.md", "# Fresh\n\n[plan](tickets/01-0010.0040-install-plan.md)\n")

        self.close_the_ticket()

        self.assertIn("tickets/done/01-0010.0040-install-plan.md", self.read("docs/fresh.md"))


class CitationForms(RepositoryCase):
    """Forms beyond the plain inline link that still name a record, and forms that do not."""

    def setUp(self) -> None:
        super().setUp()
        self.write(TICKET, "# Install /plan\n")

    def close_the_ticket(self) -> None:
        move_doc.perform(self.root, [(TICKET, CLOSED)])

    def test_a_reference_definition_follows_the_record(self) -> None:
        self.write(
            "docs/queue.md",
            "# Queue\n\nSee [the plan][plan].\n\n[plan]: tickets/01-0010.0040-install-plan.md\n",
        )

        self.close_the_ticket()

        self.assertEqual(
            "# Queue\n\nSee [the plan][plan].\n\n[plan]: tickets/done/01-0010.0040-install-plan.md\n",
            self.read("docs/queue.md"),
        )

    def test_an_absolute_path_inside_the_repository_follows_the_record(self) -> None:
        self.write(
            "docs/queue.md",
            f"# Queue\n\n[plan]({self.root.as_posix()}/docs/tickets/01-0010.0040-install-plan.md)\n",
        )

        self.close_the_ticket()

        self.assertEqual(
            f"# Queue\n\n[plan]({self.root.as_posix()}/docs/tickets/done/01-0010.0040-install-plan.md)\n",
            self.read("docs/queue.md"),
        )

    def test_a_file_uri_inside_the_repository_follows_the_record(self) -> None:
        uri = f"file:///{self.root.as_posix()}/docs/tickets/01-0010.0040-install-plan.md"
        self.write("docs/queue.md", f"# Queue\n\n[plan]({uri})\n")

        self.close_the_ticket()

        self.assertEqual(
            f"# Queue\n\n[plan]({uri.replace('/tickets/', '/tickets/done/')})\n",
            self.read("docs/queue.md"),
        )

    def test_an_absolute_path_in_another_repository_is_evidence_not_a_citation(self) -> None:
        self.write(
            "docs/queue.md",
            "# Queue\n\n[source](D:/Dev/AI/meteoscape/docs/tickets/01-0010.0040-install-plan.md)\n",
        )
        before = self.read("docs/queue.md")

        self.close_the_ticket()

        self.assertEqual(before, self.read("docs/queue.md"))

    def test_a_percent_encoded_target_is_recognised_and_re_encoded(self) -> None:
        spaced = "docs/tickets/install plan.md"
        self.write(spaced, "# Install plan\n")
        self.write("docs/queue.md", "# Queue\n\n[plan](tickets/install%20plan.md)\n")

        move_doc.perform(self.root, [(spaced, "docs/tickets/done/install plan.md")])

        self.assertEqual(
            "# Queue\n\n[plan](tickets/done/install%20plan.md)\n",
            self.read("docs/queue.md"),
        )

    def test_an_angle_bracketed_destination_keeps_its_brackets(self) -> None:
        self.write("docs/queue.md", "# Queue\n\n[plan](<tickets/01-0010.0040-install-plan.md>)\n")

        self.close_the_ticket()

        self.assertEqual(
            "# Queue\n\n[plan](<tickets/done/01-0010.0040-install-plan.md>)\n",
            self.read("docs/queue.md"),
        )

    def test_a_label_wrapped_across_lines_is_still_one_citation(self) -> None:
        self.write(
            "docs/queue.md",
            "# Queue\n\nSee [the install\nplan ticket](tickets/01-0010.0040-install-plan.md).\n",
        )

        self.close_the_ticket()

        self.assertEqual(
            "# Queue\n\nSee [the install\nplan ticket](tickets/done/01-0010.0040-install-plan.md).\n",
            self.read("docs/queue.md"),
        )

    def test_a_moving_records_citation_of_a_staying_record_is_re_depthed(self) -> None:
        self.write(TICKET, "# Install /plan\n\nGoverned by [the process](../process.md#verification).\n")
        self.write("docs/process.md", "# Process\n\n## Verification\n")

        self.close_the_ticket()

        self.assertEqual(
            "# Install /plan\n\nGoverned by [the process](../../process.md#verification).\n",
            self.read(CLOSED),
        )


class StrawDogBindings(RepositoryCase):
    """A straw dog binds a question by its id, which does not move when a record does: a move
    repairs citations and leaves every binding as written."""

    def setUp(self) -> None:
        super().setUp()
        self.write(TICKET, "# Install /plan\n")

    def close_the_ticket(self) -> None:
        move_doc.perform(self.root, [(TICKET, CLOSED)])

    def test_a_binding_stays_as_written_when_the_work_that_answers_it_closes(self) -> None:
        process = (
            "# Process\n\n"
            '<straw-dog question="q-0010.0040">\nPreliminary.\n</straw-dog>\n\n'
            '<straw-dog until="/plan is installed" ticket="docs/tickets/01-0010.0040-install-plan.md">\n'
            "Bound the old way.\n</straw-dog>\n"
        )
        self.write("docs/process.md", process)

        self.close_the_ticket()

        self.assertEqual(process, self.read("docs/process.md"))

    def test_an_illustration_of_the_binding_syntax_follows_nothing(self) -> None:
        entry = "AGENTS.md"
        self.write(
            entry,
            "# Entry\n\n"
            'Wrapped in `<straw-dog until="c" ticket="docs/tickets/01-0010.0040-install-plan.md">`.\n\n'
            "```md\n"
            '<straw-dog until="c" ticket="docs/tickets/01-0010.0040-install-plan.md">rule</straw-dog>\n'
            "```\n",
        )
        before = self.read(entry)

        self.close_the_ticket()

        self.assertEqual(before, self.read(entry))


if __name__ == "__main__":
    unittest.main()
