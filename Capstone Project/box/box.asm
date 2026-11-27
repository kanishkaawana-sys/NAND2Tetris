// Box.asm - Capstone Part C (K = 32)
// Black box while any key is pressed, white (erased) otherwise.
// Rows 32..51, 1 word (16 pixels) wide, at the left edge of the screen.
//
// Variables (RAM 16, 17, 18, assigned by the assembler in this order):
//   color = -1 (black) or 0 (white)
//   addr  = address of the word being drawn
//   rows  = rows still left to draw

(MAIN_LOOP)
    @KBD
    D=M
    @SET_BLACK
    D;JNE           // any key pressed (KBD != 0) -> draw black

    @color
    M=0             // no key -> color = white
    @DRAW_START
    0;JMP

(SET_BLACK)
    @color
    M=-1            // -1 = 1111111111111111 = 16 black pixels

(DRAW_START)
    // Start address = SCREEN + 32*row. One screen row = 32 words,
    // so row 32 starts at 16384 + 32*32 = 16384 + 1024 = 17408.
    @1024           // <-- MOVE BOX VERTICALLY: change to 32 * (start row)
    D=A
    @SCREEN
    D=D+A
    @addr
    M=D

    @20             // <-- BOX HEIGHT: number of rows to draw
    D=A
    @rows
    M=D

(ROW_LOOP)
    @color
    D=M
    @addr
    A=M
    M=D             // write one word = 16 pixels of this row

    @addr
    D=M
    @32             // 32 words per row, so addr + 32 = same column, next row down
    D=D+A
    @addr
    M=D

    @rows
    M=M-1
    D=M
    @ROW_LOOP
    D;JGT           // repeat until all rows are done

    @MAIN_LOOP
    0;JMP           // go back to polling the keyboard