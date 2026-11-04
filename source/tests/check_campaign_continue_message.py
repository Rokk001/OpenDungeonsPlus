#!/usr/bin/env python3
"""Checks that Continue campaign shows no lost-level message when no level was played."""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
campaign = (root / 'source/game/Campaign.cpp').read_text(encoding='utf-8')
menu = (root / 'source/modes/MenuModeCampaign.cpp').read_text(encoding='utf-8')

start = campaign.index('bool Campaign::importDefinition(')
body = campaign[start:campaign.index('bool Campaign::importProgress(')]
assert re.search(r'if\(!mActive\)\s*\{\s*mPlayedLevel = mLevels\.size\(\);\s*mPlayedLevelWon = false;', body), \
    'importDefinition must mark that no level was played'
assert 'return !mLevels.empty();' in body
assert 'lost-level message' in menu and 'OD_LOG_INF("Campaign menu shows the lost-level message' in menu, \
    'the lost-level message must be logged'
print('check_campaign_continue_message: ok')
sys.exit(0)
