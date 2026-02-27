#!/usr/bin/env python3
"""
Password prompt that shows emojis derived from a hash of what you type,
instead of stars or nothing.

- Empty input  → blank placeholder
- Any input    → SHA-256 XOR-folded into 10 bytes, each indexing one emoji
                 (256 emojis × 10 positions = 80 bits of visual entropy)
"""
import sys
import tty
import termios
import hashlib
import select
import random
import time

# 256 hand-picked emojis that render reliably across terminals.
EMOJI_MAP = [
    # 0-15   faces
    '😀','😁','😂','🤣','😃','😄','😅','😆','😉','😊','😋','😎','😍','😘','🥰','😗',
    # 16-31  faces
    '😙','😚','🙂','🤗','🤩','🤔','🤨','😐','😑','😶','🙄','😏','😣','😥','😮','🤐',
    # 32-47  faces
    '😯','😪','😫','🥱','😴','😌','😛','😜','😝','🤤','😒','😓','😔','😕','🙃','🤑',
    # 48-63  faces
    '😲','🙁','😖','😞','😟','😤','😢','😭','😦','😧','😨','😩','🤯','😬','😰','😱',
    # 64-79  faces / costumes
    '🥵','🥶','😳','🤪','😵','🥴','🤧','🤒','🤕','🤠','😷','🥸','🤡','👻','💀','👽',
    # 80-95  animals
    '🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐸','🐵','🙈',
    # 96-111 animals
    '🙉','🙊','🐔','🐧','🐦','🐤','🦆','🦅','🦉','🦇','🐺','🐗','🐴','🦄','🐝','🐛',
    # 112-127 animals
    '🦋','🐌','🐞','🐜','🦟','🦗','🦂','🐢','🐍','🦎','🦖','🦕','🐙','🦑','🦐','🦞',
    # 128-143 sea / big animals
    '🦀','🐡','🐟','🐠','🐬','🐳','🐋','🦈','🐊','🐅','🐆','🦓','🦍','🐘','🦛','🦏',
    # 144-159 farm / misc animals
    '🐪','🐫','🦒','🦘','🐃','🐂','🐄','🐎','🐖','🐏','🐑','🦙','🐐','🦌','🐕','🐩',
    # 160-175 small animals / birds
    '🐈','🐓','🦃','🦚','🦜','🦢','🦩','🕊','🐇','🦝','🦨','🦡','🦦','🦥','🐁','🐀',
    # 176-191 fruit
    '🍎','🍊','🍋','🍇','🍓','🍈','🍒','🍑','🥭','🍍','🥝','🍅','🫐','🍆','🥑','🥦',
    # 192-207 vegetables / bread
    '🥬','🥒','🌽','🥕','🧄','🧅','🥔','🍠','🥐','🥖','🍞','🥨','🧀','🥚','🍳','🧈',
    # 208-223 meat / fast food
    '🥞','🧇','🥓','🥩','🍗','🍖','🌭','🍔','🍟','🍕','🥪','🥙','🧆','🌮','🌯','🥗',
    # 224-239 sports
    '⚽','🏀','🏈','⚾','🥎','🎾','🏐','🏉','🥏','🎱','🏓','🏸','🥊','🥋','🎽','🛹',
    # 240-255 nature / music / misc
    '🌈','🔥','💧','❄','🌊','⭐','🌟','💫','✨','🎵','🎶','🎸','🎹','🎺','🎻','🎮',
]

assert len(EMOJI_MAP) == 256, f"Need 256 emojis, got {len(EMOJI_MAP)}"

DISPLAY_LEN = 10  # 10 emoji slots; all 32 SHA-256 bytes are folded in via XOR


def password_to_emojis(password: str) -> str:
    """Return a fixed-length emoji string derived from the password hash."""
    if not password:
        return '  ' * DISPLAY_LEN  # visible blank placeholder (2 spaces per emoji slot)
    digest = hashlib.sha256(password.encode('utf-8')).digest()
    # XOR-fold all 32 bytes into DISPLAY_LEN bytes so every bit contributes.
    folded = bytearray(DISPLAY_LEN)
    for i, b in enumerate(digest):
        folded[i % DISPLAY_LEN] ^= b
    return ''.join(EMOJI_MAP[b] for b in folded)


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
