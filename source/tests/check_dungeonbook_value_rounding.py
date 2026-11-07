"""Check that the game values of the statistics text and the Dungeonbook are rounded (owner decision 830).

Static check, no game needed. The owner saw "Experience: 51.59700000000005" and "56.51100000000007" on the values
sheet: experience, hit points, gold and the ratings are sums of floating point steps, and the exact text of such a sum
shows its error. They are now written with at most two decimals and without zeros at the end.

1. Wiring. Every writer of these values uses Creature::formatRoundedNumber: the statistics text (Experience, HP,
   Gold), the server lines of the Dungeonbook (attack rating, defense rating, raw damage per second) and the values
   sheet (attributes, critical chance, ratings and defenses through formatProfileValue). The client rounds the
   numbers of the statistics text again, so the raw sum of an older server is not shown either.
2. Behaviour. A Python replica of formatRoundedNumber, read against the C++ code, is run on the owner's values, on
   simulated experience, gold and hit point sums and on every magnitude: the text has at most two decimals, no zero
   at the end, no "-0", and it is the nearest such number.
"""
from pathlib import Path
import random
import re

repo = Path(__file__).resolve().parents[2]
creature_cpp = (repo / 'source/entities/Creature.cpp').read_text()
creature_h = (repo / 'source/entities/Creature.h').read_text()
server = (repo / 'source/network/ODServer.cpp').read_text()
social = (repo / 'source/render/SocialWindow.cpp').read_text()


def function_of(text, signature):
    body = text[text.index(signature):]
    return body[:body.index('\n}\n')]


# 1. Wiring
assert 'static std::string formatRoundedNumber(double value);' in creature_h
for tree in ('source',):
    for path in (repo / tree).rglob('*'):
        if path.suffix in ('.cpp', '.h'):
            assert 'formatExactNumber' not in path.read_text(errors='replace'), path
rounded = function_of(creature_cpp, 'std::string Creature::formatRoundedNumber(double value)')
decimals = int(re.search(r'static const int32_t ROUNDED_DECIMALS = (\d+);', creature_cpp)[1])
fixed_max = float(re.search(r'static const double ROUNDED_FIXED_MAX = ([0-9.e+]+);', creature_cpp)[1])
assert decimals == 2 and fixed_max == 1e15, (decimals, fixed_max)
# The order of the steps is what the replica below does
steps = ('if(!std::isfinite(value))', 'stream.imbue(std::locale::classic());',
         'if(std::fabs(value) >= ROUNDED_FIXED_MAX)', 'stream << std::scientific;', 'stream << std::fixed;',
         'stream << std::setprecision(ROUNDED_DECIMALS) << value;', "text.find('e')",
         "while(!mantissa.empty() && (mantissa[mantissa.size() - 1] == '0'))",
         "if(!mantissa.empty() && (mantissa[mantissa.size() - 1] == '.'))", 'if(mantissa == "-0")',
         'return mantissa + suffix;')
positions = [rounded.index(step) for step in steps]
assert positions == sorted(positions), 'formatRoundedNumber does its steps in another order than the replica'
stats = function_of(creature_cpp, 'std::string Creature::getStatsText(const Seat* viewer)')
for fragment in ('"Experience: " << formatRoundedNumber(mExp)',
                 '"HP: " << formatRoundedNumber(getHP()) << " / " << formatRoundedNumber(mMaxHP)',
                 '"Gold: " << formatRoundedNumber(mGoldCarried)'):
    assert fragment in stats, fragment
for raw in ('<< mExp', '<< getHP()', '<< mMaxHP', '<< mGoldCarried'):
    assert raw not in stats, 'a raw value is written: ' + raw
for getter in ('getAttackRating', 'getDefenseRating', 'getRawDamagePerSecond'):
    assert 'Creature::formatRoundedNumber(creature->%s())' % getter in server, getter
assert 'return groupThousands(Creature::formatRoundedNumber(value));' in function_of(
    social, 'std::string formatProfileValue(double value)')
for field in ('critical', 'attackRating', 'defenseRating', 'physicalDefense', 'magicalDefense', 'elementDefense'):
    assert 'formatProfileValue(entry.%s)' % field in social, field
assert 'breakAttributeValue(formatProfileValue(values[i]))' in social
assert 'const double values[] = {entry.strength, entry.dexterity, entry.life, entry.mana};' in social
statistics = function_of(social, 'std::string formatStatisticsNumbers(const std::string& value)')
assert 'parser.imbue(std::locale::classic());' in statistics
assert '(isNumber ? formatProfileValue(number) : parts[i])' in statistics, 'the statistics numbers are rounded'
values = function_of(social, 'void SocialWindow::refreshValues(')
assert 'line.slots ? countFilledSlots(value) : formatStatisticsNumbers(value)' in values
for window, label in (('Experience', 'Experience'), ('HitPoints', 'HP'), ('Gold', 'Gold'),
                      ('DamagePerSecond', 'Raw damage per second')):
    assert '{"%s", "%s", false}' % (window, label) in values, window


# 2. Behaviour
def rounded_number(value):
    """Replica of Creature::formatRoundedNumber."""
    if value != value:
        return 'nan'
    if value in (float('inf'), float('-inf')):
        return '-inf' if value < 0 else 'inf'
    text = ('%.*e' if abs(value) >= fixed_max else '%.*f') % (decimals, value)
    mantissa, sep, exponent = text.partition('e')
    while mantissa and mantissa[-1] == '0':
        mantissa = mantissa[:-1]
    if mantissa and mantissa[-1] == '.':
        mantissa = mantissa[:-1]
    if mantissa == '-0':
        mantissa = '0'
    return mantissa + sep + exponent


def group_thousands(number):
    """Replica of groupThousands in SocialWindow.cpp."""
    if any(c in number for c in 'eEin'):
        return number
    sign = 1 if number.startswith('-') else 0
    whole = number.find('.') if '.' in number else len(number)
    while whole > sign + 3:
        number = number[:whole - 3] + ',' + number[whole - 3:]
        whole -= 3
    return number


def statistics_numbers(value):
    """Replica of formatStatisticsNumbers: every plain number part rounded and grouped."""
    if not value:
        return '-'
    parts = value.split(' / ')
    shown = []
    for part in parts:
        try:
            number = float(part)
            is_number = part.strip() == part and part.lower() not in ('nan', 'inf', '-inf', 'infinity')
        except ValueError:
            is_number = False
        shown.append(group_thousands(rounded_number(number)) if is_number else part)
    return ' / '.join(shown)


FIXED = re.compile(r'-?[0-9]+(\.[0-9]{0,%d}[1-9])?' % (decimals - 1))
EXPONENT = re.compile(r'-?[1-9](\.[0-9]{0,%d}[1-9])?e[+-][0-9]{2,3}' % (decimals - 1))


def assert_rounded(value):
    text = rounded_number(value)
    assert FIXED.fullmatch(text) or (abs(value) >= fixed_max and EXPONENT.fullmatch(text)), (value, text)
    assert text != '-0' and (not text.startswith('-') or float(text) < 0), ('a negative zero is shown', value, text)
    if abs(value) < fixed_max:
        # the nearest number with two decimals (the binary value decides a tie, as printf does)
        assert abs(float(text) - value) <= 0.005 * (1 + 1e-9) + abs(value) * 2e-16, (value, text)
    else:
        assert abs(float(text) - value) <= abs(value) * 0.0051, (value, text)
    return text


# The owner's values (screenshot 2026-11-07 19:25) and other shown numbers
for value, text in ((51.59700000000005, '51.6'), (56.51100000000007, '56.51'), (70.0, '70'), (0.0, '0'),
                    (4.5864, '4.59'), (14.8, '14.8'), (41.666666666666664, '41.67'), (0.1 + 0.2, '0.3'),
                    (-0.004, '0'), (-1234.5, '-1234.5'), (1e20, '1e+20'), (-9.8765e300, '-9.88e+300'),
                    (999.999, '1000'), (2.5, '2.5'), (float('nan'), 'nan'), (float('-inf'), '-inf')):
    assert rounded_number(value) == text, (value, rounded_number(value), text)
assert group_thousands(rounded_number(42600.004)) == '42,600'
# The client path: the raw text of an older server is rounded, slots and words stay
for text, shown in (('51.59700000000005', '51.6'), ('70 / 70', '70 / 70'), ('69.99999999999999 / 70', '70 / 70'),
                    ('0 / 0', '0 / 0'), ('42600.5', '42,600.5'), ('3 / 2', '3 / 2'), ('', '-'),
                    ('Healing Draught / -', 'Healing Draught / -'), ('4.5864', '4.59')):
    assert statistics_numbers(text) == shown, (text, statistics_numbers(text), shown)

# Simulated sums of the game: experience gained in small steps, gold in fractions, hit points healed and hurt
rng = random.Random(830)
sums = 0
for run in range(400):
    exp = gold = 0.0
    hp = max_hp = rng.choice((40.0, 70.0, 155.0, 1200.0))
    for _ in range(rng.randint(10, 400)):
        exp += rng.choice((0.1, 0.2, 0.627, 0.3, 1.1, 0.07, 0.013)) * rng.randint(1, 9)
        gold += rng.choice((0.1, 0.25, 0.3, 1.0 / 3)) * rng.randint(1, 50)
        hp = min(max_hp, max(0.0, hp + rng.choice((-1, 1)) * rng.choice((0.1, 0.35, 0.7, 2.2))))
        for value in (exp, gold, hp, max_hp, -exp):
            assert_rounded(value)
            sums += 1
# Every magnitude and form
for exponent in range(-320, 308):
    for mantissa in (1.0, 9.8765432109876543, 1.0000000000000002, 5.0, 4.995, 9.995):
        for sign in (1, -1):
            assert_rounded(sign * mantissa * 10.0 ** exponent if exponent > -300 else sign * mantissa * 1e-300)
# The longest text the values sheet can get stays what check_dungeonbook_profile_layout.py measures
longest = max((group_thousands(rounded_number(float('-9.8765432109876543e%d' % e))) for e in range(-320, 308)), key=len)
assert longest == '-987,654,321,098,765.38', longest
print('value rounding ok: Experience 51.59700000000005 -> %s, 56.51100000000007 -> %s, %d simulated sums and every '
      'magnitude with at most %d decimals; longest value %s' % (
          rounded_number(51.59700000000005), rounded_number(56.51100000000007), sums, decimals, longest))
