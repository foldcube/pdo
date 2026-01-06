# PDO File Reader

Python tools for extracting 3D models and 2D papercraft layouts from Pepakura Designer (.pdo) files.

Converted from [pdo-tools](https://github.com/dpethes/pdo-tools) by dpethes (Pascal) to Python.

## Features

- **Extract 3D Model**: Exports the 3D geometry as OBJ format
- **Extract 2D Layout**: Exports the unfolded papercraft pattern as SVG format
- **Texture Support**: Decompresses and embeds textures in SVG (advanced version)
- **Material Information**: Preserves material colors and properties

## Tools

### pdo_reader.py (Basic)
Simple extractor for geometry and basic layout.

**Requirements:** Python 3.6+ (no external dependencies)

**Usage:**
```bash
python3 pdo_reader.py <file.pdo>
```

**Outputs:**
- `*_extracted.obj` - 3D model in OBJ format
- `*_layout.svg` - 2D unfolded papercraft layout

### pdo_reader_advanced.py (With Textures)
Full-featured extractor with texture decompression and embedding.

**Requirements:**
- Python 3.6+
- Optional: PIL/Pillow for better PNG encoding (will fallback to built-in if not available)

**Usage:**
```bash
python3 pdo_reader_advanced.py <file.pdo>
```

**Outputs:**
- `*_extracted.obj` - 3D model in OBJ format
- `*_textured.svg` - 2D layout with embedded textures

**Features:**
- Zlib decompression of texture data
- RGB to PNG conversion
- Base64 encoding for SVG embedding
- SVG clipping paths for face textures
- Material color preservation

### Example

```bash
python3 pdo_reader_advanced.py torus.pdo
```

This will create:
- `torus_extracted.obj` - The 3D model
- `torus_textured.svg` - The 2D layout with textures (if any)

## Output Formats

### OBJ File
Standard Wavefront OBJ format containing:
- Vertices (`v x y z`)
- Faces (`f v1 v2 v3 ...`)

### SVG File
Scalable Vector Graphics format showing:
- 2D polygon outlines
- Unfolded face layout
- Can be viewed in any web browser or vector graphics editor

## Implementation Details

Converted from Pascal to Python based on:
- **[pdo-tools](https://github.com/dpethes/pdo-tools)** by dpethes - Primary reference (Pascal/Lazarus)
- **[PepakuraReverse](https://github.com/daeken/PepakuraReverse)** - Format research

Supports Pepakura Designer file format version 3 (versions 4, 5, and 6).

### PDO File Structure

1. **Header**: Version info, locale, codepage, encryption settings, model parameters
2. **Objects**: 3D geometry (vertices, faces, edges) with 2D unfolding coordinates
3. **Materials**: Colors, textures (zlib-compressed RGB data)
4. **Parts**: 2D layout groupings and bounding boxes
5. **Settings**: Page layout, fold line styles, edge IDs

### Texture Handling (Advanced Version)

Textures in PDO files are:
1. Stored as zlib-compressed RGB data (width × height × 3 bytes)
2. Decompressed using Python's `zlib` library
3. Converted to PNG format (with PIL/Pillow or built-in implementation)
4. Base64-encoded for embedding in SVG
5. Clipped to face polygons using SVG `<clipPath>` elements

## Example Files

The repository includes several test files:
- `pyramid.pdo` - Simple 5-vertex pyramid
- `cone.pdo` - Cone shape
- `cylinder.pdo` - Cylinder shape
- `sphere.pdo` - Sphere approximation
- `torus.pdo` - Donut/torus shape (300 vertices, 600 faces)

## Limitations

### Basic Version (pdo_reader.py)
- No texture extraction
- Basic SVG without embedded images

### Advanced Version (pdo_reader_advanced.py)
- Parts and tab geometry not yet fully implemented
- Edge numbers and labels not exported
- Fold line styles not differentiated
- Text blocks not extracted

### Both Versions
- Multi-page layouts exported as single file
- Some advanced PDO features may not be supported

## Format Notes

PDO files use a proprietary binary format. The file structure includes:
- Length-prefixed strings (UTF-8 or UTF-16)
- Little-endian byte ordering
- Optional string encryption (shift cipher)

## Sources

- [pdo-tools GitHub Repository](https://github.com/dpethes/pdo-tools)
- [PepakuraReverse GitHub Repository](https://github.com/daeken/PepakuraReverse)
- [PDO File Format Documentation](https://docs.fileformat.com/misc/pdo/)

## License

This tool is provided for educational purposes. Pepakura Designer and the PDO format are proprietary software/formats owned by Tama Software.
