#!/bin/bash
cd "/Users/manoshranjan/1g 1 million"
VENV_PY="/Users/manoshranjan/1g 1 million/virality_agent/.venv/bin/python"
PYTHONPATH="/Users/manoshranjan/1g 1 million/virality_agent" "$VENV_PY" -m virality.cli mine @liamottley @nick_saraev @brettmalinowski --per-creator 3 --rounds 2
