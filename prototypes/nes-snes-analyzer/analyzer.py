#!/usr/bin/env python3
"""
NES/SNES ROM Analyzer
Parses iNES/NES 2.0 and SNES ROM headers with terminal-native output
Supports TNES→iNES conversion for 3DS Virtual Console dumps
"""

import sys
import struct
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


# ========== NES iNES Format ==========

@dataclass
class INESHeader:
    """iNES ROM header (16 bytes)"""
    magic: bytes  # "NES\x1A"
    prg_rom_size: int  # 16KB units
    chr_rom_size: int  # 8KB units
    flags6: int
    flags7: int
    flags8: int
    flags9: int
    flags10: int
    
    @property
    def mapper_number(self) -> int:
        """8-bit mapper number from flags 6 and 7"""
        return ((self.flags7 & 0xF0) | (self.flags6 >> 4))
    
    @property
    def has_trainer(self) -> bool:
        return bool(self.flags6 & 0x04)
    
    @property
    def has_battery(self) -> bool:
        return bool(self.flags6 & 0x02)
    
    @property
    def mirroring(self) -> str:
        if self.flags6 & 0x08:
            return "4-screen"
        return "Vertical" if (self.flags6 & 0x01) else "Horizontal"
    
    @property
    def is_nes2(self) -> bool:
        """Check if NES 2.0 format"""
        return (self.flags7 & 0x0C) == 0x08
    
    @property
    def is_vs_system(self) -> bool:
        return bool(self.flags7 & 0x01)
    
    @property
    def is_playchoice(self) -> bool:
        return bool(self.flags7 & 0x02)


# ========== SNES Format ==========

@dataclass
class SNESHeader:
    """SNES internal ROM header (48 bytes at $FFB0-$FFDF)"""
    maker_code: str  # 2 bytes
    game_code: str  # 4 bytes
    expansion_ram_size: int
    special_version: int
    cartridge_type_sub: int
    game_title: str  # 21 bytes
    map_mode: int
    cartridge_type: int
    rom_size: int
    ram_size: int
    destination_code: int
    fixed_value: int
    mask_rom_version: int
    complement_check: int
    checksum: int
    
    @property
    def rom_size_kb(self) -> int:
        """Actual ROM size in KB"""
        return 2 ** self.rom_size
    
    @property
    def ram_size_kb(self) -> int:
        """Actual RAM size in KB"""
        return 2 ** self.ram_size if self.ram_size > 0 else 0
    
    @property
    def map_mode_name(self) -> str:
        modes = {
            0x20: "2.68MHz LoROM",
            0x21: "2.68MHz HiROM",
            0x23: "SA-1",
            0x25: "2.68MHz ExHiROM",
            0x30: "3.58MHz LoROM",
            0x31: "3.58MHz HiROM",
            0x35: "3.58MHz ExHiROM",
        }
        return modes.get(self.map_mode, f"Unknown (0x{self.map_mode:02X})")
    
    @property
    def destination(self) -> str:
        dest = {0x00: "Japan", 0x01: "USA", 0x02: "Europe (PAL)"}
        return dest.get(self.destination_code, f"Unknown (0x{self.destination_code:02X})")


# ========== Parsers ==========

def parse_ines_header(data: bytes) -> Optional[INESHeader]:
    """Parse iNES header from ROM data"""
    if len(data) < 16:
        return None
    
    magic = data[0:4]
    if magic != b'NES\x1A':
        return None
    
    return INESHeader(
        magic=magic,
        prg_rom_size=data[4],
        chr_rom_size=data[5],
        flags6=data[6],
        flags7=data[7],
        flags8=data[8],
        flags9=data[9],
        flags10=data[10],
    )


def detect_snes_header_offset(data: bytes) -> Optional[int]:
    """Detect SNES header location (accounting for copier headers)"""
    # SNES header is at $FFB0-$FFDF in ROM address space
    # For LoROM: typically at 0x7FB0 or 0xFFB0
    # For HiROM: typically at 0xFFB0 or 0x40FFB0
    
    # Check common offsets
    offsets = [
        0x7FB0,   # LoROM without copier header
        0x81B0,   # LoROM with 512-byte copier header (0x200 + 0x7FB0)
        0xFFB0,   # HiROM without copier header
        0x101B0,  # HiROM with copier header
    ]
    
    for offset in offsets:
        if offset + 48 <= len(data):
            # Check fixed value at $FFDA (offset + 0x2A)
            if offset + 0x2A < len(data) and data[offset + 0x2A] == 0x33:
                return offset
    
    return None


def parse_snes_header(data: bytes, offset: int) -> Optional[SNESHeader]:
    """Parse SNES header from ROM data at given offset"""
    if offset + 48 > len(data):
        return None
    
    header_data = data[offset:offset + 48]
    
    try:
        maker_code = header_data[0:2].decode('ascii', errors='ignore')
        game_code = header_data[2:6].decode('ascii', errors='ignore')
        game_title = header_data[16:37].decode('shift-jis', errors='ignore').strip()
        
        return SNESHeader(
            maker_code=maker_code,
            game_code=game_code,
            expansion_ram_size=header_data[13],
            special_version=header_data[14],
            cartridge_type_sub=header_data[15],
            game_title=game_title,
            map_mode=header_data[37],
            cartridge_type=header_data[38],
            rom_size=header_data[39],
            ram_size=header_data[40],
            destination_code=header_data[41],
            fixed_value=header_data[42],
            mask_rom_version=header_data[43],
            complement_check=struct.unpack('<H', header_data[44:46])[0],
            checksum=struct.unpack('<H', header_data[46:48])[0],
        )
    except Exception:
        return None


# ========== Display Functions ==========

def format_box(title: str, content: list[str], width: int = 60) -> str:
    """Terminal box with GameBoy aesthetic"""
    lines = []
    lines.append("┌" + "─" * (width - 2) + "┐")
    lines.append("│ " + title.ljust(width - 4) + " │")
    lines.append("├" + "─" * (width - 2) + "┤")
    
    for line in content:
        lines.append("│ " + line.ljust(width - 4) + " │")
    
    lines.append("└" + "─" * (width - 2) + "┘")
    return "\n".join(lines)


def display_ines_info(header: INESHeader, file_size: int) -> None:
    """Display iNES header information"""
    content = [
        f"Format: {'NES 2.0' if header.is_nes2 else 'iNES'}",
        f"Mapper: #{header.mapper_number}",
        f"PRG ROM: {header.prg_rom_size * 16} KB ({header.prg_rom_size} × 16KB)",
        f"CHR ROM: {header.chr_rom_size * 8} KB ({header.chr_rom_size} × 8KB)" if header.chr_rom_size > 0 else "CHR ROM: None (uses CHR-RAM)",
        f"Mirroring: {header.mirroring}",
        f"Battery: {'Yes' if header.has_battery else 'No'}",
        f"Trainer: {'Yes (512 bytes)' if header.has_trainer else 'No'}",
    ]
    
    if header.is_vs_system:
        content.append("System: VS System")
    elif header.is_playchoice:
        content.append("System: PlayChoice-10")
    
    expected_size = 16 + (512 if header.has_trainer else 0) + (header.prg_rom_size * 16384) + (header.chr_rom_size * 8192)
    content.append(f"File size: {file_size:,} bytes (expected: {expected_size:,})")
    
    print(format_box("NES ROM HEADER", content))


def display_snes_info(header: SNESHeader, file_size: int) -> None:
    """Display SNES header information"""
    content = [
        f"Title: {header.game_title}",
        f"Maker: {header.maker_code}  Game Code: {header.game_code}",
        f"Map Mode: {header.map_mode_name}",
        f"ROM Size: {header.rom_size_kb} KB",
        f"RAM Size: {header.ram_size_kb} KB" if header.ram_size_kb > 0 else "RAM: None",
        f"Destination: {header.destination}",
        f"Version: {header.mask_rom_version}",
        f"Checksum: 0x{header.checksum:04X}",
        f"Complement: 0x{header.complement_check:04X}",
    ]
    
    # Verify checksum
    checksum_valid = (header.checksum + header.complement_check) == 0xFFFF
    content.append(f"Checksum Valid: {'✓ Yes' if checksum_valid else '✗ No'}")
    
    content.append(f"File size: {file_size:,} bytes")
    
    print(format_box("SNES ROM HEADER", content))


# ========== Main ==========

def analyze_rom(path: Path) -> None:
    """Analyze NES or SNES ROM file"""
    if not path.exists():
        print(f"✗ File not found: {path}")
        return
    
    data = path.read_bytes()
    file_size = len(data)
    
    print(f"\n▸ Analyzing: {path.name}")
    print(f"  Size: {file_size:,} bytes\n")
    
    # Try NES format first
    ines = parse_ines_header(data)
    if ines:
        display_ines_info(ines, file_size)
        return
    
    # Try SNES format
    snes_offset = detect_snes_header_offset(data)
    if snes_offset is not None:
        snes = parse_snes_header(data, snes_offset)
        if snes:
            if snes_offset > 0:
                print(f"  ► Header offset: 0x{snes_offset:04X} (copier header detected)")
            display_snes_info(snes, file_size)
            return
    
    print("✗ Unknown ROM format (not iNES or SNES)")


def main():
    if len(sys.argv) < 2:
        print("Usage: analyzer.py <rom_file>")
        print("       analyzer.py <directory>  # batch analyze")
        sys.exit(1)
    
    target = Path(sys.argv[1])
    
    if target.is_file():
        analyze_rom(target)
    elif target.is_dir():
        # Batch mode
        extensions = {'.nes', '.smc', '.sfc', '.fig'}
        roms = [f for f in target.rglob('*') if f.suffix.lower() in extensions]
        
        if not roms:
            print(f"✗ No ROM files found in {target}")
            sys.exit(1)
        
        print(f"▸ Found {len(roms)} ROM files\n")
        for rom in sorted(roms):
            analyze_rom(rom)
            print()
    else:
        print(f"✗ Invalid path: {target}")
        sys.exit(1)


if __name__ == '__main__':
    main()
