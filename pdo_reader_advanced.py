#!/usr/bin/env python3
"""
Enhanced PDO (Pepakura Designer) File Reader
Converted from pdo-tools by dpethes (https://github.com/dpethes/pdo-tools)

Features:
- Extract 3D models (OBJ format)
- Extract 2D papercraft layouts with textures (SVG format)
- Decompress and embed texture images
- Preserve material information
"""

import struct
import sys
import zlib
import base64
from io import BytesIO
from dataclasses import dataclass, field
from typing import List, BinaryIO, Optional

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
    u: float  # texture coordinate
    v: float  # texture coordinate
    flap: int
    flap_height: float
    flap_a_angle: float
    flap_b_angle: float

@dataclass
class PdoTexture:
    width: int
    height: int
    data_size: int
    data_header: int
    data_hash: int
    compressed_data: bytes
    texture_id: int = -1
    pixels: Optional[bytes] = None

@dataclass
class PdoMaterial:
    name: str
    color2d_rgba: List[float] = field(default_factory=list)
    has_texture: bool = False
    texture: Optional[PdoTexture] = None
    color3d: List[float] = field(default_factory=list)

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

@dataclass
class PdoRect:
    left: float
    top: float
    width: float
    height: float

@dataclass
class PdoPart:
    object_index: int
    name: str
    bounding_box: PdoRect

class PdoReaderAdvanced:
    def __init__(self, filename):
        self.filename = filename
        self.file = None
        self.string_shift = 0
        self.multi_byte_chars = False
        self.version = 0
        self.objects = []
        self.materials = []
        self.parts = []
        self.textures = []

    def read_int32(self) -> int:
        return struct.unpack('<i', self.file.read(4))[0]

    def read_uint32(self) -> int:
        return struct.unpack('<I', self.file.read(4))[0]

    def read_uint8(self) -> int:
        return struct.unpack('<B', self.file.read(1))[0]

    def read_uint16(self) -> int:
        return struct.unpack('<H', self.file.read(2))[0]

    def read_double(self) -> float:
        return struct.unpack('<d', self.file.read(8))[0]

    def read_float(self) -> float:
        return struct.unpack('<f', self.file.read(4))[0]

    def read_string(self, shift=0) -> str:
        """Read length-prefixed string"""
        length = self.read_int32()
        if length == 0:
            return ""

        if self.multi_byte_chars:
            length = length // 2
            chars = []
            for i in range(length - 1):
                w = self.read_uint16()
                chars.append(chr((w - shift) & 0xFF))
            self.read_uint16()  # null terminator
            return ''.join(chars)
        else:
            chars = []
            for i in range(length - 1):
                b = self.read_uint8()
                chars.append(chr(b - shift))
            self.read_uint8()  # null terminator
            return ''.join(chars)

    def read_shifted_string(self) -> str:
        return self.read_string(self.string_shift)

    def read_header(self):
        """Read PDO file header"""
        magic = self.file.read(10)
        if magic != b'version 3\n':
            raise ValueError("Not a version 3 PDO file")

        self.version = self.read_int32()
        multi_byte = self.read_int32()
        self.multi_byte_chars = (multi_byte == 1)

        unknown_int = self.read_int32()

        if self.version > 4:
            designer_id = self.read_string()
            self.string_shift = self.read_int32()

        locale = self.read_shifted_string()
        codepage = self.read_shifted_string()

        print(f"Version: {self.version}, Multi-byte: {self.multi_byte_chars}")

        texlock = self.read_int32()

        if self.version == 6:
            show_startup = self.read_uint8()
            password_flag = self.read_uint8()

        key = self.read_shifted_string()

        if self.version == 6:
            v6_lock = self.read_int32()
            if v6_lock > 0:
                self.file.read(v6_lock * 8)
        elif self.version > 4:
            show_startup = self.read_uint8()
            password_flag = self.read_uint8()

        assembled_height = self.read_double()
        origin_x = self.read_double()
        origin_y = self.read_double()
        origin_z = self.read_double()

    def read_texture(self) -> PdoTexture:
        """Read texture data"""
        width = self.read_int32()
        height = self.read_int32()
        wrapped_size = self.read_int32()

        TEXTURE_DATA_WRAPPER_SIZE = 6
        data_size = wrapped_size - TEXTURE_DATA_WRAPPER_SIZE

        data_header = self.read_uint16()
        compressed_data = self.file.read(data_size)
        data_hash = self.read_uint32()

        texture = PdoTexture(
            width=width,
            height=height,
            data_size=data_size,
            data_header=data_header,
            data_hash=data_hash,
            compressed_data=compressed_data
        )

        # Check if we already have this texture
        for i, tex in enumerate(self.textures):
            if tex.data_hash == data_hash:
                texture.texture_id = i
                return texture

        # New texture
        texture.texture_id = len(self.textures)
        self.textures.append(texture)

        return texture

    def decompress_texture(self, texture: PdoTexture) -> bytes:
        """Decompress texture data using zlib"""
        if texture.pixels is not None:
            return texture.pixels

        try:
            # Decompress zlib data
            pixels = zlib.decompress(texture.compressed_data)
            texture.pixels = pixels
            return pixels
        except Exception as e:
            print(f"Warning: Failed to decompress texture: {e}")
            return b''

    def rgb_to_png(self, rgb_data: bytes, width: int, height: int) -> bytes:
        """Convert raw RGB data to PNG format"""
        try:
            from PIL import Image
            img = Image.frombytes('RGB', (width, height), rgb_data)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
        except ImportError:
            # Fallback: create simple PNG without PIL
            return self.create_simple_png(rgb_data, width, height)

    def create_simple_png(self, rgb_data: bytes, width: int, height: int) -> bytes:
        """Create a simple PNG file without PIL (basic implementation)"""
        import zlib

        def write_chunk(chunk_type: bytes, data: bytes) -> bytes:
            chunk_len = struct.pack('>I', len(data))
            chunk_data = chunk_type + data
            crc = zlib.crc32(chunk_data) & 0xFFFFFFFF
            return chunk_len + chunk_data + struct.pack('>I', crc)

        # PNG signature
        png = b'\x89PNG\r\n\x1a\n'

        # IHDR chunk
        ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        png += write_chunk(b'IHDR', ihdr)

        # IDAT chunk - compress image data
        raw_data = b''
        for y in range(height):
            raw_data += b'\x00'  # filter type
            row_start = y * width * 3
            raw_data += rgb_data[row_start:row_start + width * 3]

        compressed = zlib.compress(raw_data, 9)
        png += write_chunk(b'IDAT', compressed)

        # IEND chunk
        png += write_chunk(b'IEND', b'')

        return png

    def read_material(self) -> PdoMaterial:
        """Read material"""
        name = self.read_shifted_string()

        # 3D colors (16 floats)
        color3d = [self.read_float() for _ in range(16)]

        # 2D color RGBA
        a = self.read_float()
        r = self.read_float()
        g = self.read_float()
        b = self.read_float()
        color2d_rgba = [r, g, b, a]

        # Texture
        texture_flag = self.read_uint8()
        has_texture = (texture_flag == 1)

        texture = None
        if has_texture:
            texture = self.read_texture()

        return PdoMaterial(name, color2d_rgba, has_texture, texture, color3d)

    def read_materials(self):
        """Read all materials"""
        print("\n=== Reading Materials ===")
        mat_count = self.read_int32()
        print(f"Material count: {mat_count}")

        for i in range(mat_count):
            material = self.read_material()
            if not material.name:
                material.name = f"material_{i}"
            self.materials.append(material)
            print(f"  {material.name}: texture={material.has_texture}")

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

        Nx = self.read_double()
        Ny = self.read_double()
        Nz = self.read_double()
        coord = self.read_double()

        vertex_count = self.read_int32()
        vertices = []
        for i in range(vertex_count):
            vertices.append(self.read_vertex2d())

        return PdoFace(material_index, part_index, Nx, Ny, Nz, coord, vertices)

    def read_object(self) -> PdoObject:
        """Read 3D object"""
        name = self.read_shifted_string()
        visible = self.read_uint8()

        vertex_count = self.read_int32()
        vertices = []
        for i in range(vertex_count):
            x = self.read_double()
            y = self.read_double()
            z = self.read_double()
            vertices.append(PdoVertex3D(x, y, z))

        face_count = self.read_int32()
        faces = []
        for i in range(face_count):
            faces.append(self.read_face())

        edge_count = self.read_int32()
        # Each edge is 22 bytes (not 28)
        self.file.read(edge_count * 22)

        return PdoObject(name, visible, vertices, faces)

    def read_objects(self):
        """Read all 3D objects"""
        print("\n=== Reading Objects ===")
        object_count = self.read_int32()
        print(f"Object count: {object_count}")

        for i in range(object_count):
            obj = self.read_object()
            self.objects.append(obj)
            print(f"  {obj.name}: {len(obj.vertices)} vertices, {len(obj.faces)} faces")

    def parse(self):
        """Parse the PDO file"""
        with open(self.filename, 'rb') as self.file:
            self.read_header()
            self.read_objects()
            self.read_materials()
            # Skip other sections for now

    def export_obj(self, output_file):
        """Export to OBJ format"""
        with open(output_file, 'w') as f:
            f.write(f"# Extracted from {self.filename}\n\n")

            vertex_offset = 1

            for obj in self.objects:
                f.write(f"o {obj.name}\n\n")

                for v in obj.vertices:
                    f.write(f"v {v.x:.6f} {v.y:.6f} {v.z:.6f}\n")

                f.write("\n")

                for face in obj.faces:
                    indices = [str(v.id_vertex + vertex_offset) for v in face.vertices]
                    f.write(f"f {' '.join(indices)}\n")

                vertex_offset += len(obj.vertices)
                f.write("\n")

        print(f"\n✓ Exported OBJ to: {output_file}")

    def export_svg_with_textures(self, output_file):
        """Export 2D layout with textures to SVG"""
        # Find bounding box
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
            # SVG header
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<svg xmlns="http://www.w3.org/2000/svg" ')
            f.write('xmlns:xlink="http://www.w3.org/1999/xlink" ')
            f.write(f'width="{width:.2f}mm" height="{height:.2f}mm" ')
            f.write(f'viewBox="{min_x-10:.2f} {min_y-10:.2f} {width:.2f} {height:.2f}">\n')

            # Definitions for clip paths
            f.write('  <defs>\n')
            clip_id = 0

            # Process faces with textures
            for obj in self.objects:
                for face in obj.faces:
                    if face.material_index < 0 or face.material_index >= len(self.materials):
                        continue

                    material = self.materials[face.material_index]

                    if material.has_texture and material.texture:
                        # Create clip path for this face
                        f.write(f'    <clipPath id="clip{clip_id}">\n')
                        points = ' '.join(f"{v.x:.2f},{v.y:.2f}" for v in face.vertices)
                        f.write(f'      <polygon points="{points}"/>\n')
                        f.write(f'    </clipPath>\n')

                        # Decompress texture
                        texture = material.texture
                        if texture.texture_id >= 0 and texture.texture_id < len(self.textures):
                            stored_texture = self.textures[texture.texture_id]
                            rgb_data = self.decompress_texture(stored_texture)

                            if rgb_data:
                                # Convert to PNG
                                png_data = self.rgb_to_png(rgb_data, texture.width, texture.height)
                                # Encode as base64
                                b64_data = base64.b64encode(png_data).decode('ascii')

                                # Calculate texture bounding box
                                tex_min_x = min(v.x for v in face.vertices)
                                tex_min_y = min(v.y for v in face.vertices)
                                tex_max_x = max(v.x for v in face.vertices)
                                tex_max_y = max(v.y for v in face.vertices)
                                tex_width = tex_max_x - tex_min_x
                                tex_height = tex_max_y - tex_min_y

                                # Store for later rendering
                                f.write(f'    <!-- Texture for clip{clip_id}: {texture.width}x{texture.height} -->\n')

                        clip_id += 1

            f.write('  </defs>\n\n')

            # Draw layer
            f.write('  <g id="papercraft">\n')

            # Draw faces with textures
            clip_id = 0
            for obj in self.objects:
                for face in obj.faces:
                    if len(face.vertices) < 3:
                        continue

                    material = self.materials[face.material_index] if face.material_index >= 0 else None

                    if material and material.has_texture and material.texture:
                        texture = material.texture
                        if texture.texture_id >= 0:
                            stored_texture = self.textures[texture.texture_id]
                            rgb_data = self.decompress_texture(stored_texture)

                            if rgb_data:
                                png_data = self.rgb_to_png(rgb_data, texture.width, texture.height)
                                b64_data = base64.b64encode(png_data).decode('ascii')

                                tex_min_x = min(v.x for v in face.vertices)
                                tex_min_y = min(v.y for v in face.vertices)
                                tex_max_x = max(v.x for v in face.vertices)
                                tex_max_y = max(v.y for v in face.vertices)
                                tex_width = tex_max_x - tex_min_x
                                tex_height = tex_max_y - tex_min_y

                                f.write(f'    <image x="{tex_min_x:.2f}" y="{tex_min_y:.2f}" ')
                                f.write(f'width="{tex_width:.2f}" height="{tex_height:.2f}" ')
                                f.write(f'preserveAspectRatio="none" ')
                                f.write(f'clip-path="url(#clip{clip_id})" ')
                                f.write(f'xlink:href="data:image/png;base64,{b64_data}"/>\n')

                        clip_id += 1
                    else:
                        # Draw polygon without texture
                        points = ' '.join(f"{v.x:.2f},{v.y:.2f}" for v in face.vertices)
                        f.write(f'    <polygon points="{points}" fill="white" stroke="black" stroke-width="0.5"/>\n')

            # Draw outlines
            for obj in self.objects:
                for face in obj.faces:
                    if len(face.vertices) < 3:
                        continue
                    points = ' '.join(f"{v.x:.2f},{v.y:.2f}" for v in face.vertices)
                    f.write(f'    <polygon points="{points}" fill="none" stroke="black" stroke-width="0.5"/>\n')

            f.write('  </g>\n')
            f.write('</svg>\n')

        print(f"\n✓ Exported SVG with textures to: {output_file}")
        print(f"  Textures: {len(self.textures)}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pdo_reader_advanced.py <file.pdo>")
        sys.exit(1)

    pdo_file = sys.argv[1]
    reader = PdoReaderAdvanced(pdo_file)

    try:
        reader.parse()

        # Export OBJ
        obj_file = pdo_file.replace('.pdo', '_extracted.obj')
        reader.export_obj(obj_file)

        # Export SVG with textures
        svg_file = pdo_file.replace('.pdo', '_textured.svg')
        reader.export_svg_with_textures(svg_file)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
