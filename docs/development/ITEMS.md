# Items, trading and potions

Creatures have six equipment slots: right hand, left hand, head, armour, boots and
one ring. Weapons must match their spawn weapon class, and shields need a shield
hand. Four inventory slots hold spare items and potions. Equipment changes happen
outside combat; unwanted inventory can be sold to a merchant.

Items have Poor, Common, Rare or Epic quality. Common items require level 1, Rare
level 10 and Epic level 20. Bonuses are rolled when an item is created. Rare items
have one special effect and Epic items have two. Each Epic item line can exist only
once on a map. Item bags, hero loot and workshop-opened item boxes provide items.
The keeper can carry bags and give their contents to an own creature.

The merchant buys and sells goods stored on the room's tables. Each table starts
with three goods places; research scales capacity, rounded down per table. A
creature selling an item receives half its base price, less the keeper's margin;
the keeper receives the margin share. Buying costs the base price plus the margin.
Keeper purchases use the base price, and the keeper cannot sell directly. Margin
starts at 10 percent and can be set from 0 to 50 percent. Fair mode reserves wanted
goods for the creature with the highest item rating; Profit mode favors the highest
level, breaking ties by base wage. Reservations expire after 60 turns. Trading affects creature mood.
Fractional gold is retained.

Creatures have one potion slot at levels 1-9, two at 10-19 and three from level 20.
Combat drinking uses these slots. Outside combat, empty slots refill from inventory
and creatures can buy suitable potions. Healing and mana potions restore resources;
Lifespring restores both, Thaw ends freezing, and timed potions grant their listed
effects. A useful gifted potion is drunk at once; otherwise it goes into a free
potion or inventory slot, or remains in its bag. Every gift grants the listed mood
bonus, even when the bag remains on the floor.

Herb gardens grow Bloodroot, Moonlily and Ironfern; Sunthorn needs its cultivation
research. Plants progress through sprout, young and ripe stages. Gardeners harvest
ripe beds, and workers carry herb bundles to an alchemy lab. Brewers reserve the
recipe's herbs when brewing starts and retain progress while work pauses. Completed
potions appear as bags in the lab, and workers carry them to merchant tables or a treasury.
The lab window lists recipes, brewers, remaining time and herb stock. Garden and
lab research shorten growth and brewing time; tool research shortens opening of
Rare and Epic item boxes in the workshop.

Poor spawn-weapon and shield bags retain their equipment name and equipment identity, cost 20 gold, and use a matching
weapon-class base icon with the grey Poor frame. Rolled Poor gear is carried separately from the permanent spawn fallback.
Hero item qualities interpolate linearly from 60/35/4/1 percent at level 1 to 2/17/62/19 at level 30
(Poor/Common/Rare/Epic). Network version 0.7.4 rejects clients using the previous item packet format.

Automatic healing, mana and combat-buff drinks are limited to combat; Thaw may be used whenever frozen.
Outside combat, creatures refill their potion slots and shop. Only enemy workers loot herb bundles by carrying them
to their own laboratory; fighters have no herb inventory. A split laboratory divides herbs by tile count and retains
integer remainders in the original room. When a cauldron is removed, reserved brews keep their progress in another
free cauldron, or pause in their surviving room until a cauldron becomes available; paused brews are saved with the room.
The merchant is visited for buying and selling, rather than as an additional leisure destination.
Epic serials identify unique instances internally and in the log; the profile adds no serial text.

K opens merchant stock and trading settings; L opens the laboratory overview, while M keeps the full map.
Creature profiles show equipment, potion and inventory images with quality frames and item tooltips.
In the editor, item boxes and bags share a catalogue/quality or random-content selection; item bonuses are rolled by the server.
