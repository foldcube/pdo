# PDO File Reader

A Python tool for extracting 3D models and 2D papercraft layouts from Pepakura Designer (.pdo) files.

## Features

- **Extract 3D Model**: Exports the 3D geometry as OBJ format
- **Extract 2D Layout**: Exports the unfolded papercraft pattern as SVG format
- **Cut Model Information**: Preserves face and vertex relationships

## Requirements

- Python 3.6+
- No external dependencies

## Usage

```bash
python3 pdo_reader.py <file.pdo>
```

### Example

```bash
python3 pdo_reader.py torus.pdo
```

This will create:
- `torus_extracted.obj` - The 3D model in OBJ format
- `torus_layout.svg` - The 2D unfolded papercraft layout

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

Based on reverse-engineering work from:
- [pdo-tools](https://github.com/dpethes/pdo-tools) by dpethes
- [PepakuraReverse](https://github.com/daeken/PepakuraReverse)

Supports Pepakura Designer file format version 3 (versions 4, 5, and 6).

### PDO File Structure

1. **Header**: Version info, locale, codepage, model parameters
2. **Objects**: 3D geometry (vertices, faces, edges)
3. **Materials**: Colors and textures (not currently extracted)
4. **Parts**: 2D layout information
5. **Settings**: Display and layout settings

## Example Files

The repository includes several test files:
- `pyramid.pdo` - Simple 5-vertex pyramid
- `cone.pdo` - Cone shape
- `cylinder.pdo` - Cylinder shape
- `sphere.pdo` - Sphere approximation
- `torus.pdo` - Donut/torus shape (300 vertices, 600 faces)

## Limitations

- Material and texture extraction not yet implemented
- Edge numbers and labels not exported
- Tab shapes not included in SVG output

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
