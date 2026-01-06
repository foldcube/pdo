#!/usr/bin/env python3
"""
PDO (Pepakura Designer) File Reader
Based on pdo-tools by dpethes (https://github.com/dpethes/pdo-tools)

Extracts:
- 3D model geometry (OBJ format)
- 2D unfolded layout (SVG format)
- Face and edge information
"""

import struct
import sys
from dataclasses import dataclass, field
from typing import List, BinaryIO

@dataclass
class PdoVertex3D:
    x: float
    y: float
    z: float

@dataclass
class PdoVertex2D:
    id_vertex: int
    x: float
    y: float
    u: float
    v: float
    flap: int
    flap_height: float
    flap_a_angle: float
    flap_b_angle: float

@dataclass
class PdoFace:
    material_index: int
    part_index: int
    Nx: float
    Ny: float
    Nz: float
    coord: float
    vertices: List[PdoVertex2D] = field(default_factory=list)

@dataclass
class PdoObject:
    name: str
    visible: int
    vertices: List[PdoVertex3D] = field(default_factory=list)
    faces: List[PdoFace] = field(default_factory=list)

class PdoReader:
    def __init__(self, filename):
        self.filename = filename
        self.file = None
        self.string_shift = 0
        self.multi_byte_chars = False
        self.version = 0
        self.objects = []

    def read_int32(self) -> int:
        return struct.unpack('<i', self.file.read(4))[0]

    def read_uint32(self) -> int:
        return struct.unpack('<I', self.file.read(4))[0]

    def read_uint8(self) -> int:
        return struct.unpack('<B', self.file.read(1))[0]

    def read_double(self) -> float:
        return struct.unpack('<d', self.file.read(8))[0]

    def read_string(self, shift=0) -> str:
        """Read length-prefixed string"""
        length = self.read_int32()
        if length == 0:
            return ""

        if self.multi_byte_chars:
            # UTF-16 LE
            length = length // 2
            chars = []
            for i in range(length - 1):
                w = struct.unpack('<H', self.file.read(2))[0]
                chars.append(chr((w - shift) & 0xFF))
            # Read null terminator
            self.file.read(2)
            return ''.join(chars)
        else:
            # Single byte
            chars = []
            for i in range(length - 1):
                b = self.read_uint8()
                chars.append(chr(b - shift))
            # Read null terminator
            self.read_uint8()
            return ''.join(chars)

    def read_shifted_string(self) -> str:
        return self.read_string(self.string_shift)

    def read_header(self):
        """Read PDO file header"""
        # Check file magic
        magic = self.file.read(10)
        if magic != b'version 3\n':
            raise ValueError("Not a version 3 PDO file")

        # Read version and settings
        self.version = self.read_int32()
        multi_byte = self.read_int32()
        self.multi_byte_chars = (multi_byte == 1)

        # Unknown int
        unknown_int = self.read_int32()

        # Designer ID and string shift (if version > 4)
        if self.version > 4:
            designer_id = self.read_string()
            self.string_shift = self.read_int32()
            print(f"Designer ID: {designer_id}, String shift: {self.string_shift}")

        # Locale and codepage
        locale = self.read_shifted_string()
        codepage = self.read_shifted_string()

        print(f"Version: {self.version}, Multi-byte: {self.multi_byte_chars}")
        print(f"Locale: {locale}, Codepage: {codepage}")

        # Texture lock
        texlock = self.read_int32()

        # Version 6 specific
        if self.version == 6:
            show_startup = self.read_uint8()
            password_flag = self.read_uint8()

        # Key string
        key = self.read_shifted_string()

        # More version 6 specific data
        if self.version == 6:
            v6_lock = self.read_int32()
            if v6_lock > 0:
                # Skip junk data
                self.file.read(v6_lock * 8)
        elif self.version > 4:
            show_startup = self.read_uint8()
            password_flag = self.read_uint8()

        # Model parameters
        assembled_height = self.read_double()
        origin_x = self.read_double()
        origin_y = self.read_double()
        origin_z = self.read_double()

        print(f"Model height: {assembled_height}, Origin: ({origin_x}, {origin_y}, {origin_z})")

    def read_vertex2d(self) -> PdoVertex2D:
        """Read 2D face vertex"""
        id_vertex = self.read_int32()
        x = self.read_double()
        y = self.read_double()
        u = self.read_double()
        v = self.read_double()
        flap = self.read_uint8()
        flap_height = self.read_double()
        flap_a_angle = self.read_double()
        flap_b_angle = self.read_double()

        # Skip flap fold info (24 bytes)
        self.file.read(24)

        return PdoVertex2D(id_vertex, x, y, u, v, flap,
                           flap_height, flap_a_angle, flap_b_angle)

    def read_face(self) -> PdoFace:
        """Read face"""
        material_index = self.read_int32()
        part_index = self.read_int32()

        # Normal vector and coord
        Nx = self.read_double()
        Ny = self.read_double()
        Nz = self.read_double()
        coord = self.read_double()

        # Read vertices
        vertex_count = self.read_int32()
        vertices = []
        for i in range(vertex_count):
            vertices.append(self.read_vertex2d())

        return PdoFace(material_index, part_index, Nx, Ny, Nz, coord, vertices)

    def read_object(self) -> PdoObject:
        """Read 3D object"""
        name = self.read_shifted_string()
        visible = self.read_uint8()

        print(f"\n  Object: {name}, Visible: {visible}")

        # Read 3D vertices
        vertex_count = self.read_int32()
        vertices = []
        for i in range(vertex_count):
            x = self.read_double()
            y = self.read_double()
            z = self.read_double()
            vertices.append(PdoVertex3D(x, y, z))

        print(f"    Vertices: {vertex_count}")

        # Read faces
        face_count = self.read_int32()
        faces = []
        for i in range(face_count):
            faces.append(self.read_face())

        print(f"    Faces: {face_count}")

        # Skip edges for now
        edge_count = self.read_int32()
        # Each edge is 28 bytes
        self.file.read(edge_count * 28)

        return PdoObject(name, visible, vertices, faces)

    def read_objects(self):
        """Read all 3D objects"""
        print("\n=== Reading Objects ===")
        object_count = self.read_int32()
        print(f"Object count: {object_count}")

        for i in range(object_count):
            obj = self.read_object()
            self.objects.append(obj)

    def parse(self):
        """Parse the PDO file"""
        with open(self.filename, 'rb') as self.file:
            self.read_header()
            self.read_objects()
            # Note: We're skipping materials, parts, settings, etc. for now
            # These can be added if needed

    def export_obj(self, output_file):
        """Export to OBJ format"""
        with open(output_file, 'w') as f:
            f.write(f"# Extracted from {self.filename}\n")
            f.write(f"# Objects: {len(self.objects)}\n\n")

            vertex_offset = 1  # OBJ indices start at 1

            for obj in self.objects:
                f.write(f"# Object: {obj.name}\n")
                f.write(f"o {obj.name}\n\n")

                # Write 3D vertices
                for v in obj.vertices:
                    f.write(f"v {v.x:.6f} {v.y:.6f} {v.z:.6f}\n")

                f.write("\n")

                # Write faces
                for face in obj.faces:
                    # Get vertex indices for this face
                    indices = [str(v.id_vertex + vertex_offset) for v in face.vertices]
                    f.write(f"f {' '.join(indices)}\n")

                vertex_offset += len(obj.vertices)
                f.write("\n")

        print(f"\n✓ Exported OBJ to: {output_file}")
        total_verts = sum(len(o.vertices) for o in self.objects)
        total_faces = sum(len(o.faces) for o in self.objects)
        print(f"  Total vertices: {total_verts}")
        print(f"  Total faces: {total_faces}")

    def export_svg(self, output_file):
        """Export 2D layout to SVG"""
        # Find bounding box of all 2D coordinates
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

        for obj in self.objects:
            for face in obj.faces:
                for v in face.vertices:
                    min_x = min(min_x, v.x)
                    min_y = min(min_y, v.y)
                    max_x = max(max_x, v.x)
                    max_y = max(max_y, v.y)

        if min_x == float('inf'):
            print("No 2D data to export")
            return

        width = max_x - min_x + 20
        height = max_y - min_y + 20

        with open(output_file, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" ')
            f.write(f'width="{width:.2f}" height="{height:.2f}" ')
            f.write(f'viewBox="{min_x-10:.2f} {min_y-10:.2f} {width:.2f} {height:.2f}">\n')
            f.write('  <g id="layout">\n')

            # Draw faces
            for obj in self.objects:
                for face in obj.faces:
                    if len(face.vertices) < 3:
                        continue

                    # Create polygon
                    points = ' '.join(f"{v.x:.2f},{v.y:.2f}" for v in face.vertices)
                    f.write(f'    <polygon points="{points}" ')
                    f.write('fill="white" stroke="black" stroke-width="0.5"/>\n')

            f.write('  </g>\n')
            f.write('</svg>\n')

        print(f"\n✓ Exported SVG to: {output_file}")
        print(f"  Dimensions: {width:.1f} x {height:.1f}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pdo_reader.py <file.pdo>")
        sys.exit(1)

    pdo_file = sys.argv[1]
    reader = PdoReader(pdo_file)

    try:
        reader.parse()

        # Export OBJ
        obj_file = pdo_file.replace('.pdo', '_extracted.obj')
        reader.export_obj(obj_file)

        # Export SVG
        svg_file = pdo_file.replace('.pdo', '_layout.svg')
        reader.export_svg(svg_file)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
