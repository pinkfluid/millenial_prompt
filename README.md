# Millennial Password Prompt

> A completely unnecessary, over-engineered password prompt that shows emojis instead of stars. You probably shouldn't use this in production.

## What it does

Instead of showing boring `********` or absolutely nothing like a grumpy old terminal as you type your password, it displays a string of 10 emojis derived from a hash of what you've typed so far. Finally, a password prompt that respects your need for constant visual stimulation!

```
Password: 🐪🐮🍞🐸🍳😒🦓🦖🦡😱
```

- **Empty input** → blank space (same width, no emoji)
- **Any input** → 10 emojis that change as you type

## Features

- **256 hand-picked emojis** that actually render in most terminals
- **SHA-256** hash of your password, XOR-folded across 10 display slots (80 bits of visual entropy)
- **Keystroke hiding** — the display only refreshes on a random 200–300 ms interval with added jitter, hiding the keystroke count from unintended eyes
- **No dependencies** — pure Python stdlib (`hashlib`, `termios`, `tty`, `select`)

## Usage

```python
from millenial_password_prompt import get_password

password = get_password("Enter password: ")
```

Or run it directly:

```bash
python3 millenial_password_prompt.py
```

## Warning

This was completely vibe coded, nobody should take it seriously.

