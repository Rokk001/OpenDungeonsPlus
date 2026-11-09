#!/usr/bin/env python3
"""Align the wooden mug's physical bowl and lip with the tavern attachment contract.

The original mesh runs along native z; the drink rig expects -x. Keep its materials, topology and UVs, compact its
radial geometry around the handle grip, and put actual wooden base/lip edges at the authored contact points.
Call with an original exported TavernMug.mesh.xml and a different output XML path, optionally --report report.json.
"""
import argparse
import copy
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


def layout_without_vectors(root):
    """Snapshot every mesh field except the position/normal vectors that this repair deliberately changes."""
    layout = copy.deepcopy(root)
    for vertex in layout.iter('vertex'):
        for field in list(vertex):
            if field.tag in ('position', 'normal'):
                vertex.remove(field)
    return ET.tostring(layout)


def normalize_mug(source, destination):
    """Repair an original z-axis mug once, preserving all non-vector mesh data and returning fixed-contract measures."""
    assert source.resolve() != destination.resolve(), 'Keep the original mesh XML as the repair source'
    mesh = ET.parse(source)
    root = mesh.getroot()
    preserved = layout_without_vectors(root)
    shared = root.find('sharedgeometry')
    assert shared is not None
    buffer = next(item for item in shared.findall('vertexbuffer') if item.get('positions') == 'true')
    vertices = list(buffer)
    assert len(vertices) == 8412, ('mug vertices', len(vertices))
    old = np.array([[float(vertex.find('position').get(axis)) for axis in 'xyz'] for vertex in vertices])
    normal_buffer = next(item for item in shared.findall('vertexbuffer') if item.get('normals') == 'true')
    normals = np.array([[float(vertex.find('normal').get(axis)) for axis in 'xyz'] for vertex in normal_buffer])
    assert len(normals) == len(vertices)
    materials = {}
    for submesh in root.find('submeshes'):
        assert submesh.get('usesharedvertices') == 'true'
        assert submesh.get('material') not in materials, 'Unexpected repeated material submesh'
        materials[submesh.get('material')] = {int(face.get(axis)) for face in submesh.find('faces')
                                              for axis in ('v1', 'v2', 'v3')}
    assert set(materials) == {'TavernWood', 'TavernIron', 'TavernFoam'}
    foam = sorted(materials['TavernFoam'])
    assert not set(foam).intersection(materials['TavernWood'] | materials['TavernIron'])
    wood = old[sorted(materials['TavernWood'])]
    foam_points = old[foam]
    # These material-defined ends reject an already repaired source instead of deforming the mug a second time.
    assert abs(float(wood[:, 2].min()) + 0.065) < 1e-6
    assert abs(float(wood[:, 2].max()) - 0.060) < 1e-6
    assert abs(float(foam_points[:, 2].min()) - 0.042) < 1e-6
    assert abs(float(foam_points[:, 2].max()) - 0.0719873) < 1e-6
    foam_share = (0.060 - 0.042) / (0.0719873 - 0.042)
    transform = np.array([[0.0, 0.0, -1.44], [0.0, 0.6, 0.0], [0.6, 0.0, 0.0]])
    foam_transform = transform.copy()
    foam_transform[0, 2] *= foam_share
    position = old @ transform.T + np.array([-0.0846, 0.0, 0.0270])
    position[foam, 0] = -0.0846 - 1.44 * (0.042 + (old[foam, 2] - 0.042) * foam_share)
    new_normals = normals @ np.linalg.inv(transform)
    new_normals[foam] = normals[foam] @ np.linalg.inv(foam_transform)
    lengths = np.linalg.norm(new_normals, axis=1)
    assert np.isfinite(new_normals).all() and float(lengths.min()) > 1e-12
    new_normals /= lengths[:, None]
    for index, vertex in enumerate(vertices):
        for axis, value in zip('xyz', position[index]):
            vertex.find('position').set(axis, format(float(value), '.9g'))
    for index, vertex in enumerate(normal_buffer):
        for axis, value in zip('xyz', new_normals[index]):
            vertex.find('normal').set(axis, format(float(value), '.9g'))
    new_wood = position[sorted(materials['TavernWood'])]
    new_foam = position[foam]
    assert abs(float(new_wood[:, 0].max()) - 0.009) < 1e-7
    assert abs(float(new_wood[:, 0].min()) + 0.171) < 1e-7
    assert abs(float(new_foam[:, 0].min()) + 0.171) < 1e-7
    assert np.max(np.abs(np.linalg.norm(new_normals, axis=1) - 1.0)) < 1e-10
    assert layout_without_vectors(root) == preserved, 'Topology, materials, UVs or another mesh field changed'
    destination.parent.mkdir(parents=True, exist_ok=True)
    mesh.write(destination, encoding='utf-8', xml_declaration=True)
    return {'vertices': len(vertices), 'materials': {name: len(indices) for name, indices in materials.items()},
            'bowl_axis': [-1.0, 0.0, 0.0], 'physical_base_centre': [0.009, 0.0, -0.0372],
            'physical_rim_centre': [-0.171, 0.0, -0.0372], 'nominal_body_radial_half_width': 0.0384,
            'foot_contact_point': [0.009, 0.0, 0.0], 'lip_contact_point': [-0.171, 0.0, 0.0],
            'wood_bounds': [new_wood.min(axis=0).tolist(), new_wood.max(axis=0).tolist()],
            'foam_bounds': [new_foam.min(axis=0).tolist(), new_foam.max(axis=0).tolist()],
            'handle_outer_radial_extent': 0.0324, 'topology_materials_uvs_preserved': True}


def main():
    """Write a separate canonical candidate and optional measurements without overwriting the original source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = normalize_mug(args.input, args.output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
