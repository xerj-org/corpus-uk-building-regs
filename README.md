# corpus-uk-building-regs — UK Building Regulations 2010 (SI 2010/2214)

Per-provision plain-text mirror of the **Building Regulations 2010 (SI 2010/2214)**,
current version as served by legislation.gov.uk. Built for the XERJ corpus hub.

- **Source document:** https://www.legislation.gov.uk/uksi/2010/2214 — machine lane
  `https://www.legislation.gov.uk/uksi/2010/2214/data.xml` (CLML XML, one file for the
  whole SI; 3,263,306 bytes as fetched).
- **Fetched:** 2026-10-04. Regenerate with `python3 tools/extract.py _src/data.xml .`
  (fetch the XML into `_src/` first; `_src/` is not committed).
- **Scope:** the Statutory Instrument itself — its Parts, regulations and Schedules,
  as currently in force/amended. This is **NOT** the Approved Documents (the guidance
  documents A–S published separately by DLUHC/Welsh Government that set out how to
  comply with Schedule 1 requirements). Approved Documents are explicitly out of scope
  for this mirror.

## Layout

| Directory | Files | Contents |
|---|---|---|
| `regs/` | 170 | one file per regulation, e.g. `reg-04.txt`, `reg-14za.txt`, `reg-44zbn1.txt` |
| `schedules/` | 8 | `sched-1.txt` … `sched-6.txt`, `sched-3a.txt`, `sched-4a.txt` (whole schedule per file, with paragraph numbering) |
| `parts/` | 15 | `part-1.txt` … `part-10.txt`, incl. `part-2a.txt`, `part-2b-wales.txt`, `part-7a.txt`, `part-9a.txt`, `part-9b.txt` — index files listing each Part's regulations and chapters |
| `misc/` | 1 | `signature.txt` (the SI's signed-section / signatory block) |

Each regulation file header carries: regulation number and heading, SI reference,
the Part (and Chapter) it sits in, the canonical legislation.gov.uk per-provision
URL, and XML metadata (in-force date, extent, repeal status) where present.

## Notes on fidelity (read before using)

- **Version:** this is the "current" (point-in-time as served at fetch date) version.
  Several 2025–2026 amendments have commencement dates close to the fetch date; each
  file header records the `RestrictStartDate` the XML carries for that provision.
- **England/Wales divergence:** where a regulation has different text for England and
  Wales, legislation.gov.uk's XML stores the England text inline (extent E) and the
  Wales text in a separate alternative-version container. Both are kept: the England
  text is the file body, and the Wales text is appended under a
  `--- ALTERNATIVE VERSION — applies in Wales only ---` separator (27 regulations).
  Part 2B ("Dutyholders and competence — Wales") is a separate Part in the SI and has
  its own regulation files.
- **Duplicate numbers:** two provisions numbered 44ZB (and 44ZC) exist in Part 9A
  (inserted at different dates by different amending SIs); the later one is filed as
  `reg-44zbn1.txt` / `reg-44zc...n1`, matching its canonical URL.
- **Repealed material:** Schedules 4A and 5 are repealed; they remain in the source
  XML and in this mirror, flagged in the file header (`status: Repealed`).
- **Editorial annotations** (CLML `Commentary` amendment notes, F-notes) are skipped;
  they are editorial apparatus, not law. Pagination and the `TABLE` layout artefacts
  of the source are normalised; tables render as `cell | cell` rows.

## Licence

UK **Open Government Licence v3.0**. Verified at fetch time:
- Site reuse statement (footer of every legislation.gov.uk page, checked on
  https://www.legislation.gov.uk/uksi/2010/2214/contents):
  *"All content is available under the Open Government Licence v3.0 except where
  otherwise stated. … © Crown and database right"*
  (the footer also notes the site reuses some EUR-Lex-derived content under
  Commission Decision 2011/833/EU — not relevant to this SI).
- OGL v3.0 licence text: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
- Note: the classic reuse-statement page `https://www.legislation.gov.uk/about`
  returned 404 at fetch time; the per-page footer statement above is the operative
  reuse statement actually served with the document.

Content: © Crown copyright, licensed under OGL v3.0. This mirror attributes the
source and records provenance per file; it makes no additional claim on the text.
