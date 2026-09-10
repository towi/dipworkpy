# Rule-Switches: `convoy_via_explicit`

## Was der Schalter regelt

Gilgamesch B.3.2.14 Satz 1: Eine als *mve [Convoy]* markierte Bewegung ist
**ausschließlich** eine Konvoibewegung — ohne (überlebende) Konvoier bleibt
die Armee stehen, selbst wenn das Ziel auch auf dem Landweg erreichbar wäre.

Standard-Diplomacy (Dippy/DipNet) kennt diese strenge Lesart nicht: dort ist
ein *via convoy*-Marker rein informativ bzw. existiert gar nicht; ob eine
Bewegung zur See geht, entscheidet allein, ob ein **con-Order** für diese
Bewegung vorliegt.

Der Schalter `Switches.convoy_via_explicit` (Default **False**)
schaltet zwischen beiden Lesarten:

| Stellung | Semantik |
|---|---|
| `False` (Default, Dippy/DipNet) | Das `[Convoy]`-Flag (`Order.via_convoy`) ist rein informativ, **solange ein Landweg existiert**: dann entscheidet allein die con-Order (angrenzend oder nicht). Eine markierte Bewegung **ohne Landweg** ist ein eindeutiger Konvoi-Versuch — sie wird zur Konvoibewegung und scheitert bei toter Route in k1 (`$criv`, Stand mit **voller** Verteidigungsstärke; DipNet *no convoy*). Zwei angrenzende Armeen können mit einer con-Order die **Plätze tauschen**; eine "beanspruchte" angrenzende Bewegung mit unterbrochenem Konvoi **steht** (kein Land-Fallback). |
| `True` (Gilgamesch B.3.2.14 scharf) | Das Flag allein erzwingt die Seeroute (ohne Route: Scheitern in k1 `$criv`, kein Land-Fallback). Unmarkierte angrenzende Bewegungen bleiben Landbewegungen und ignorieren bestellte Konvois (Satz 3); unmarkierte nicht-angrenzende nutzen den Konvoi (Notwendigkeit). |

## Wo der Schalter wirkt — Architektur

**Nicht im Conflicter.** Der Konflikt-Löser ist bewusst geografie- und
schalterunabhängig: Konvoibewegungen erreichen ihn bereits als
`OrderType.cmve`. Die Entscheidung Land/See trifft der **Order-Vorverarbeiter**
(`dipworkpy/order_prep.py`, Klassifikationskern:
`dipworkpy.geography.convoy.classify_cmove_candidates`), der vor dem Konflikt
läuft und die Orders umschreibt. Die Runde (`round_full`) verkabelt das:
Syntax → **Prep** → Geography → Conflict.

```
            via_convoy + Switches.convoy_via_explicit
                        │
                        ▼
   ┌──────────── order_prep (geografie-beachtend) ───────────┐
   │  mve ──(con-Order / Flag / Switch / Karte)──► cmve       │
   └──────────────────────────────────────────────────────────┘
                        │  cmve = "das ist eine Konvoibewegung"
                        ▼
   ┌──────────── conflict_game (blind dafür) ─────────────────┐
   │  cmve → t_order.cmove; tote Route → $criv/$fn6: steht    │
   └──────────────────────────────────────────────────────────┘
```

(Subfeld→Oberfeld-Normierung wird später ebenfalls in den Vorverarbeiter
wandern; heute macht das noch die Geography-Phase.)

## Dieselbe Situation, beide Stellungen

Brett (Standard-Map, real): `Con` und `Bul` grenzen direkt an; die Flotte auf
`AEG` **befiehlt kein con**. Die Armee-Order trägt das via-Flag.

### Default — `convoy_via_explicit=false` (Beispiel [16](examples/dwex/16_switch_convoy_via_default.dwex))

```dwex
@dwex
title: B.3.2.14 Satz 1 -- via ohne Konvoier: Default (convoy_via_explicit=false)
map {
  Con LCB 0,0
  Bul LC 1,0
  AEG O 0.5,0.8
  Con -- Bul
  Con --F AEG
  AEG --F Bul
}
orders {
  Tu A Con mve Bul via  # via-Flag gesetzt, aber kein con befohlen
  Tu F AEG hld          # Flotte da, konvoiert aber nicht
}
@end
```

Ausgang: Landzug — die Armee läuft von `Con` nach `Bul`, das Flag wird
ignoriert. (Genau dieser Fall war die DipNet-Divergenz `h9QEPT6s5…`: DipNet
zieht per Land, Gilgamesch scharf würde stehen bleiben.)

### Gilgamesch — `convoy_via_explicit=true` (Beispiel [17](examples/dwex/17_switch_convoy_via_explicit.dwex))

```dwex
@dwex
title: B.3.2.14 Satz 1 -- via ohne Konvoier: Gilgamesch (convoy_via_explicit=true)
switches {
  convoy_via_explicit
}
map {
  Con LCB 0,0
  Bul LC 1,0
  AEG O 0.5,0.8
  Con -- Bul
  Con --F AEG
  AEG --F Bul
}
orders {
  Tu A Con mve Bul via !  # via-Flag zwingt zur Seeroute: kein Konvoier -> steht
  Tu F AEG hld            # Flotte da, konvoiert aber nicht
}
@end
```

Ausgang: Die Armee **bleibt stehen** (fehlgeschlagene Konvoibewegung,
volle Verteidigungsstärke) — der Zug schneidet nichts, die Bewegung wird mit
`succeeds=False` gemeldet (`!`).

### Default-Swap (nur mit con-Order, ohne Flag)

```dwex
@dwex
title: Default: con-Order beansprucht die angrenzende Bewegung -- Swap
map {
  Con LCB 0,0
  Bul LC 1,0
  BLA O 0.5,0.8
  Con -- Bul
  Con --F BLA
  BLA --F Bul
}
orders {
  Tu A Con mve Bul  # angrenzend, unmarkiert
  Ru A Bul mve Con  # Gegenbewegung
  Tu F BLA con Con  # konvoiert genau Con->Bul
}
@end
```

Ausgang: `Con->Bul` wird zur Konvoibewegung (`cmve`), `Bul->Con` bleibt
Landzug — die Armeen **tauschen die Plätze** (kein Randkonflikt für cmove
vs. nmove, B.3.2.13/C.2.3). Wird die Flotte vertrieben, **steht** die
beanspruchte Bewegung (kein Land-Fallback). Mit `convoy_via_explicit=true`
wäre derselbe Zug ein gewöhnlicher Head-to-Head — beide bleiben stehen.

## Tests

- `tests/test_b3214_convoy_via.py` — Schalterstellungen end-to-end
  (`round_full`) plus Klassifikator-Einheitstests (Beide Stellungen,
  cmve-Durchreichung, Default=False des Engine-Switches).
- `tests/test_conflict_datc.py` — B.3.2.13/B.3.2.14-Fälle; die
  Gilgamesch-strengen Pins (Satz 1/Satz 3, Swap-Regelung) setzen den
  Schalter explizit auf `True`.
- `doc/examples/dwex/16…/17…` — die beiden dwex-Blöcke oben sind
  ausführbare Beispiele (`tests/test_dwex_examples.py` adjudiziert sie).
