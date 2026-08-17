# Controlled Real-Data Ingestion Runbook

This runbook registers the operational checks, ingestion commands, and validation loops for executing a controlled real-data load.

---

## 1. Pre-Load Checklists
*   [ ] Verify Gate 4 dry-run verification loops have achieved "Ready" status.
*   [ ] Confirm AES-256 staging partition permissions are active.
*   [ ] Validate that target directories in `data/real_*` contain only `.gitkeep` files.
*   [ ] Verify the target ingestion file name matches standard regex rules.
*   [ ] Obtain the final written CISO and CHRO signoff token.
*   [ ] Confirm scheduling window parameters defined in [CONTROLLED_LOAD_SCHEDULING_REQUIREMENTS.md](file:///c:/tmp/HR-DASHBOARD/docs/CONTROLLED_LOAD_SCHEDULING_REQUIREMENTS.md) are met.

---

## 2. Ingestion Execution
*   **Step 1**: Place the inbound file in `data/real_inbox/`.
*   **Step 2**: Trigger the schema validator to scan column counts, delimiters, and formats.
*   **Step 3**: Verify control totals and run the no-real-data validation checks.
*   **Step 4**: Trigger view generation to compile canonical DuckDB schema updates.

---

## 3. Post-Load Checks
*   [ ] Validate headcount sums and record counts against source totals.
*   [ ] Run masking audits on employee identity, salaries, and candidate keys.
*   [ ] Check audit logs to confirm that view accesses were registered.
*   [ ] Archive source files under `data/real_archive/`.

## 4. Attendance — the coverage declaration is the only guard

**Read this before asking a client for an attendance file.**

Attendance is the only date-grained domain. The commit refuses it without
`coverage_start` and `coverage_end`, and **that declaration is the only thing
standing between the client and thousands of fabricated absences.**

### 4.1 What a wrong declaration does

Inside the declared window, a working day with no row **is an absence**. That
inversion is deliberate and it is what makes the absence figure honest — a
client who genuinely did not report a day gets a real absence rather than a
silent gap.

The consequence, stated plainly:

> **Declare a window wider than the data and the system manufactures one
> absence per employee per uncovered working day — each indistinguishable from
> a real one.** At this client's headcount that is thousands of fabricated
> absences, and nothing downstream can tell them apart.

Outside the declared window the same day is NULL — *not measured* — and every
sum, count and average skips it. So the difference between a correct
declaration and a wide one is the difference between "we have no data for
those days" and "everyone was absent".

### 4.2 What the operator must do

1. **Establish the export's true date span before declaring.** Open the file
   and read the minimum and maximum `attendance_date`. Do not infer it from the
   month, the filename, or what the client said on a call.
2. **Declare exactly that span.** Not the calendar month, unless the file
   genuinely covers the calendar month.
3. **Expect a hard stop if they disagree.** A row outside the declared window
   aborts the run and names the offending dates. That is the gate working, not
   a broken upload — re-declare to match the file, or ask the client for the
   missing days.
4. **A partial upload is normal.** One week of a month is a legitimate load.
   The coverage note tells the client how much of the period they vouched for,
   and the figures stay honest because the rest is NULL rather than zero.

### 4.3 Tell the client this before they upload

**Attendance and payroll unlock each other's exception surfaces.** Loading
attendance alone lights up the attendance KPIs and the coverage note, but
**the Attendance exceptions page stays empty** — it reconciles against payroll.

*"I sent you attendance and the attendance page is still empty"* is the
reasonable complaint, and it should be pre-empted rather than answered.

### 4.4 If the client has no rostering system

Lateness is measured against a schedule. With no `scheduled_start`, lateness is
**withheld rather than reported as zero** — the client will see no lateness
figures and no attendance-compliance percentage, and that is correct: those
figures have nothing to measure against. Punches, missing punches and absences
still work.

Do not read the withheld figures as a failed load.

