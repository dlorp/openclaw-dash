# NES/SNES ROM Analyzer

Terminal-native ROM header parser for NES (iNES/NES 2.0) and SNES formats.

## Features

- **NES ROMs (.nes)**
  - iNES and NES 2.0 format detection
  - Mapper number identification
  - PRG/CHR ROM size calculation
  - Battery, trainer, mirroring detection
  - VS System / PlayChoice-10 detection

- **SNES ROMs (.smc, .sfc)**
  - Internal header parsing (at $FFB0)
  - Copier header detection (512-byte SMC headers)
  - LoROM/HiROM/ExHiROM identification
  - Checksum validation
  - Japanese title support (Shift-JIS decoding)

- **Terminal Aesthetic**
  - GameBoy-inspired box drawing
  - Glyphs over emoji (▸ ✓ ✗)
  - Dense information display

## Usage

### Single File
```bash
./analyzer.py path/to/game.nes
./analyzer.py path/to/game.smc
```

### Batch Analysis
```bash
./analyzer.py /path/to/rom/directory/
```
Recursively scans for `.nes`, `.smc`, `.sfc`, `.fig` files.

### Example Output

```
▸ Analyzing: zelda.nes
  Size: 131,088 bytes

┌──────────────────────────────────────────────────────────┐
│ NES ROM HEADER                                           │
├──────────────────────────────────────────────────────────┤
│ Format: iNES                                             │
│ Mapper: #1                                               │
│ PRG ROM: 128 KB (8 × 16KB)                              │
│ CHR ROM: None (uses CHR-RAM)                            │
│ Mirroring: Horizontal                                    │
│ Battery: Yes                                             │
│ Trainer: No                                              │
│ File size: 131,088 bytes (expected: 131,088)            │
└──────────────────────────────────────────────────────────┘
```

## Testing

Generate test ROM files:
```bash
./test_data_generator.py
```

Creates `test_roms/` with sample NES and SNES files:
- `test_basic.nes` - Basic iNES ROM (NROM mapper)
- `test_battery.nes` - Battery-backed RAM (MMC1)
- `test_trainer.nes` - ROM with 512-byte trainer
- `test_lorom.smc` - SNES LoROM
- `test_hirom.sfc` - SNES HiROM with RAM
- `test_copier.smc` - SNES with 512-byte copier header

Then analyze:
```bash
./analyzer.py test_roms/
```

## Use Cases

### Fan Translation Workflow
- Verify ROM integrity before translation work
- Identify mapper and memory configuration
- Batch-scan translation project directories

### ROM Preservation
- Catalog personal ROM collections
- Verify dumps against known good headers
- Identify copier headers on SNES dumps

### 3DS Virtual Console
- TNES format support planned (see IMPLEMENTATION.md)
- Automatic TNES→iNES conversion utility

### Emulation Setup
- Quick mapper identification for emulator config
- Verify ROM/RAM sizes match emulator expectations

## Technical Details

### NES Format Support
- **iNES** - 16-byte header + optional 512-byte trainer
- **NES 2.0** - Extended format detection via flags 7
- **Mappers** - 8-bit mapper number (0-255)
- **Sizes** - PRG ROM in 16KB units, CHR ROM in 8KB units

### SNES Format Support
- **Internal header** - 48 bytes at $FFB0-$FFDF (LoROM) or $40FFB0 (HiROM)
- **Copier headers** - Auto-detect 512-byte SMC headers
- **Map modes** - LoROM, HiROM, ExHiROM, SA-1
- **Checksums** - Validates complement + checksum = 0xFFFF

### Header Detection
- **NES**: Magic bytes "NES\x1A" at offset 0
- **SNES**: Fixed value 0x33 at $FFDA, tries common offsets:
  - 0x7FB0 (LoROM)
  - 0x81B0 (LoROM + copier)
  - 0xFFB0 (HiROM)
  - 0x101B0 (HiROM + copier)

## Alignment with dlorp's Interests

- **Retro gaming** - NES/GBA/PSX modding and emulation
- **Fan translations** - NES/GBA ROM header analysis
- **Binary format parsers** - Suite expansion (PSX → GBA → NES/SNES)
- **Terminal-native tools** - GameBoy aesthetic, glyphs over emoji
- **Local-first** - No external dependencies, works offline

## Next Steps

See `IMPLEMENTATION.md` for:
- TNES→iNES conversion utility
- NES save file (.sav) parser
- SNES SRM save analyzer
- Integration with r3LAY retro gaming module

## Dependencies

- Python 3.8+
- Standard library only (no external packages)

## License

MIT
