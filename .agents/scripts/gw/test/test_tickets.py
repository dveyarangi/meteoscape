# Mechanism: ticket
"""Reading a live ticket's header and sections, and saying whether the record keeps its shape."""

from __future__ import annotations

import contextlib
import io
import json
import unittest

from repository import RepositoryCase

import tickets

STORE = "docs/questions"
LIVE = "docs/tickets/01-0002-live.md"
PLANNED = "docs/tickets/01-0003-planned.md"
RFC = "docs/rfc/01-0003-planned.md"
QUEUE = "docs/tickets/README.md"
MARKED = "- **record of** what it intends to become\n"


def ticket(
    header: str,
    sections: str = (
        "## What to build\n\nThe thing.\n\n"
        "## Acceptance criteria\n\n- [ ] It works.\n- [ ] `/verify` has been run.\n"
    ),
    title: str = "# A ticket",
    mark: str = MARKED,
) -> str:
    return f"{title}\n\n{mark}{header}\n{sections}"


BEFORE = (
    "- **Status:** Ready\n"
    "- **Type:** HITL\n"
    "- **Minted:** 2026-09-08\n"
    "- **Depends on:** [an earlier one](./01-0001-earlier.md) (what it supplies)\n"
    "- **Outcome:** One sentence saying what lands.\n"
)
PLANNED_BEFORE = (
    "- **Status:** In progress\n"
    "- **Type:** AFK\n"
    "- **Minted:** 2026-09-08\n"
    "- **Plan:** [plan](../rfc/01-0003-planned.md) — what it selected\n"
    "- **Outcome:** One sentence saying what lands.\n"
)
# A ticket minted the day the format moved, and so held to the narrowed shape.
AFTER = BEFORE.replace("2026-09-08", tickets.FORMAT_MOVED)
NAMED_FIVE = (
    "## Parent\n\nThe spec.\n\n## What to build\n\nThe thing.\n\n"
    "## Acceptance criteria\n\n- [ ] It works.\n- [ ] `/verify` has been run.\n\n"
    "## Out of scope\n\nThe rest.\n\n## Parent scope addressed\n\nStories 1, 2.\n"
)


class Records(RepositoryCase):
    """A tree with two tickets minted before the format moved, one of them planned, and its RFC,
    all conforming.

    Every live ticket names the question it answers (the user, 2026-10-03), so a ticket written
    here without an `Answers` line is given one, and a store entry it owns, as it is written; a
    test of the field itself writes the ticket raw.
    """

    def setUp(self) -> None:
        super().setUp()
        self.questions: dict[str, str] = {}
        self.write(QUEUE, f"# Delivery status\n\n{MARKED}\n**Candidate:** none.\n")
        self.write("docs/tickets/01-0001-earlier.md", ticket(BEFORE))
        self.write(LIVE, ticket(BEFORE))
        self.write(PLANNED, ticket(PLANNED_BEFORE))
        self.write(RFC, "# A ticket — implementation plan\n")

    def write(self, name: str, text: str):
        if name.startswith("docs/tickets/0") and "**Outcome:**" in text and "**Answers:**" not in text:
            text = self.answered(name, text)
        return super().write(name, text)

    def write_raw(self, name: str, text: str):
        return super().write(name, text)

    def answered(self, name: str, text: str) -> str:
        """The ticket with an `Answers` line before its Outcome, naming an entry it owns."""
        if name not in self.questions:
            identity = f"q-{len(self.questions) + 1:04d}"
            self.questions[name] = f"{identity}-what-is-it-for.md"
            super().write(
                f"{STORE}/{self.questions[name]}",
                f"# {identity} What is it for?\n\n- **state** open\n"
                f"- **owner** [it](../tickets/{name.rsplit('/', 1)[1]})\n",
            )
        bullet = "- " if "- **Outcome:**" in text else ""
        line = f"{bullet}**Answers:** [{self.questions[name][:6]}](../questions/{self.questions[name]})\n"
        return text.replace(f"{bullet}**Outcome:**", line + f"{bullet}**Outcome:**", 1)

    def checked(self):
        return tickets.check(self.root)

    def problems(self) -> list[str]:
        return [note.problem for note in self.checked().diagnostics]

    def problem_lines(self) -> list[tuple[str, int]]:
        return [(note.record, note.line) for note in self.checked().diagnostics]


class TheHeader(Records):
    def test_written_bare_rather_than_as_a_bullet_list_is_reported_as_the_form(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("- **", "**")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("bullet list", problems[0])
        self.assertEqual([(LIVE, 4)], self.problem_lines(), "the mark's line counts")

    def test_missing_a_required_field_names_it(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("- **Type:** HITL\n", "")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Type", problems[0])

    def test_allows_one_parenthetical_qualifier(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("Ready", "Ready (aligned 2026-09-08)")))

        self.assertEqual([], self.problems())

    def test_done_must_open_its_parenthetical_with_the_date(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("Ready", "Done (split)")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Done", problems[0])
        self.assertIn("date", problems[0])

    def test_done_dated_with_words_after_a_comma_is_fine(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("Ready", "Done (2026-09-08, split)")))

        self.assertEqual([], self.problems())

    def test_with_a_type_outside_hitl_and_afk_is_reported(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("HITL", "Pairing")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Pairing", problems[0])

    def test_carrying_kind_is_reported_since_it_is_no_longer_a_field(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("- **Type:** HITL\n", "- **Type:** HITL\n- **Kind:** Maintenance\n")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Kind", problems[0])

    def test_with_outcome_before_another_field_is_reported(self) -> None:
        swapped = (
            "- **Status:** Ready\n"
            "- **Outcome:** One sentence saying what lands.\n"
            "- **Type:** HITL\n"
            "- **Minted:** 2026-09-08\n"
        )
        self.write(LIVE, ticket(swapped))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Outcome", problems[0])
        self.assertIn("last", problems[0])

    def test_with_known_fields_out_of_the_shelfs_order_is_reported(self) -> None:
        swapped = (
            "- **Type:** HITL\n"
            "- **Status:** Ready\n"
            "- **Minted:** 2026-09-08\n"
            "- **Outcome:** One sentence saying what lands.\n"
        )
        self.write(LIVE, ticket(swapped))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Status", problems[0])
        self.assertIn("order", problems[0])

    def test_a_one_off_field_may_sit_anywhere_before_outcome(self) -> None:
        self.write(
            LIVE,
            ticket(BEFORE.replace("- **Type:** HITL\n", "- **Related:** [x](./01-0001-earlier.md)\n- **Type:** HITL\n")),
        )

        self.assertEqual([], self.problems())

    def test_with_an_outcome_of_two_sentences_is_reported(self) -> None:
        self.write(
            LIVE,
            ticket(BEFORE.replace("One sentence saying what lands.", "Two sentences. The second one.")),
        )

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("one sentence", problems[0])

    def test_reads_a_wrapped_bullet_as_one_value(self) -> None:
        self.write(
            LIVE,
            ticket(BEFORE.replace("One sentence saying what lands.", "One sentence\n  saying what lands.")),
        )

        checked = self.checked()

        self.assertEqual([], checked.diagnostics)
        live = next(record for record in checked.records if record.record == LIVE)
        self.assertEqual("One sentence saying what lands.", live.fields["Outcome"])

    def test_with_a_link_that_does_not_resolve_is_reported(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("01-0001-earlier.md", "01-0001-elsewhere.md")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("01-0001-elsewhere.md", problems[0])

    def test_a_status_line_in_a_later_section_is_prose_not_header(self) -> None:
        self.write(
            LIVE,
            ticket(BEFORE, sections="## What to build\n\n**Status:** Accepted, as prose.\n\n"
                   "## Acceptance criteria\n\n- [ ] `/verify` has been run.\n"),
        )

        self.assertEqual([], self.problems())


class TheMark(Records):
    """A live ticket opens its header with what it is a record of, so the agent editing it meets
    the kind in context; the ticket format declares the kind, and the check holds the two equal."""

    def test_a_ticket_carrying_none_is_reported(self) -> None:
        self.write(LIVE, ticket(BEFORE, mark=""))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("names no kind", problems[0])
        self.assertEqual([(LIVE, 3)], self.problem_lines())

    def test_a_ticket_marked_with_another_kind_is_reported(self) -> None:
        self.write(LIVE, ticket(BEFORE, mark="- **record of** what happened\n"))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("what happened", problems[0])
        self.assertIn("what it intends to become", problems[0])

    def test_the_mark_under_its_former_name_is_reported_and_the_header_still_read(self) -> None:
        self.write(LIVE, ticket(BEFORE, mark="- **kind** what it intends to become\n"))

        problems = self.problems()

        self.assertEqual(1, len(problems), "the fields after it are read, so none goes missing")
        self.assertIn("`- **kind**`", problems[0])

    def test_is_told_from_the_retired_kind_field(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("- **Type:** HITL\n", "- **Type:** HITL\n- **Kind:** Maintenance\n")))

        problems = self.problems()

        self.assertEqual(1, len(problems), "the mark passes while the retired field is refused")
        self.assertIn("Kind is no longer a field", problems[0])

    def test_the_queue_carrying_none_is_reported(self) -> None:
        self.write(QUEUE, "# Delivery status\n\n**Candidate:** none.\n")

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("names no kind", problems[0])
        self.assertEqual([(QUEUE, 3)], self.problem_lines())

    def test_the_queue_marked_with_another_kind_is_reported(self) -> None:
        self.write(QUEUE, "# Delivery status\n\n- **record of** what exists\n\n**Candidate:** none.\n")

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("what exists", problems[0])

    def test_a_tree_without_a_queue_is_not_reported_for_it(self) -> None:
        (self.root / QUEUE).unlink()

        self.assertEqual([], self.problems())


class ThePlanBullet(Records):
    def test_absent_while_an_rfc_exists_is_reported(self) -> None:
        self.write(PLANNED, ticket(PLANNED_BEFORE.replace("- **Plan:** [plan](../rfc/01-0003-planned.md) — what it selected\n", "")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Plan", problems[0])
        self.assertIn(RFC, problems[0])

    def test_present_while_no_rfc_exists_is_reported(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("- **Minted:** 2026-09-08\n", "- **Minted:** 2026-09-08\n- **Plan:** [plan](../rfc/01-0002-live.md)\n")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Plan", problems[0])

    def test_pointing_at_another_file_than_the_rfc_is_reported(self) -> None:
        self.write(PLANNED, ticket(PLANNED_BEFORE.replace("../rfc/01-0003-planned.md", "./01-0002-live.md")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Plan", problems[0])
        self.assertIn(RFC, problems[0])


class TheSections(Records):
    def test_a_required_section_missing_is_reported(self) -> None:
        self.write(LIVE, ticket(BEFORE, sections="## Acceptance criteria\n\n- [ ] `/verify` run.\n"))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("What to build", problems[0])

    def test_a_provisional_heading_is_read_as_the_criteria_section(self) -> None:
        self.write(
            LIVE,
            ticket(BEFORE, sections="## What to build\n\nX.\n\n"
                   "## Acceptance criteria — provisional, firmed at the align\n\n- [ ] `/verify` run.\n"),
        )

        self.assertEqual([], self.problems())

    def test_a_ticket_minted_since_the_format_moved_holding_a_narrative_section_is_reported(self) -> None:
        self.write(LIVE, ticket(AFTER, sections="## Why this exists\n\nBecause.\n\n" + NAMED_FIVE))

        problems = self.problems()

        self.assertEqual(1, len(problems), problems)
        self.assertIn("`Why this exists`", problems[0])

    def test_a_ticket_minted_since_the_format_moved_may_hold_the_five_named_sections(self) -> None:
        self.write(LIVE, ticket(AFTER, sections=NAMED_FIVE))

        self.assertEqual([], self.problems())

    def test_a_ticket_minted_before_the_format_moved_is_not_reported_for_any_section(self) -> None:
        sections = (
            "## Why this exists\n\nBecause.\n\n## Decisions this ticket's align owns\n\n1. One.\n\n"
            "## Verification — 2026-09-08\n\nNotes.\n\n"
            "## What to build\n\nThe thing.\n\n## Acceptance criteria\n\n- [ ] `/verify` run.\n"
        )
        self.write(LIVE, ticket(BEFORE, sections=sections))
        self.write(PLANNED, ticket(PLANNED_BEFORE, sections=sections))

        self.assertEqual([], self.problems())

    def test_no_acceptance_box_naming_verify_is_reported_for_either_shape(self) -> None:
        for header in (BEFORE, AFTER):
            with self.subTest(header=header):
                self.write(LIVE, ticket(header, sections="## What to build\n\nX.\n\n## Acceptance criteria\n\n- [ ] It works.\n"))

                problems = self.problems()

                self.assertEqual(1, len(problems))
                self.assertIn("/verify", problems[0])

    def test_a_ticket_minted_since_the_format_moved_with_prose_among_its_criteria_is_reported(self) -> None:
        self.write(
            LIVE,
            ticket(AFTER, sections="## What to build\n\nX.\n\n## Acceptance criteria\n\n"
                   "Firmed at the align.\n\n- [ ] It works,\n  wrapped.\n- [x] `/verify` run.\n"),
        )

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("Firmed at the align.", problems[0])
        self.assertEqual([(LIVE, 17)], self.problem_lines(), "the mark's, the Minted and the Answers lines count")

    def test_a_ticket_minted_before_the_format_moved_may_hold_prose_among_its_criteria(self) -> None:
        self.write(
            PLANNED,
            ticket(PLANNED_BEFORE, sections="## What to build\n\nX.\n\n## Acceptance criteria\n\n"
                   "Provisional, firmed at the align.\n\n- [ ] `/verify` run.\n"),
        )

        self.assertEqual([], self.problems())


class WhenItWasMinted(Records):
    """A ticket says the day it was minted, and its shape is read from it: one minted before the
    format moved is held to the required sections and the `/verify` box alone (the user,
    2026-10-11)."""

    def test_a_ticket_without_minted_is_reported(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("- **Minted:** 2026-09-08\n", "")))

        self.assertEqual(["the header has no Minted bullet"], self.problems())

    def test_a_minted_that_is_no_date_is_reported(self) -> None:
        for written in ("last week", "2026-13-01", "2026-9-8"):
            with self.subTest(written=written):
                self.write(LIVE, ticket(BEFORE.replace("2026-09-08", written)))

                problems = self.problems()

                self.assertEqual(1, len(problems), problems)
                self.assertIn("Minted", problems[0])
                self.assertIn("YYYY-MM-DD", problems[0])

    def test_minted_out_of_order_is_reported(self) -> None:
        self.write(
            LIVE,
            ticket(BEFORE.replace("- **Minted:** 2026-09-08\n", "").replace("- **Outcome:**", "- **Minted:** 2026-09-08\n- **Outcome:**")),
        )

        problems = self.problems()

        self.assertEqual(1, len(problems), problems)
        self.assertIn("Minted", problems[0])

    def test_the_record_says_when_it_was_minted(self) -> None:
        records = {read.record: read.as_record() for read in self.checked().records}

        self.assertEqual("2026-09-08", records[LIVE]["minted"])
        self.assertNotIn("stage", records[LIVE])


class TheQuestionItAnswers(Records):
    """A ticket names the question its goal answers by one link to a store entry it owns, and its
    open questions live under that entry, never in a section of its own (the user,
    2026-10-03)."""

    def raw(self, answers: str | None, sections: str | None = None) -> None:
        header = BEFORE if answers is None else BEFORE.replace(
            "- **Outcome:**", f"- **Answers:** {answers}\n- **Outcome:**"
        )
        self.write_raw(LIVE, ticket(header) if sections is None else ticket(header, sections))

    def test_a_ticket_without_one_is_reported(self) -> None:
        self.raw(None)

        self.assertEqual(["the header has no Answers bullet"], self.problems())

    def test_a_link_that_resolves_to_nothing_is_reported_once(self) -> None:
        self.raw("[q-0009](../questions/q-0009-gone.md)")

        problems = self.problems()

        self.assertEqual(1, len(problems), problems)
        self.assertIn("does not resolve", problems[0])

    def test_a_link_to_a_file_that_is_not_an_entry_is_reported(self) -> None:
        self.raw("[earlier](./01-0001-earlier.md)")

        self.assertEqual(["Answers links ./01-0001-earlier.md, which is not an entry of the store"], self.problems())

    def test_an_entry_owned_by_another_record_is_reported(self) -> None:
        theirs = self.questions["docs/tickets/01-0001-earlier.md"]
        self.raw(f"[q-0001](../questions/{theirs})")

        self.assertEqual(["Answers links q-0001, whose owner is not this ticket"], self.problems())

    def test_an_open_issues_section_is_reported_in_every_ticket(self) -> None:
        sections = (
            "## What to build\n\nThe thing.\n\n## Open issues\n\n- One.\n\n"
            "## Acceptance criteria\n\n- [ ] `/verify` has been run.\n"
        )
        self.write(LIVE, ticket(BEFORE, sections))
        self.write(PLANNED, ticket(PLANNED_BEFORE, sections))

        problems = self.problems()

        self.assertEqual(2, len(problems), problems)
        self.assertTrue(all("Open issues" in problem for problem in problems), problems)


class Pairing(Records):
    def test_a_live_rfc_whose_ticket_is_archived_is_reported(self) -> None:
        self.write("docs/tickets/done/01-0003-planned.md", self.read(PLANNED))
        (self.root / PLANNED).unlink()

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn(RFC, problems[0])
        self.assertIn("done", problems[0])

    def test_an_archived_rfc_whose_ticket_is_live_is_reported(self) -> None:
        self.write("docs/rfc/done/01-0003-planned.md", self.read(RFC))
        (self.root / RFC).unlink()
        self.write(PLANNED, ticket(PLANNED_BEFORE.replace("../rfc/", "../rfc/done/")))

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("docs/rfc/done/01-0003-planned.md", problems[0])

    def test_an_rfc_naming_no_ticket_is_reported(self) -> None:
        self.write("docs/rfc/01-0009-orphan.md", "# Orphan — implementation plan\n")

        problems = self.problems()

        self.assertEqual(1, len(problems))
        self.assertIn("docs/rfc/01-0009-orphan.md", problems[0])
        self.assertIn("no ticket", problems[0])

    def test_a_closed_pair_is_matched_by_name_and_never_opened(self) -> None:
        self.write("docs/tickets/done/01-0004-closed.md", "**Status:** bare, and never read\n")
        self.write("docs/rfc/done/01-0004-closed.md", b"\xff\xfe not even text".decode("latin-1"))

        self.assertEqual([], self.problems())
        self.assertEqual([], self.checked().skipped)


class AnUnreadableRecord(Records):
    def test_is_skipped_with_its_reason_and_fails_the_run(self) -> None:
        (self.root / LIVE).write_bytes(b"\xff\xfe\x00 not utf-8")

        checked = self.checked()

        self.assertEqual([], checked.diagnostics)
        self.assertEqual(1, len(checked.skipped))
        self.assertEqual(LIVE, checked.skipped[0].record)
        self.assertIn("UTF-8", checked.skipped[0].why)

    def test_without_a_title_line_is_skipped_rather_than_misread(self) -> None:
        self.write(LIVE, "Not a title\n\n- **Status:** Ready\n")

        checked = self.checked()

        self.assertEqual(1, len(checked.skipped))
        self.assertIn("title", checked.skipped[0].why)


class TheCommandLine(Records):
    def invoke(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = tickets.main(list(argv), self.root)
        return status, out.getvalue()

    def test_refuses_a_bare_invocation_rather_than_choosing_a_mode(self) -> None:
        status, out = self.invoke()

        self.assertEqual(2, status)
        self.assertIn("usage", out)

    def test_reports_a_clean_tree_with_a_zero_status_and_its_records(self) -> None:
        status, out = self.invoke("--check")

        self.assertEqual(0, status)
        report = json.loads(out)
        self.assertEqual([], report["diagnostics"])
        self.assertEqual(3, len(report["records"]))

    def test_reports_a_violation_with_file_line_and_rule_and_a_non_zero_status(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("Ready", "Nearly")))

        status, out = self.invoke("--check")

        self.assertEqual(1, status)
        diagnostics = json.loads(out)["diagnostics"]
        self.assertEqual(1, len(diagnostics))
        note = diagnostics[0]
        self.assertEqual(LIVE, note["record"])
        self.assertEqual(4, note["line"], "the Status line, after the mark")
        self.assertIn("Nearly", note["problem"])

    def test_a_skip_alone_fails_the_run(self) -> None:
        (self.root / LIVE).write_bytes(b"\xff\xfe\x00")

        status, out = self.invoke("--check")

        self.assertEqual(1, status)
        self.assertEqual(1, len(json.loads(out)["skipped"]))

    def test_refuses_a_flag_it_does_not_know(self) -> None:
        status, out = self.invoke("--lists")

        self.assertEqual(2, status)
        self.assertIn("--list", out)


class TheList(Records):
    """The live tickets as their headers say, rendered on request and never copied (the user,
    2026-10-10): id, slug, status word, type, title and the question each answers."""

    def listed(self) -> tuple[int, list[str], list[str]]:
        """The exit status, the table's rows, and every other line printed after the table."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = tickets.main(["--list"], self.root)
        lines = out.getvalue().splitlines()
        rows = [line for line in lines if line.startswith("| [")]
        after = [line for line in lines if line and not line.startswith("|")]
        return status, rows, after

    def test_names_every_live_ticket_in_id_order_with_the_question_it_answers(self) -> None:
        self.write("docs/tickets/01-0002.0010-child.md", ticket(BEFORE, title="# A child"))
        self.write("docs/tickets/done/01-0000-closed.md", ticket(BEFORE, title="# Closed"))

        status, rows, after = self.listed()

        self.assertEqual(0, status)
        self.assertEqual([], after)
        self.assertEqual(
            [
                "| [01-0001 earlier](docs/tickets/01-0001-earlier.md) | Ready | HITL | A ticket | "
                "[q-0001 what-is-it-for](docs/questions/q-0001-what-is-it-for.md) |",
                "| [01-0002 live](docs/tickets/01-0002-live.md) | Ready | HITL | A ticket | "
                "[q-0002 what-is-it-for](docs/questions/q-0002-what-is-it-for.md) |",
                "| [01-0002.0010 child](docs/tickets/01-0002.0010-child.md) | Ready | HITL | A child | "
                "[q-0004 what-is-it-for](docs/questions/q-0004-what-is-it-for.md) |",
                "| [01-0003 planned](docs/tickets/01-0003-planned.md) | In progress | AFK | A ticket | "
                "[q-0003 what-is-it-for](docs/questions/q-0003-what-is-it-for.md) |",
            ],
            rows,
        )

    def test_shows_the_status_word_and_leaves_its_qualifier_in_the_ticket(self) -> None:
        self.write(LIVE, ticket(BEFORE.replace("Ready", "Ready (aligned 2026-09-08)")))

        _, rows, _ = self.listed()

        self.assertIn("| [01-0002 live](docs/tickets/01-0002-live.md) | Ready | HITL |", rows[1])
        self.assertNotIn("aligned", rows[1])

    def test_an_edited_ticket_shows_in_the_next_list_with_no_other_edit(self) -> None:
        _, before, _ = self.listed()
        self.write(LIVE, ticket(BEFORE.replace("Ready", "Blocked"), title="# Renamed"))

        _, after, _ = self.listed()

        self.assertIn("| Ready | HITL | A ticket |", before[1])
        self.assertIn("| Blocked | HITL | Renamed |", after[1])

    def test_a_field_the_header_lacks_prints_a_dash_and_the_list_goes_on(self) -> None:
        self.write_raw(LIVE, ticket("- **Status:** Ready\n- **Outcome:** One sentence.\n"))

        status, rows, _ = self.listed()

        self.assertEqual(0, status)
        self.assertEqual(3, len(rows))
        self.assertEqual("| [01-0002 live](docs/tickets/01-0002-live.md) | Ready | — | A ticket | — |", rows[1])

    def test_a_bar_in_a_title_cannot_break_its_row(self) -> None:
        self.write(LIVE, ticket(BEFORE, title="# Either | or"))

        _, rows, _ = self.listed()

        self.assertIn("| Either \\| or |", rows[1])

    def test_a_ticket_it_cannot_read_is_named_under_the_table_and_fails_the_run(self) -> None:
        self.write(LIVE, "Not a title\n\n- **Status:** Ready\n")

        status, rows, after = self.listed()

        self.assertEqual(1, status)
        self.assertEqual(2, len(rows))
        self.assertEqual(1, len(after))
        self.assertIn(LIVE, after[0])
        self.assertIn("title", after[0])


if __name__ == "__main__":
    unittest.main()
