#!/usr/bin/env python3
"""Extract per-provision plain-text files from the legislation.gov.uk CLML data.xml
for SI 2010/2214 (Building Regulations 2010), current version as served.

Structure (CLML): Body > Part > (Chapter|P1group) > P1 (= regulation).
P1/P2/P3/P4/P5 are nested numbered paragraphs (Pnumber). Regulation headings live
on the enclosing P1group/Title (or P1/Title). Where a regulation differs between
England and Wales, the England text is inline (Concurrent=true, RestrictExtent=E)
and the Wales text is stored in root Versions/Version, linked by AltVersionRefs;
both are emitted, the Wales text appended under a labelled separator.
Commentary (amendment annotations) is editorial and skipped.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

L = '{http://www.legislation.gov.uk/namespaces/legislation}'
X = '{http://www.w3.org/1999/xhtml}'
M = '{http://www.legislation.gov.uk/namespaces/metadata}'
FETCH_DATE = '2026-10-04'
SI = 'SI 2010/2214'
BASE = 'https://www.legislation.gov.uk/uksi/2010/2214'

SKIP_TAGS = {L + 'Commentary', L + 'CommentaryRef', L + 'MarginNote', L + 'Amendment'}

def text_of(el):
    """itertext excluding skipped annotation subtrees; tables inline as rows."""
    out = []
    def walk(e):
        if e.tag in SKIP_TAGS:
            return
        if e.tag in (X + 'table', L + 'Tabular'):
            rows = table_rows(e)
            if rows:
                out.append(' ' + ' | '.join(rows) + ' ')
            return
        if e.tag in (X + 'img',):
            return
        if e.text:
            out.append(e.text)
        for c in e:
            walk(c)
            if c.tail:
                out.append(c.tail)
    walk(el)
    return ''.join(out)

def norm(s):
    s = re.sub(r'\s+', ' ', s.replace('\xa0', ' ')).strip()
    return re.sub(r' +([,;])', r'\1', s)

def pnum(el):
    n = el.find(L + 'Pnumber')
    if n is None:
        n = el.find(L + 'Number')
    return norm(''.join(n.itertext())) if n is not None else ''

def title_of(el):
    t = el.find(L + 'Title')
    if t is None:
        return ''
    return norm(''.join(t.itertext()))

def heading_text(el):
    """Heading only: text of a Title element excluding P blocks (a Title that
    contains P blocks carries unnumbered provision content, not a heading)."""
    t = el.find(L + 'Title')
    if t is None:
        return ''
    parts = []
    for ch in t:
        if ch.tag == L + 'P':
            continue
        txt = norm(''.join(ch.itertext()))
        if txt:
            parts.append(txt)
    if not parts and len(t) == 0 and (t.text or '').strip():
        return norm(t.text)
    return ' '.join(parts)

def label(num):
    """Pnumber -> display label: 1 -> 1., a -> (a), i -> (i)."""
    if not num:
        return ''
    if re.fullmatch(r'\d+[A-Z]?', num):
        return num.rstrip('.') + '.'
    return f'({num.rstrip(".")})'

def table_rows(tbl):
    """Rows of an xhtml table (or CLML Tabular); each cell's block children
    joined with spaces, cells joined with ' | '."""
    rows = []
    trs = list(tbl.findall(X + 'tr')) + list(tbl.findall(X + 'tbody/' + X + 'tr')) \
        + list(tbl.findall(X + 'thead/' + X + 'tr'))
    if not trs:
        trs = list(tbl.iter(X + 'tr'))
    for tr in trs:
        cells = []
        for td in tr:
            if td.tag not in (X + 'td', X + 'th'):
                continue
            parts = []
            for ch in td:
                if ch.tag in SKIP_TAGS:
                    continue
                t = norm(text_of(ch))
                if t:
                    parts.append(t)
            if not parts:
                t = norm(text_of(td))
                if t:
                    parts.append(t)
            t = ' '.join(parts)
            if t:
                cells.append(t)
        if cells:
            rows.append(' | '.join(cells))
    return rows

def render_table(tbl, out):
    for r in table_rows(tbl):
        out.append(r)

def render_para_content(para, out, depth=0, lab=None):
    """Render the children of a P{n}para in document order:
    inline text (first run picks up the paragraph number label), nested
    P{n+1} blocks, lists and tables."""
    indent = '    ' * max(0, depth)
    first_text = True
    for ch in para:
        tag = ch.tag
        if tag in (L + 'P1', L + 'P2', L + 'P3', L + 'P4', L + 'P5'):
            render_pblock(ch, out, depth + 1)
        elif tag in (X + 'table', L + 'Tabular'):
            render_table(ch, out)
        elif tag in (L + 'UnorderedList', L + 'OrderedList'):
            for li in ch.findall(L + 'ListItem'):
                t = norm(text_of(li))
                if t:
                    out.append(indent + '- ' + t)
        elif tag in SKIP_TAGS:
            continue
        else:
            t = norm(text_of(ch))
            if t and t != '\x00TABLE\x00':
                prefix = (lab + ' ') if (first_text and lab) else ''
                out.append(indent + prefix + t)
                first_text = False
                lab = None

def render_pblock(p, out, depth=0):
    """Render a P1..P5 block: its number label, optional heading, then content."""
    n = p.tag[-1]
    indent = '    ' * depth
    lab = label(pnum(p))
    head = heading_text(p)
    para = p.find(L + f'P{n}para')
    if head:
        out.append(indent + (lab + ' ' if lab else '') + head)
    if para is None or len(para) == 0:
        if lab and not head:
            # repealed/omitted provision keeps its number marker only
            out.append(indent + lab)
        return
    render_para_content(para, out, depth, lab=None if head else lab)

def reg_num(p):
    return pnum(p).rstrip('.')

def reg_slug(num):
    m = re.fullmatch(r'(\d+)([A-Z]*)', num)
    if m:
        return f"reg-{int(m.group(1)):02d}{m.group(2).lower()}"
    return 'reg-' + re.sub(r'[^A-Za-z0-9]', '-', num).lower()

def flags(el):
    f = {}
    for k in ('RestrictExtent', 'RestrictStartDate', 'Status', 'Concurrent', 'AltVersionRefs'):
        if el.attrib.get(k):
            f[k] = el.attrib[k]
    return f

def main(src, outdir):
    tree = ET.parse(src)
    root = tree.getroot()
    body = root.find('.//' + L + 'Body')
    schedules_el = root.find('.//' + L + 'Schedules')

    # Wales variants: id -> element (first P1 inside)
    versions = {}
    for v in root.findall(L + 'Versions/' + L + 'Version'):
        p1 = v.find('.//' + L + 'P1')
        if p1 is not None:
            versions[v.attrib.get('id')] = v

    os.makedirs(os.path.join(outdir, 'regs'), exist_ok=True)
    os.makedirs(os.path.join(outdir, 'schedules'), exist_ok=True)
    os.makedirs(os.path.join(outdir, 'parts'), exist_ok=True)
    os.makedirs(os.path.join(outdir, 'misc'), exist_ok=True)

    manifest = []
    seen = {}

    def emit_reg(p1, part_label, part_title, group, chapter=None):
        num = reg_num(p1)
        uri_tail = (p1.attrib.get('DocumentURI') or '').rstrip('/').rsplit('/', 1)[-1]
        slug = reg_slug(num)
        if slug in seen:
            seen[slug] += 1
            # same number twice (e.g. 44ZB and later-inserted 44ZBn1): fall
            # back to the canonical legislation.gov.uk path segment
            slug = 'reg-' + re.sub(r'[^A-Za-z0-9]', '-', uri_tail.lower())
            if slug in seen:
                seen[slug] += 1
                slug = f'{slug}-{seen[slug]}'
            else:
                seen[slug] = 1
        else:
            seen[slug] = 1
        title = heading_text(p1) or heading_text(group) or (chapter and chapter[1]) or ''
        gflags = flags(group)
        lines = []
        para = p1.find(L + 'P1para')
        if para is not None:
            render_para_content(para, lines, -1)
        p1flags = flags(p1)
        allflags = {**gflags, **p1flags}
        head = [
            f'Regulation {num}' + (f' — {title}' if title else ''),
            f'Building Regulations 2010 ({SI}), current version as served by legislation.gov.uk, fetched {FETCH_DATE}',
            f'{part_label}' + (f' — {part_title}' if part_title else ''),
            f'Source: {BASE}/regulation/{uri_tail}',
        ]
        notes = []
        if allflags.get('RestrictStartDate'):
            notes.append(f"in force from {allflags['RestrictStartDate']}")
        ext = allflags.get('RestrictExtent')
        if ext:
            notes.append(f"extent {ext.replace('+', ' and ')}")
        if allflags.get('Status'):
            notes.append(f"status: {allflags['Status']}")
        wales_id = allflags.get('AltVersionRefs')
        if wales_id and wales_id in versions:
            head.append('This regulation has a different Wales version; it is appended below '
                        '(the inline text above is the England version).')
        if notes:
            head.append('XML metadata: ' + '; '.join(notes))
        body_txt = '\n'.join(x for x in lines if x.strip())
        text = '\n'.join(head) + '\n\n' + body_txt + '\n'
        if wales_id and wales_id in versions:
            wv = versions[wales_id]
            wp1 = wv.find('.//' + L + 'P1')
            wlines = []
            wpara = wp1.find(L + 'P1para')
            if wpara is not None:
                render_para_content(wpara, wlines, -1)
            wl = ['', '--- ALTERNATIVE VERSION — applies in Wales only (XML Version container '
                 f'"{wales_id}", RestrictExtent W) ---', '']
            wl.extend(wlines)
            wl.append('')
            wl.append(f'Source (Wales version): {BASE}/regulation/{num}/wales')
            text += '\n'.join(wl) + '\n'
        path = f'regs/{slug}.txt'
        with open(os.path.join(outdir, path), 'w', encoding='utf-8') as f:
            f.write(text)
        manifest.append((path, num, title, part_label))

    part_files = []
    for part in body.findall(L + 'Part'):
        pnum_txt = norm(''.join(part.find(L + 'Number').itertext()))
        ptitle = heading_text(part)
        plabel = pnum_txt.title() if pnum_txt.isupper() else pnum_txt
        part_lines = [
            f'{pnum_txt}' + (f' — {ptitle}' if ptitle else ''),
            f'Building Regulations 2010 ({SI}), current version, fetched {FETCH_DATE}',
            f'Source: {BASE}/part/{pnum_txt.split()[-1].lower()}',
            '',
            'Index of provisions in this Part (files under regs/):',
            '',
        ]
        entries = []          # interleaved index rows: ('chapter'|'reg', text)

        def walk_containers(container):
            """Document-order walk through Pblock/Chapter nesting."""
            for ch in container:
                if ch.tag == L + 'Chapter':
                    cnum = norm(''.join(ch.find(L + 'Number').itertext())) if ch.find(L + 'Number') is not None else ''
                    ctitle = heading_text(ch)
                    entries.append(('chapter', f'{cnum} — {ctitle}'.strip(' —')))
                    walk_containers(ch)
                elif ch.tag in (L + 'Pblock', L + 'Pblocks'):
                    walk_containers(ch)
                elif ch.tag == L + 'P1group':
                    for p1 in ch.findall(L + 'P1'):
                        emit_reg(p1, pnum_txt, ptitle, ch)
                        entries.append(('reg', pnum(p1).rstrip('.'), heading_text(p1) or heading_text(ch), flags(ch)))
                elif ch.tag == L + 'P1':
                    emit_reg(ch, pnum_txt, ptitle, container if container.tag == L + 'P1group' else part)
                    entries.append(('reg', pnum(ch).rstrip('.'), title_of(ch) or ptitle,
                                    flags(container if container.tag == L + 'P1group' else part)))

        walk_containers(part)
        for e in entries:
            if e[0] == 'chapter':
                part_lines.append(e[1])
            else:
                _, num, ttl, fl = e
                note = ''
                if fl.get('AltVersionRefs'):
                    note += ' [England text; Wales variant appended in file]'
                if fl.get('Status') == 'Repealed':
                    note += ' [repealed]'
                part_lines.append(f'  reg {num}: {ttl}{note}')
        slug = 'part-' + re.sub(r'[^A-Za-z0-9]+', '-', pnum_txt.lower().replace('part', '', 1)).strip('-')
        path = f'parts/{slug}.txt'
        with open(os.path.join(outdir, path), 'w', encoding='utf-8') as f:
            f.write('\n'.join(part_lines) + '\n')
        part_files.append((path, pnum_txt, ptitle, len(entries)))

    # schedules
    sched_files = []
    for s in schedules_el.findall(L + 'Schedule'):
        snum = norm(''.join(s.find(L + 'Number').itertext())) if s.find(L + 'Number') is not None else ''
        tblock = s.find(L + 'TitleBlock')
        stitle = norm(''.join(tblock.itertext())) if tblock is not None else ''
        stitle = re.sub(r'^Schedule\s*\S+\s*', '', stitle, flags=re.I).strip() or stitle
        sflags = flags(s)
        lines = []

        def render_sched_container(ch):
            """A Part (CLASS) or P1group inside a schedule: heading line, then
            its P1s (direct, and those inside nested P1groups), in order."""
            t = heading_text(ch)
            n = pnum(ch)
            if t or n:
                lines.append(f'{n} — {t}'.strip(' —'))
            for sub in ch:
                if sub.tag == L + 'P1':
                    render_pblock(sub, lines, 0)
                elif sub.tag == L + 'P1group':
                    render_sched_container(sub)
                elif sub.tag in (X + 'table', L + 'Tabular'):
                    render_table(sub, lines)
                elif sub.tag == L + 'Title':
                    # unnumbered provision content inside a Title
                    for p in sub.findall(L + 'P'):
                        render_para_content(p, lines, 0)
                elif sub.tag == L + 'P':
                    # unnumbered paragraph directly under the container
                    render_para_content(sub, lines, 0)

        for ch in s.find(L + 'ScheduleBody'):
            if ch.tag == L + 'P1':
                render_pblock(ch, lines, 0)
            elif ch.tag in (L + 'P1group', L + 'Part'):
                render_sched_container(ch)
            elif ch.tag in (X + 'table', L + 'Tabular'):
                render_table(ch, lines)
            else:
                t = norm(text_of(ch))
                if t:
                    lines.append(t)
        short = snum.replace('SCHEDULE', '').strip().lower().replace(' ', '-')
        path = f'schedules/sched-{short}.txt'
        head = [
            f'{snum}' + (f' — {stitle}' if stitle else ''),
            f'Building Regulations 2010 ({SI}), current version, fetched {FETCH_DATE}',
            f'Source: {BASE}/schedule/{short.upper()}',
        ]
        notes = []
        if sflags.get('Status'):
            notes.append(f"status: {sflags['Status']}")
        if sflags.get('RestrictStartDate'):
            notes.append(f"in force from {sflags['RestrictStartDate']}")
        if sflags.get('RestrictExtent'):
            notes.append(f"extent {sflags['RestrictExtent']}")
        if notes:
            head.append('XML metadata: ' + '; '.join(notes))
        with open(os.path.join(outdir, path), 'w', encoding='utf-8') as f:
            f.write('\n'.join(head) + '\n\n' + '\n'.join(x for x in lines if x.strip()) + '\n')
        sched_files.append((path, snum, stitle, sflags.get('Status')))

    # signed section
    signed = body.find(L + 'SignedSection')
    if signed is not None:
        lines = []
        sst = signed.find(L + 'SignedSectionText')
        if sst is not None:
            render_para_content(sst, lines, 0)
        for sp in signed.findall(L + 'Signatory'):
            for ch in sp:
                if ch.tag == L + 'Signee':
                    for sub in ch:
                        t = norm(text_of(sub))
                        if t:
                            lines.append(t)
                else:
                    t = norm(text_of(ch))
                    if t:
                        lines.append(t)
        with open(os.path.join(outdir, 'misc/signature.txt'), 'w', encoding='utf-8') as f:
            f.write(f'Signature block\nBuilding Regulations 2010 ({SI})\nSource: {BASE}\n\n' + '\n'.join(lines) + '\n')

    print('parts:', len(part_files))
    for p in part_files:
        print('  ', p)
    print('schedules:', len(sched_files))
    for s in sched_files:
        print('  ', s)
    print('regs emitted:', len(manifest), 'unique slugs:', len(set(m[0] for m in manifest)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
