"""Render question diagrams without network access or temporary image files."""
import io
import math
import re
import xml.etree.ElementTree as ET


def diagram_folder(certification_id, level_code, level, set_id):
    for component in (certification_id, level_code):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', component):
            raise ValueError(f'Invalid storage path component: {component!r}')
    low, high = level['target_grade_min'], level['target_grade_max']
    if not isinstance(low, int) or not isinstance(high, int) or low > high:
        raise ValueError('A valid grade range is required for diagram storage')
    grade = str(low) if low == high else f'{low}-{high}'
    return f'{certification_id}/grade_{grade}/{level_code}/{set_id}'


def render_chart_svg(chart_type, data):
    if not isinstance(data, dict):
        raise ValueError('Chart data must be an object')
    if chart_type == 'GEOMETRY_SVG':
        source = data.get('svg')
        if not isinstance(source, str) or '<!DOCTYPE' in source.upper() or '<!ENTITY' in source.upper():
            raise ValueError('Geometry must contain standalone SVG without a DTD or entities')
        try:
            root = ET.fromstring(source)
        except ET.ParseError as exc:
            raise ValueError('Invalid geometry SVG') from exc
        namespace = 'http://www.w3.org/2000/svg'
        allowed_tags = {'svg', 'g', 'defs', 'path', 'rect', 'circle', 'ellipse', 'line',
                        'polyline', 'polygon', 'text', 'tspan', 'title', 'desc',
                        'clipPath', 'marker', 'use'}
        if root.tag not in ('svg', f'{{{namespace}}}svg'):
            raise ValueError('Geometry root must be svg')
        for node in root.iter():
            tag = node.tag.removeprefix(f'{{{namespace}}}')
            if tag not in allowed_tags:
                raise ValueError(f'Unsupported geometry SVG element: {tag}')
            for name, value in node.attrib.items():
                local = name.rsplit('}', 1)[-1].lower()
                if local.startswith('on') or local == 'style':
                    raise ValueError('SVG event handlers and inline CSS are not supported')
                if local == 'href' and not value.startswith('#'):
                    raise ValueError('SVG references must be local')
                if 'url(' in value.lower() and not re.fullmatch(r'url\(#[A-Za-z_][\w.-]*\)', value):
                    raise ValueError('SVG paint references must be local')
        if 'viewBox' not in root.attrib:
            raise ValueError('Geometry SVG requires a viewBox for responsive display')
        if root.tag == 'svg':
            root.set('xmlns', namespace)
        ET.register_namespace('', namespace)
        return ET.tostring(root, encoding='utf-8', xml_declaration=True)

    if chart_type not in {'BAR', 'LINE', 'PIE'}:
        raise ValueError(f'Unsupported chart type: {chart_type}')
    categories, values = data.get('categories'), data.get('values')
    if (not isinstance(categories, list) or not isinstance(values, list)
            or not categories or len(categories) != len(values)
            or not all(isinstance(c, str) and c.strip() for c in categories)
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                       and math.isfinite(v) for v in values)):
        raise ValueError('Charts require equally sized nonempty categories and finite numeric values')
    if chart_type == 'PIE' and (min(values) < 0 or sum(values) <= 0):
        raise ValueError('Pie values must be nonnegative with a positive total')

    # Lazy import keeps non-chart generation independent of Matplotlib.
    from matplotlib import rc_context
    from matplotlib.figure import Figure
    fig = Figure(figsize=(8, 5), layout='constrained')
    ax = fig.subplots()
    with rc_context({'svg.fonttype': 'path'}):
        if chart_type == 'PIE':
            ax.pie(values, labels=[f'{c}: {v:g}' for c, v in zip(categories, values)],
                   startangle=90)
            ax.set_aspect('equal')
        else:
            positions = range(len(categories))
            if chart_type == 'BAR':
                ax.bar(positions, values, color='#2874a6', width=.6)
            else:
                ax.plot(positions, values, color='#2874a6', marker='o', linewidth=2.5)
            ax.set_xticks(list(positions), categories)
            ax.set_axisbelow(True)
            ax.grid(axis='y', color='#d9dee5')
            ax.spines[['top', 'right']].set_visible(False)
            ax.margins(y=.2)
            for x, value in enumerate(values):
                ax.annotate(f'{value:g}', (x, value), xytext=(0, 8),
                            textcoords='offset points', ha='center')
        for key, setter in [('title', ax.set_title), ('x_label', ax.set_xlabel), ('y_label', ax.set_ylabel)]:
            if data.get(key):
                if not isinstance(data[key], str):
                    raise ValueError(f'{key} must be text')
                setter(data[key])
        output = io.BytesIO()
        fig.savefig(output, format='svg', facecolor='white', metadata={'Date': None})
    return output.getvalue()
