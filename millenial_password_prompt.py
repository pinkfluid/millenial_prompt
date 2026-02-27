#!/usr/bin/env python3
"""
Password prompt that shows emojis derived from a hash of what you type,
instead of stars or nothing.

- Empty or short input → stars placeholder (at least 4 chars required)
- Input (>= 4 chars)  → SHA-256 XOR-folded into 3 bytes, each indexing one emoji
                        (8 emojis × 3 positions = 9 bits of visual entropy)
"""
import sys
import tty
import termios
import hashlib
import select
import random
import time

# 8 hand-picked emojis for the hash palette.
EMOJI_MAP = [
    '🍄', '🌻', '🌲', '🌊', '🔮', '🎃', '👻', '🎱'
]

assert len(EMOJI_MAP) == 8, f"Need 8 emojis for palette, got {len(EMOJI_MAP)}"

DISPLAY_LEN = 3  # 3 emoji slots; all 32 SHA-256 bytes are folded in via XOR


def password_to_emojis(password: str) -> str:
    """Return a fixed-length emoji string derived from the password hash."""
    if not password:
        return '  ' * DISPLAY_LEN
    if len(password) < 4:
        # Show random emojis for the first 3 characters
        return ''.join(random.choice(EMOJI_MAP) for _ in range(DISPLAY_LEN))
    digest = hashlib.sha256(password.encode('utf-8')).digest()
    # XOR-fold all 32 bytes into DISPLAY_LEN bytes so every bit contributes.
    folded = bytearray(DISPLAY_LEN)
    for i, b in enumerate(digest):
        folded[i % DISPLAY_LEN] ^= b
    return ''.join(EMOJI_MAP[b % len(EMOJI_MAP)] for b in folded)


def get_password(prompt: str = 'Password: ') -> str:
    """Read a password from the terminal, displaying emojis instead of characters.

    Uses select() with a timeout instead of threads. The display only updates
    when input has been idle for 200–300 ms, so keystrokes aren't counted.
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    chars: list[str] = []
    dirty = False
    deadline = time.monotonic() + 0.2 + random.uniform(0, 0.1)

    try:
        tty.setraw(fd)
        sys.stdout.write('\r' + prompt + password_to_emojis(''))
        sys.stdout.flush()

        while True:
            # Wait for input up to the next tick; update display if dirty.
            timeout = max(0.0, deadline - time.monotonic())
            ready, _, _ = select.select([sys.stdin], [], [], timeout)

            if not ready:
                # Tick fired — refresh display if something changed.
                if dirty:
                    dirty = False
                    sys.stdout.write('\r' + prompt + password_to_emojis(''.join(chars)))
                    sys.stdout.flush()
                # Schedule next tick.
                deadline = time.monotonic() + 0.2 + random.uniform(0, 0.1)
                continue

            ch = sys.stdin.buffer.read(1)

            # Handle multi-byte UTF-8 sequences
            if ch[0] & 0x80:
                if ch[0] & 0xE0 == 0xC0:
                    ch += sys.stdin.buffer.read(1)
                elif ch[0] & 0xF0 == 0xE0:
                    ch += sys.stdin.buffer.read(2)
                elif ch[0] & 0xF8 == 0xF0:
                    ch += sys.stdin.buffer.read(3)
                char = ch.decode('utf-8', errors='replace')
            else:
                char = ch.decode('ascii', errors='replace')

            if char in ('\r', '\n'):
                break
            elif char in ('\x7f', '\x08'):  # backspace / delete
                if chars:
                    chars.pop()
                    dirty = True
            elif char == '\x03':            # Ctrl-C
                raise KeyboardInterrupt
            elif char == '\x04':            # Ctrl-D
                break
            elif char.isprintable():
                chars.append(char)
                dirty = True

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write('\n')
        sys.stdout.flush()

    return ''.join(chars)


if __name__ == '__main__':
    try:
        pw = get_password()
    except KeyboardInterrupt:
        print('\nCancelled.')
