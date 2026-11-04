"""
scripts/build_drawio_diagrams.py
Generates native, editable draw.io XML (.drawio) files from Mermaid (.mmd) architecture diagrams.
Compatible with diagrams.net / draw.io desktop and web apps.
Standardized for AI for BI Enterprise Architecture Documentation.
"""

import os
import re
import html
import xml.etree.ElementTree as ET
from pathlib import Path

# Standardized color scheme according to Enterprise Architectural Review standards
COLOR_MAP = {
    'frontend': ('#e1f5fe', '#0288d1', '#01579b'),     # Light Blue
    'gateway': ('#ede7f6', '#5e35b1', '#311b92'),      # Purple
    'orchestration': ('#e8eaf6', '#3949ab', '#1a237e'),# Indigo / Deep Purple
    'analytics': ('#fff3e0', '#f57c00', '#e65100'),    # Orange / Amber
    'retrieval': ('#e0f2f1', '#00897b', '#004d40'),    # Teal / Cyan
    'data': ('#e8f5e9', '#43a047', '#1b5e20'),         # Green
    'external': ('#fce4ec', '#d81b60', '#880e4f'),     # Pink / Red
    'security': ('#eceff1', '#546e7a', '#263238'),     # Grey / Slate
    'default': ('#f5f5f5', '#757575', '#212121')
}

def determine_category(nid, lbl):
    low = (nid + " " + lbl).lower()
    if any(k in low for k in ['client', 'browser', 'ui', 'frontend', 'screen', 'view', 'input', 'deck', 'stepper', 'shell', 'user', 'actor', 'analyst']):
        return 'frontend'
    elif any(k in low for k in ['api', 'gateway', 'router', 'sse', 'middleware', 'cors', 'rest']):
        return 'gateway'
    elif any(k in low for k in ['supervisor', 'orchestrat', 'specialist', 'dag', 'planner', 'agent', 'intent', 'memory', 'session', 'handoff']):
        return 'orchestration'
    elif any(k in low for k in ['retriev', 'embed', 'bm25', 'lance', 'rrf', 'graph', 'corpus', 'fusion', 'linker', 'semantic layer']):
        return 'retrieval'
    elif any(k in low for k in ['engine', 'diagnostic', 'forecast', 'predictive', 'scenario', 'prescriptive', 'impact', 'churn', 'critic', 'faithfulness', 'statistical']):
        return 'analytics'
    elif any(k in low for k in ['warehouse', 'database', 'adapter', 'sql', 'ast', 'postgres', 'sqlite', 'mysql', 'catalog', 'store', 'volume', 'fingerprint', 'cache']):
        return 'data'
    elif any(k in low for k in ['groq', 'cloud', 'lpu', 'llm', 'inference', 'external', 'foundation']):
        return 'external'
    elif any(k in low for k in ['security', 'observability', 'tracer', 'audit', 'token', 'latency', 'telemetry', 'guard', 'redaction', 'span']):
        return 'security'
    return 'default'

def parse_mmd_flowchart(mmd_text):
    """Robust parser extracting nodes, node shapes, edges, and subgraphs from Mermaid flowchart."""
    nodes = {}        # nid -> label
    node_shapes = {}  # nid -> 'rectangle' | 'cylinder' | 'rhombus'
    edges = []        # list of dicts: src, dst, label, dashed, bidi
    subgraphs = []
    subgraph_stack = []

    lines = mmd_text.splitlines()
    for line in lines:
        s = line.strip()
        if not s or s.startswith('%%') or s.startswith('flowchart') or s.startswith('direction') or s.startswith('classDef') or s.startswith('class '):
            continue

        # Subgraph start
        sub_match = re.match(r'subgraph\s+([A-Za-z0-9_]+)\["?(.*?)"?\]', s)
        if sub_match:
            sub_id = sub_match.group(1)
            sub_label = sub_match.group(2).replace('<br/>', '\n')
            sg_obj = {'id': sub_id, 'label': sub_label, 'nodes': []}
            subgraphs.append(sg_obj)
            subgraph_stack.append(sg_obj)
            continue

        if s == 'end':
            if subgraph_stack:
                subgraph_stack.pop()
            continue

        # Extract explicit node declarations: Id[("Label")] | Id{"Label"} | Id["Label"]
        node_decl_matches = re.finditer(r'([A-Za-z0-9_]+)(?:\[\("?(.*?)"?\)\]|\{"?(.*?)"?\}|\["?(.*?)"?\])', s)
        for nd in node_decl_matches:
            nid = nd.group(1)
            raw_lbl = nd.group(2) or nd.group(3) or nd.group(4) or nid
            clean_lbl = raw_lbl.replace('<br/>', '\n').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
            nodes[nid] = clean_lbl
            if '[(' in nd.group(0):
                node_shapes[nid] = 'cylinder'
            elif '{' in nd.group(0):
                node_shapes[nid] = 'rhombus'
            else:
                node_shapes[nid] = 'rectangle'

            if subgraph_stack:
                subgraph_stack[-1]['nodes'].append(nid)

        # Edge parsing: handles chained arrows (A --> B --> C), bidirectional (<-->), dashed (-.->)
        arrow_token_pattern = re.compile(r'(<-->|<-.->|<==>|-->|-\.->|==>)')
        if arrow_token_pattern.search(s):
            # Split line into tokens preserving arrow boundaries
            raw_parts = re.split(r'\s*(<-->|<-.->|<==>|-->|-\.->|==>)(?:\|"?(.*?)"?\|)?\s*', s)
            # raw_parts alternates: [segment_0, arrow_1, label_1, segment_1, arrow_2, label_2, segment_2, ...]
            i = 0
            while i < len(raw_parts) - 2:
                src_segment = raw_parts[i].strip()
                arrow = raw_parts[i+1]
                edge_label = (raw_parts[i+2] or "").replace('<br/>', ' ').replace('&lt;', '<').replace('&gt;', '>').strip()
                dst_segment = raw_parts[i+3].strip() if i + 3 < len(raw_parts) else ""

                if src_segment and dst_segment and arrow:
                    # Clean up node identifiers from possible brackets
                    def extract_ids(seg):
                        seg_clean = re.sub(r'\[.*?\]|\(.*?\)', '', seg)
                        return [x.strip() for x in seg_clean.split('&') if x.strip()]

                    src_nodes = extract_ids(src_segment)
                    dst_nodes = extract_ids(dst_segment)

                    for sn in src_nodes:
                        for dn in dst_nodes:
                            if sn and dn:
                                edges.append({
                                    'src': sn,
                                    'dst': dn,
                                    'label': edge_label,
                                    'dashed': '-.-' in arrow,
                                    'bidi': '<' in arrow
                                })
                                if sn not in nodes:
                                    nodes[sn] = sn
                                    node_shapes[sn] = 'rectangle'
                                if dn not in nodes:
                                    nodes[dn] = dn
                                    node_shapes[dn] = 'rectangle'
                i += 3

    return nodes, node_shapes, edges, subgraphs

def parse_mmd_sequence(mmd_text):
    """Parser extracting participants and messages from Mermaid sequence diagram."""
    participants = []
    messages = []

    for line in mmd_text.splitlines():
        s = line.strip()
        if not s or s.startswith('%%') or s.startswith('sequenceDiagram') or s.startswith('autonumber'):
            continue
        part_match = re.match(r'(?:participant|actor)\s+([A-Za-z0-9_]+)\s+as\s+(.*)', s)
        if part_match:
            pid = part_match.group(1)
            plbl = part_match.group(2).replace('<br/>', '\n')
            is_actor = s.startswith('actor')
            participants.append({'id': pid, 'label': plbl, 'is_actor': is_actor})
            continue
        msg_match = re.match(r'([A-Za-z0-9_]+)(->>|-->>|-\)\)|-\) )\s*([A-Za-z0-9_]+):\s*(.*)', s)
        if msg_match:
            src = msg_match.group(1)
            arrow = msg_match.group(2)
            dst = msg_match.group(3)
            txt = msg_match.group(4).replace('<br/>', '\n').replace('&lt;', '<').replace('&gt;', '>')
            messages.append({'src': src, 'dst': dst, 'text': txt, 'is_return': '-->>' in arrow})

    return participants, messages

def build_flowchart_drawio(nodes, node_shapes, edges, subgraphs, title):
    """Constructs an mxGraphModel for a flowchart with professional styling and layout."""
    root = ET.Element('mxfile', host='app.diagrams.net', version='24.0.0', type='device')
    diagram = ET.SubElement(root, 'diagram', id='diag_' + re.sub(r'\W', '_', title), name=title)
    graph = ET.SubElement(diagram, 'mxGraphModel', dx='1800', dy='1400', grid='1', gridSize='10',
                          guides='1', tooltips='1', connect='1', arrows='1', fold='1', page='1',
                          pageScale='1', pageWidth='2800', pageHeight='2200', math='0', shadow='0')
    mroot = ET.SubElement(graph, 'root')
    ET.SubElement(mroot, 'mxCell', id='0')
    ET.SubElement(mroot, 'mxCell', id='1', parent='0')

    node_coords = {}
    col_width = 320
    row_height = 110
    start_x = 80
    start_y = 80

    sub_y = start_y
    for sg in subgraphs:
        sg_id = f"subgraph_{sg['id']}"
        sg_nodes = [n for n in sg['nodes'] if n in nodes]
        if not sg_nodes:
            continue
        count = len(sg_nodes)
        cols_in_sub = min(count, 4) if count > 0 else 1
        rows_in_sub = (count - 1) // 4 + 1 if count > 0 else 1
        sg_w = max(cols_in_sub * col_width + 40, 400)
        sg_h = rows_in_sub * row_height + 80

        sg_cell = ET.SubElement(mroot, 'mxCell', id=sg_id, value=sg['label'],
                                style="swimlane;whiteSpace=wrap;html=1;fillColor=#fafafa;strokeColor=#90a4ae;fontStyle=1;fontSize=13;startSize=32;rounded=1;arcSize=6;",
                                vertex='1', parent='1')
        ET.SubElement(sg_cell, 'mxGeometry', x=str(start_x), y=str(sub_y), width=str(sg_w), height=str(sg_h), attrib={'as': 'geometry'})

        for idx, nid in enumerate(sg_nodes):
            nx = start_x + 25 + (idx % 4) * col_width
            ny = sub_y + 45 + (idx // 4) * row_height
            node_coords[nid] = (nx, ny, 280, 75)

        sub_y += sg_h + 35

    # Any remaining nodes not in a subgraph
    idx = 0
    rem_y = sub_y + 20
    for nid in nodes:
        if nid not in node_coords:
            nx = start_x + (idx % 4) * col_width
            ny = rem_y + (idx // 4) * row_height
            node_coords[nid] = (nx, ny, 280, 75)
            idx += 1

    # Render node cells with respective shape and enterprise color palette
    for nid, lbl in nodes.items():
        x, y, w, h = node_coords.get(nid, (100, 100, 280, 75))
        category = determine_category(nid, lbl)
        c_fill, c_stroke, c_font = COLOR_MAP.get(category, COLOR_MAP['default'])

        shape_type = node_shapes.get(nid, 'rectangle')
        if shape_type == 'cylinder':
            shape_style = "shape=cylinder;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;"
        elif shape_type == 'rhombus':
            shape_style = "shape=rhombus;whiteSpace=wrap;html=1;"
        else:
            shape_style = "rounded=1;whiteSpace=wrap;html=1;"

        style = f"{shape_style}fillColor={c_fill};strokeColor={c_stroke};strokeWidth=1.5;fontColor={c_font};fontSize=11;fontStyle=1;shadow=0;"
        ncell = ET.SubElement(mroot, 'mxCell', id=nid, value=lbl, style=style, vertex='1', parent='1')
        ET.SubElement(ncell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), attrib={'as': 'geometry'})

    # Render edges
    for e_idx, e in enumerate(edges):
        if e['src'] not in nodes or e['dst'] not in nodes:
            continue
        eid = f"edge_{e['src']}_{e['dst']}_{e_idx}"
        edge_style = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#455a64;strokeWidth=1.5;"
        if e['dashed']:
            edge_style += "dashed=1;"
        if e['bidi']:
            edge_style += "startArrow=classic;endArrow=classic;"
        else:
            edge_style += "endArrow=classic;"

        ecell = ET.SubElement(mroot, 'mxCell', id=eid, value=e['label'], style=edge_style, edge='1', parent='1', source=e['src'], target=e['dst'])
        ET.SubElement(ecell, 'mxGeometry', relative='1', attrib={'as': 'geometry'})

    return ET.tostring(root, encoding='utf-8').decode('utf-8')

def build_sequence_drawio(participants, messages, title):
    """Constructs an mxGraphModel for a sequence diagram with lifelines and numbered callouts."""
    root = ET.Element('mxfile', host='app.diagrams.net', version='24.0.0', type='device')
    diagram = ET.SubElement(root, 'diagram', id='diag_' + re.sub(r'\W', '_', title), name=title)
    graph = ET.SubElement(diagram, 'mxGraphModel', dx='1800', dy='1400', grid='1', gridSize='10',
                          guides='1', tooltips='1', connect='1', arrows='1', fold='1', page='1',
                          pageScale='1', pageWidth='3200', pageHeight='2600', math='0', shadow='0')
    mroot = ET.SubElement(graph, 'root')
    ET.SubElement(mroot, 'mxCell', id='0')
    ET.SubElement(mroot, 'mxCell', id='1', parent='0')

    part_x = {}
    col_w = 230
    top_y = 60
    lifeline_len = len(messages) * 48 + 180

    for idx, p in enumerate(participants):
        px = 80 + idx * col_w
        part_x[p['id']] = px
        category = determine_category(p['id'], p['label'])
        c_fill, c_stroke, c_font = COLOR_MAP.get(category, COLOR_MAP['default'])

        if p.get('is_actor'):
            style = f"shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fillColor={c_fill};strokeColor={c_stroke};fontColor={c_font};fontStyle=1;"
            pcell = ET.SubElement(mroot, 'mxCell', id=p['id'], value=p['label'], style=style, vertex='1', parent='1')
            ET.SubElement(pcell, 'mxGeometry', x=str(px + 40), y=str(top_y), width='40', height='60', attrib={'as': 'geometry'})
        else:
            style = f"shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;collapsible=0;recursiveResize=0;outlineConnect=0;fillColor={c_fill};strokeColor={c_stroke};fontColor={c_font};fontStyle=1;size=42;fontSize=11;"
            pcell = ET.SubElement(mroot, 'mxCell', id=p['id'], value=p['label'], style=style, vertex='1', parent='1')
            ET.SubElement(pcell, 'mxGeometry', x=str(px), y=str(top_y), width='180', height=str(lifeline_len), attrib={'as': 'geometry'})

    # Messages
    for idx, m in enumerate(messages):
        src_id = m['src']
        dst_id = m['dst']
        my = top_y + 80 + idx * 48
        sx = part_x.get(src_id, 80) + 90
        dx = part_x.get(dst_id, 80) + 90

        edge_style = "html=1;verticalAlign=bottom;endArrow=block;rounded=0;strokeColor=#37474f;strokeWidth=1.5;fontSize=10;"
        if m['is_return']:
            edge_style += "dashed=1;"

        eid = f"msg_{idx}"
        mcell = ET.SubElement(mroot, 'mxCell', id=eid, value=f"{idx+1}. {m['text']}", style=edge_style, edge='1', parent='1')
        geo = ET.SubElement(mcell, 'mxGeometry', x='1', y='-10', relative='1', attrib={'as': 'geometry'})
        ET.SubElement(geo, 'mxPoint', x=str(sx), y=str(my), attrib={'as': 'sourcePoint'})
        ET.SubElement(geo, 'mxPoint', x=str(dx), y=str(my), attrib={'as': 'targetPoint'})

    return ET.tostring(root, encoding='utf-8').decode('utf-8')

def main():
    arch_dir = Path("docs/architecture")
    mmd_files = sorted(arch_dir.glob("*.mmd"))
    print(f"Building Draw.io XML for {len(mmd_files)} standardized architecture diagrams...")

    for f in mmd_files:
        name = f.stem
        text = f.read_text(encoding='utf-8')
        out_file = arch_dir / f"{name}.drawio"

        if "sequenceDiagram" in text:
            participants, messages = parse_mmd_sequence(text)
            xml_content = build_sequence_drawio(participants, messages, name)
        else:
            nodes, node_shapes, edges, subgraphs = parse_mmd_flowchart(text)
            xml_content = build_flowchart_drawio(nodes, node_shapes, edges, subgraphs, name)

        out_file.write_text(xml_content, encoding='utf-8')
        print(f"Successfully compiled: {out_file.name} ({len(xml_content)} bytes)")

if __name__ == '__main__':
    main()
