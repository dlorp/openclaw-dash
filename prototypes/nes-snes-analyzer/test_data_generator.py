#!/usr/bin/env python3
"""
Test ROM data generator for NES/SNES analyzer
Creates sample ROM files for testing without requiring actual ROMs
"""

import struct
from pathlib import Path


def generate_ines_rom(
    output_path: Path,
    prg_rom_banks: int = 2,
    chr_rom_banks: int = 1,
    mapper: int = 0,
    has_battery: bool = False,
    has_trainer: bool = False,
    mirroring: str = "vertical"
) -> None:
    """Generate a valid iNES ROM file"""
    
    # Build flags
    flags6 = (mapper & 0x0F) << 4
    if mirroring == "vertical":
        flags6 |= 0x01
    if has_battery:
        flags6 |= 0x02
    if has_trainer:
        flags6 |= 0x04
    
    flags7 = (mapper & 0xF0)
    
    # Build header
    header = bytearray([
        0x4E, 0x45, 0x53, 0x1A,  # "NES\x1A"
        prg_rom_banks,
        chr_rom_banks,
        flags6,
        flags7,
        0, 0, 0, 0, 0, 0, 0, 0  # Unused
    ])
    
    # Build ROM data
    data = bytearray(header)
    
    # Add trainer if present
    if has_trainer:
        data.extend(b'\x00' * 512)
    
    # Add PRG ROM (fill with pattern)
    prg_size = prg_rom_banks * 16384
    for i in range(prg_size):
        data.append((i * 7) & 0xFF)  # Simple pattern
    
    # Add CHR ROM if present
    if chr_rom_banks > 0:
        chr_size = chr_rom_banks * 8192
        for i in range(chr_size):
            data.append((i * 13) & 0xFF)  # Different pattern
    
    output_path.write_bytes(data)
    print(f"✓ Generated iNES ROM: {output_path.name} ({len(data):,} bytes)")


def generate_snes_rom(
    output_path: Path,
    title: str = "TEST ROM",
    map_mode: int = 0x20,
    rom_size_kb: int = 512,
    ram_size_kb: int = 0,
    destination: int = 0x01,
    add_copier_header: bool = False
) -> None:
    """Generate a valid SNES ROM file"""
    
    # Calculate size values
    rom_size_val = 0
    temp = rom_size_kb
    while temp > 1:
        rom_size_val += 1
        temp //= 2
    
    ram_size_val = 0
    if ram_size_kb > 0:
        temp = ram_size_kb
        while temp > 1:
            ram_size_val += 1
            temp //= 2
    
    # Build ROM data (fill with pattern)
    rom_data = bytearray()
    
    # Add copier header if requested (512 bytes)
    if add_copier_header:
        rom_data.extend(b'\x00' * 512)
    
    # Calculate header offset
    if map_mode in [0x20, 0x30]:  # LoROM
        header_offset = 0x7FB0
    else:  # HiROM
        header_offset = 0xFFB0
    
    # Fill ROM with pattern up to header
    for i in range(header_offset):
        rom_data.append((i * 11) & 0xFF)
    
    # Build SNES header (48 bytes at $FFB0-$FFDF)
    maker_code = b'99'
    game_code = b'TEST'
    
    # Pad/truncate title to 21 bytes
    title_bytes = title.encode('ascii', errors='ignore')[:21].ljust(21, b' ')
    
    header = bytearray()
    header.extend(maker_code)  # 0-1: Maker code
    header.extend(game_code)   # 2-5: Game code
    header.extend(b'\x00' * 7) # 6-12: Fixed value
    header.append(0x00)         # 13: Expansion RAM size
    header.append(0x00)         # 14: Special version
    header.append(0x00)         # 15: Cartridge type sub
    header.extend(title_bytes)  # 16-36: Game title
    header.append(map_mode)     # 37: Map mode
    header.append(0x00)         # 38: Cartridge type
    header.append(rom_size_val) # 39: ROM size
    header.append(ram_size_val) # 40: RAM size
    header.append(destination)  # 41: Destination code
    header.append(0x33)         # 42: Fixed value
    header.append(0x00)         # 43: Mask ROM version
    
    # Calculate checksum (simplified - just sum all bytes)
    # In real ROMs this would be more complex for non-power-of-2 sizes
    temp_checksum = sum(rom_data) & 0xFFFF
    complement = (0xFFFF - temp_checksum) & 0xFFFF
    
    header.extend(struct.pack('<H', complement))    # 44-45: Complement check
    header.extend(struct.pack('<H', temp_checksum)) # 46-47: Checksum
    
    # Add header to ROM
    rom_data.extend(header)
    
    # Add vectors (16 bytes at $FFE0-$FFEF, 16 bytes at $FFF0-$FFFF)
    # Point all vectors to $8000 (simplified)
    vectors = bytearray()
    for _ in range(16):  # 16 2-byte vectors
        vectors.extend(b'\x00\x80')
    rom_data.extend(vectors)
    
    # Pad to full ROM size
    target_size = (rom_size_kb * 1024) + (512 if add_copier_header else 0)
    while len(rom_data) < target_size:
        rom_data.append(0xFF)
    
    output_path.write_bytes(rom_data)
    print(f"✓ Generated SNES ROM: {output_path.name} ({len(rom_data):,} bytes)")


def main():
    """Generate test ROM files"""
    output_dir = Path("test_roms")
    output_dir.mkdir(exist_ok=True)
    
    print("▸ Generating test ROM files...\n")
    
    # NES ROMs
    generate_ines_rom(
        output_dir / "test_basic.nes",
        prg_rom_banks=2,
        chr_rom_banks=1,
        mapper=0
    )
    
    generate_ines_rom(
        output_dir / "test_battery.nes",
        prg_rom_banks=4,
        chr_rom_banks=0,  # Uses CHR-RAM
        mapper=1,
        has_battery=True
    )
    
    generate_ines_rom(
        output_dir / "test_trainer.nes",
        prg_rom_banks=2,
        chr_rom_banks=1,
        mapper=0,
        has_trainer=True
    )
    
    # SNES ROMs
    generate_snes_rom(
        output_dir / "test_lorom.smc",
        title="LOROM TEST",
        map_mode=0x20,
        rom_size_kb=512
    )
    
    generate_snes_rom(
        output_dir / "test_hirom.sfc",
        title="HIROM TEST",
        map_mode=0x21,
        rom_size_kb=1024,
        ram_size_kb=8
    )
    
    generate_snes_rom(
        output_dir / "test_copier.smc",
        title="COPIER HEADER TEST",
        map_mode=0x20,
        rom_size_kb=256,
        add_copier_header=True
    )
    
    print(f"\n✓ All test ROMs generated in {output_dir}/")


if __name__ == '__main__':
    main()
