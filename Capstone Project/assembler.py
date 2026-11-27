#!/usr/bin/env python3
"""Two-pass Hack assembler (Nand to Tetris, Capstone Part B).

Usage: python3 assembler.py path/to/Program.asm
Output: path/to/Program.hack (one 16-bit binary string per line)

Custom feature (K = 32, K mod 3 = 2):
    print a warning if the same label is declared more than once.
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Lookup tables. Comp codes are 7 bits: the 'a' bit followed by cccccc.
# ---------------------------------------------------------------------------
COMP = {
    # a = 0
    "0":   "0101010", "1":   "0111111", "-1":  "0111010",
    "D":   "0001100", "A":   "0110000", "!D":  "0001101",
    "!A":  "0110001", "-D":  "0001111", "-A":  "0110011",
    "D+1": "0011111", "A+1": "0110111", "D-1": "0001110",
    "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    # a = 1
    "M":   "1110000", "!M":  "1110001", "-M":  "1110011",
    "M+1": "1110111", "M-1": "1110010", "D+M": "1000010",
    "D-M": "1010011", "M-D": "1000111", "D&M": "1000000",
    "D|M": "1010101",
}

DEST = {
    "null": "000", "M": "001", "D": "010", "MD": "011",
    "A": "100", "AM": "101", "AD": "110", "AMD": "111",
}

JUMP = {
    "null": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

# Valid Hack symbol: letters, digits, _ . $ :  (must not start with a digit)
SYMBOL_RE = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")


def init_symbol_table():
    """Return a symbol table holding the predefined Hack symbols."""
    table = {
        "SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
        "SCREEN": 16384, "KBD": 24576,
    }
    for i in range(16):
        table["R%d" % i] = i
    return table


def clean_line(line):
    """Remove the // comment and all whitespace; return '' for blank lines."""
    line = line.split("//", 1)[0]
    return re.sub(r"\s+", "", line)


def first_pass(lines):
    """Record every (LABEL) with its ROM address.

    Returns (symbols, instructions) where instructions is a list of
    (source_line_number, cleaned_text) for real A/C instructions only.
    Duplicate labels trigger a warning; the first definition is kept.
    """
    symbols = init_symbol_table()
    label_names = set()          # labels declared so far in this file
    instructions = []
    rom_address = 0

    for line_num, raw in enumerate(lines, start=1):
        line = clean_line(raw)
        if not line:
            continue

        if line.startswith("(") and line.endswith(")"):
            name = line[1:-1]
            if name in label_names:
                # Custom feature: duplicate label warning (does not crash)
                print("Warning (Line %d): Duplicate label '(%s)' already "
                      "defined at ROM address %d."
                      % (line_num, name, symbols[name]))
            elif name in symbols:
                print("Warning (Line %d): Label '(%s)' clashes with a "
                      "predefined symbol (value %d); keeping predefined value."
                      % (line_num, name, symbols[name]))
            else:
                symbols[name] = rom_address   # labels take no ROM space
                label_names.add(name)
        else:
            instructions.append((line_num, line))
            rom_address += 1

    return symbols, instructions


def encode_a_instruction(address):
    """Return '0' + 15-bit binary for an A-instruction address."""
    if not 0 <= address <= 32767:
        raise ValueError("address %d does not fit in 15 bits" % address)
    return "0" + format(address, "015b")


def encode_c_instruction(line):
    """Translate dest=comp;jump into '111' + a + cccccc + ddd + jjj."""
    dest, jump = "null", "null"
    rest = line
    if "=" in rest:
        dest, rest = rest.split("=", 1)
    if ";" in rest:
        rest, jump = rest.split(";", 1)
    comp = rest

    if comp not in COMP:
        raise ValueError("invalid comp '%s' in '%s'" % (comp, line))
    if dest not in DEST:
        raise ValueError("invalid dest '%s' in '%s'" % (dest, line))
    if jump not in JUMP:
        raise ValueError("invalid jump '%s' in '%s'" % (jump, line))

    return "111" + COMP[comp] + DEST[dest] + JUMP[jump]


def second_pass(instructions, symbols):
    """Translate each instruction to 16 bits, allocating variables from 16."""
    next_var_address = 16
    output = []

    for line_num, line in instructions:
        try:
            if line.startswith("@"):
                value = line[1:]
                if re.fullmatch(r"[0-9]+", value):
                    address = int(value)                 # plain number
                elif SYMBOL_RE.match(value):
                    if value not in symbols:             # new variable
                        symbols[value] = next_var_address
                        next_var_address += 1
                    address = symbols[value]
                else:
                    raise ValueError("invalid A-instruction '%s'" % line)
                output.append(encode_a_instruction(address))
            else:
                output.append(encode_c_instruction(line))
        except ValueError as err:
            raise ValueError("Line %d: %s" % (line_num, err)) from None

    return output


def main():
    """Read the .asm path from argv, assemble it, write the .hack file."""
    if len(sys.argv) != 2:
        print("Usage: python3 assembler.py path/to/Program.asm")
        sys.exit(1)

    asm_path = sys.argv[1]
    try:
        with open(asm_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as err:
        print("Error: cannot read '%s' (%s)" % (asm_path, err))
        sys.exit(1)

    symbols, instructions = first_pass(lines)
    try:
        binary = second_pass(instructions, symbols)
    except ValueError as err:
        print("Error: %s" % err)
        sys.exit(1)

    hack_path = os.path.splitext(asm_path)[0] + ".hack"
    with open(hack_path, "w", newline="\n") as f:   # force '\n' endings
        for word in binary:
            f.write(word + "\n")

    print("Assembled %d instructions -> %s" % (len(binary), hack_path))


if __name__ == "__main__":
    main()