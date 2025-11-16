# Complete Diplomacy Round Evaluation - Pascal Implementation Analysis

This document analyzes how the Pascal reference implementation (`pas/SOURCE/`) handles a complete Diplomacy round, from order input to final game state. This serves as a specification for extending the Python implementation beyond pure conflict resolution.

## Executive Summary

The Pascal implementation provides a complete Diplomacy game engine with **5 main phases** orchestrated by `DIP_RUN.pas`. The current Python implementation only covers **Phase 3 (Conflict Resolution)**.

## Main Program Flow (DIP_RUN.pas)

The execution order is controlled by boolean flags and follows this sequence:

```pascal
// Main execution order (lines 402-437)
if doScanner    then Scan_Game;     // Phase 1: Parse human orders
if doParser     then Pars_Game;     // Phase 2: Validate and convert orders
if doConflicter then Conflict_Game; // Phase 3: Resolve conflicts (CURRENT PYTHON SCOPE)
if doWinter     then Winter_Game;   // Phase 4: Handle retreats and build/disband
if doOutputPlain then Output_Plain; // Phase 5: Generate output
if doMap        then Draw_Game;     // Phase 6: Draw map (optional)
```

**Command Line Interface:**
```
DIP_RUN <gamepath> [<Options>]
/s - run Scanner
/p - run Parser
/c - run Conflicter
/w - run Retreat- and Winterprogram
/m - run Mapmaker
/all - all options marked with "*"
```

## Phase 1: Order Scanning (DIP_SCAN.pas)

**Purpose**: Parse human-readable orders into machine format

**Input Files:**
- `<gamepath>/<orders_file>` - Human orders (e.g., "England: F lon-nth, A lvp S lon")
- `<variant_path>/<synonym_file>` - Territory name synonyms

**Functionality:**
- **Tokenization**: Breaks down order text into nations, units, territories, commands
- **Spell Checking**: Matches territory names against variant geography (`ExactMatch` mode)
- **Synonym Resolution**: Converts alternative names to canonical territory names
- **Error Detection**: Identifies malformed orders, unknown territories

**Key Features:**
```pascal
// Territory name matching with spell-check
ExactMatch := pos(WordN(PartieParam(kwExactMatch), 2), bsYes) <> 0;

// Debugging support
Show_ScanDebug_Info(TokenNr, Token, possible, ScanKey, TokenCode);
```

**Output**: Tokenized orders ready for validation

## Phase 2: Order Parsing (DIP_PARS.pas)

**Purpose**: Validate orders and handle geographical constraints

**Key Validations:**

### 2.1 Geographical Analysis
- **Border Checking**: Validates moves against `<variant_path>/borders.dat`
- **Unit Type Validation**: Ensures armies/fleets use appropriate territories
- **Coast Specification**: Handles multi-coast territories (Spain, St. Petersburg, Bulgaria)

### 2.2 Subfield/Overfield Transformation
```pascal
// Subfield handling (lines 191-362)
GetOverField(pLocation[idx1]^) = GetOverField(pOrder[idx2]^)  // Compare overfields
Orders_HandleZugError(idx, zeSubFieldChg);                    // Subfield change error
Orders_HandleZugError(idx, zeSupSubFieldChg);                 // Support subfield error
```

**Key Concepts:**
- **Subfields**: `SpN` (Spain North), `SpS` (Spain South), `BuN` (Bulgaria North)
- **Overfields**: `Spa` (unified Spain), `Bul` (unified Bulgaria)
- **Transformation**: Subfields resolved to overfields before conflict resolution
- **Error Handling**: Invalid coast specifications generate `zeSubFieldChg` errors

### 2.3 Order Validation
- **NSU Checking**: No-stand-unit validation (`NSUcheckingOff` parameter)
- **Support Target Validation**: Ensures support targets are reachable using `NormalMovePossible`
- **Convoy Route Validation**: Sophisticated recursive pathfinding algorithm

### 2.4 Convoy Route Checking Algorithm (D_CONVOY.pas)

The Pascal implementation uses a **recursive pathfinding algorithm** to validate convoy routes:

#### Core Algorithm (`ConvoyRoutePossible`)
```pascal
function ConvoyRoutePossible(fromField, toField: TFieldNr; FieldList: TFieldList): boolean;
```

**Input:**
- `fromField`: Army's starting position
- `toField`: Army's destination
- `FieldList`: Available convoying fleets

**Algorithm Steps:**

1. **Direct Connection Check**:
   ```pascal
   if ConvoyStepPossible(fromField, toField) then
       ConvoyRoutePossible := true; exit
   ```

2. **Recursive Path Finding**:
   ```pascal
   GetPossibleFleets(fromField, FieldList, newFleets);  // Get adjacent convoy fleets
   for each fleet in newFleets do
       delField(FieldList, fleet, FieldList2);          // Remove used fleet
       found := ConvoyRoutePossible(fleet, toField, FieldList2); // Recurse
   ```

#### Fleet Adjacency Check (`ConvoyStepPossible`)
```pascal
function ConvoyStepPossible(aFieldNr, bFieldNr: TFieldNr): boolean;
```

**Validation Logic:**
1. **Territory Type Check**: Both fields must support convoy (`pos('C', anyField.Types) <> 0`)
2. **Border Validation**: Check `borders.dat` for connectivity
3. **Unit Type Check**: Use `ConvoyRelevantUnitNr` (typically Army = 1)

```pascal
GetBorder(anyBorder, aFieldNr, bFieldNr);
status := anyBorder.aMove[ConvoyRelevantUnitNr];
result := (status <> bnNo) and (status <> bnNoBorder) and (status <> bnFfna);
```

#### Integration in Parsing Phase

**Processing Order** (lines 931-936 in `DIP_PARS.pas`):
```pascal
Unmoegliche_Convoybefehle;    // j) Check if fleet can convoy
Bewegungen_perConvoy;         // k) Convert nmove to cmove if convoyed
IMP_perConvoy_Bewegung;       // m) Validate convoy routes exist
NSO_Convoybefehle;            // n) Check convoy orders have corresponding moves
```

**Move Type Conversion** (`Bewegungen_perConvoy`):
- Identifies armies with convoy support
- Converts `nmove` → `cmove` for convoyed armies
- Only if: `IsConvoyable(unit)` AND `IsCoast(from/to)` AND `IsConvoyed(order)`

**Route Validation** (`IMP_perConvoy_Bewegung`):
```pascal
// Collect all convoy fleets for this move
for idy := 1 to AnzOrders do
    if (GetOrder(pOrder[idy]^) = ScanOrder[convoy]) and
       (GetTrgField(pOrder[idy]^) = FromField) and
       (GetRefField(pOrder[idy]^) = ToField)
    then Fleets.field[++Fleets.anz] := GetField(pOrder[idy]^);

// Validate complete route exists
if not ConvoyRoutePossible(FromField, ToField, Fleets) then
    Orders_HandleZugError(idx, zeIMPcmove);
```

#### Geography Data Integration

**Border Data Structure** (`borders.dat`):
```pascal
TBorderRec = record
    ToField: TFieldNr;                              // Destination field
    AMove: array[1..MaxUnitTypes] of TFieldNr;      // Movement permissions per unit type
end;
```

**Movement Permissions:**
- `bnYes` (65500): Movement allowed
- `bnNo` (65501): Movement forbidden
- `bnImp` (65502): Impossible move
- `bnNoBorder` (0): No border exists

**Territory Types** (`fields.dat`):
- `"Land"`: Land territory
- `"Sea"`: Sea territory
- `"Coast"`: Coastal territory (supports both land and sea)
- `"C"` flag: Supports convoy operations

#### Error Handling

**Convoy-Related Errors:**
- `zeUnitCantConvoy`: Unit type cannot convoy (e.g., Army trying to convoy)
- `zeIMPcmove`: Convoy route impossible (no valid path)
- `zeNSOconvoy`: No corresponding move for convoy order

#### Comparison with Python Implementation

**Pascal Approach:**
- ✅ **Complete geography integration** with borders.dat
- ✅ **Recursive pathfinding** with cycle detection
- ✅ **Unit type validation** per territory type
- ✅ **Comprehensive error reporting**

**Python Approach** (`eval_k1.py`):
```python
convoy_routing_engine = "always"  # Simplified placeholder
# OR
convoy_routing_engine = "fixed:Vie--Mun;Kie--NTH"  # Test specification
```

**📋 Missing in Python:**
- No geography data integration
- No recursive pathfinding
- No unit type vs territory type validation
- Simplified "always allow if convoy exists" logic

**📊 Convoy Validation Complexity:**
The Pascal convoy checking is surprisingly sophisticated:
- **Graph Theory**: Uses recursive depth-first search with cycle detection
- **Geography Integration**: Validates each step against border data
- **Multi-Type Support**: Different rules per unit type (Army/Fleet)
- **Error Classification**: Specific error codes for different convoy failure modes
- **Performance Optimization**: Fails fast on impossible routes

This represents one of the most complex geographical validations in the system, essential for proper Diplomacy adjudication.

**Output**: Validated orders with comprehensive geographical and convoy constraints applied

## Phase 3: Conflict Resolution (DIP_EVAL.pas)

**Purpose**: Resolve simultaneous order conflicts (**CURRENT PYTHON IMPLEMENTATION**)

**Algorithm**: Multi-phase evaluation (k1→k2→k3→k4→k0) as documented in current Python code

**Key Innovations in Pascal→Python Transition:**

### 3.1 Pattfield Handling
**Pascal Approach** (D_Unit.pas:64):
```pascal
pattfield,    {not a real order: empty, but do not retreat to TrgField}
```
- Inserted actual field entries with `pattfield` order type

**Python Approach** (`conflict_game.py:150`):
```python
pattfields = (efields | ufields) - sfields - (hfields - efields)
```
- Mathematical set calculation, no field insertion
- ✅ **Better encapsulation**: Separate metadata from game state

### 3.2 Result Structure
**Pascal**: Modifies original order structures in-place
**Python**: Returns immutable `ConflictResolution` with `orders` + `pattfields`

## Phase 4: Retreat & Build Resolution (DIP_WINT.pas)

**Purpose**: Handle unit retreats and winter adjustments

### 4.1 Retreat Resolution (`Retreats_Game`)

**Process:**
1. **Identify Dislodged Units**: Units with `attacked_from` order type
2. **Calculate Retreat Options**:
   ```pascal
   GetPossibleRetreatFields(DefField, PossRetFields, GetUnit(pOrder[idx]^));
   ```
3. **Apply Geographical Constraints**: Check `NormalMovePossible` for each option
4. **Remove Invalid Options**:
   - Occupied territories
   - Pattfields (from conflict resolution)
   - Attacker's origin territory
5. **User/GM Choice**: Interactive menu or automatic resolution
6. **RHR Ordering**: Right-hand rule for retreat priority

**Retreat Order Syntax:**
```
<unit> > <retreat_destination>    // Successful retreat
<unit> > ex                       // Disband (no valid retreat)
```

### 4.2 Build/Disband Phase (`Buildup_Game`)

**Winter Phase Logic:**
1. **Count Supply Centers**: Determine gained/lost SCs
2. **Calculate Adjustments**: Units vs SC count difference
3. **Build Units**: `+A <territory>` or `+F <territory>`
4. **Disband Units**: `-A <territory>` or `-F <territory>`
5. **Home SC Validation**: Can only build in unoccupied home SCs

**Build Order Syntax:**
```
+A Lon    // Build army in London
+F Kie    // Build fleet in Kiel
-A Mun    // Disband army in Munich
-F Ber    // Disband fleet in Berlin
```

## Phase 5: Output Generation (DIP_VORD.pas, DIP_TEXT.pas)

**Purpose**: Generate human-readable results

**Output Formats:**
- **Plain Text**: Turn results with status symbols
- **Graphical**: Map display with unit positions (`DIP_DRAW.pas`)
- **Error Reports**: Detailed error explanations

**Status Symbols** (matches current Python `__log__` methods):
```pascal
symbols[empty] := '0';       // Empty field
symbols[none] := ' ';        // Hold order
symbols[convoy] := 'c';      // Convoy
symbols[nmove] := '-';       // Normal move
symbols[cmove] := ':';       // Convoy move
symbols[umove] := ')';       // Unsuccessful move
symbols[hsupport] := '.';    // Hold support
symbols[msupport] := '+';    // Move support
```

## Data Files and Geography

### Geography Files (Variant-Specific)
```
<variant_path>/
├── fields.dat          # Territory definitions with coordinates
├── borders.dat         # Movement possibilities by unit type
├── <variant>.vrn       # Main variant configuration
└── synonyms.dat        # Territory name alternatives
```

### Game Files
```
<gamepath>/
├── <game>.gam          # Current game state
├── <orders>.ord        # Player orders input
├── <conflicted>.ord    # Post-conflict resolution state
├── <wintered>.ord      # Post-retreat/build state
└── <error>.err         # Error log
```

### Field Record Structure (D_FldRec.pas)
```pascal
TFieldRec = record
  name: TFieldName;           // Territory name (e.g., "London")
  xCoord, yCoord: word;       // Map coordinates
  SubOf: TFieldNr;            // Parent field (0 if overfield)
  Types: string;              // "Land" | "Sea" | "Coast"
  SP: word;                   // Supporting points
  HomeSC: word;               // Home SC ownership
  FirstBorder, LastBorder: TBorderNr; // Border range in borders.dat
end;
```

**Subfield Resolution:**
- `SubOf = 0`: Overfield (e.g., Spa, Bul, StP)
- `SubOf > 0`: Subfield (e.g., SpN→Spa, BuS→Bul)
- Resolution happens in Parser phase before conflict resolution

## Integration Points for Python Implementation

### Immediate Opportunities
1. **Geography Service**: Implement border validation for moves
2. **Retreat Resolution**: Add retreat phase after conflict resolution
3. **Build/Disband Logic**: Implement winter adjustment phase

### Architecture Suggestions

**Modular Approach** (following Pascal structure):
```python
# Phase 1: Order Input
dipworkpy.scanner.scan_orders(raw_orders: str) -> List[RawOrder]

# Phase 2: Order Validation
dipworkpy.parser.parse_orders(raw_orders: List[RawOrder], geography: Geography) -> Situation

# Phase 3: Conflict Resolution (EXISTING)
dipworkpy.conflict_game.conflict_game(situation: Situation) -> ConflictResolution

# Phase 4: Retreat Resolution
dipworkpy.retreats.resolve_retreats(conflict_result: ConflictResolution, geography: Geography) -> RetreatResolution

# Phase 5: Build/Disband
dipworkpy.winter.resolve_winter(retreat_result: RetreatResolution, sc_ownership: Dict[str, str]) -> WinterResolution
```

**Geography Service Interface:**
```python
class GeographyService:
    def validate_move(self, unit_type: str, from_territory: str, to_territory: str) -> bool
    def get_retreat_options(self, territory: str, unit_type: str, pattfields: Set[str]) -> List[str]
    def resolve_subfields(self, territory: str) -> str  # SpN → Spa
    def get_home_scs(self, nation: str) -> List[str]

    # Enhanced convoy validation based on Pascal analysis
    def validate_convoy_route(self, from_territory: str, to_territory: str,
                            convoy_fleets: List[str]) -> bool
    def get_convoy_adjacent_territories(self, territory: str) -> List[str]
    def territory_supports_convoy(self, territory: str) -> bool
```

**Enhanced Convoy Route Validation:**
```python
def convoy_route_valid_enhanced(world: t_world, field: t_field, convoyer_names: Set[str]) -> bool:
    """Enhanced convoy validation following Pascal recursive algorithm"""
    geography = get_geography_service()

    # Direct connection check
    if geography.validate_move("A", field.name, field.dest):
        return False  # Direct move possible, convoy not needed

    # Recursive pathfinding with geography data
    return geography.validate_convoy_route(field.name, field.dest, list(convoyer_names))
```

## Current Implementation Status

| Phase | Pascal Module | Python Status | Completeness |
|-------|---------------|---------------|--------------|
| **Order Scanning** | DIP_SCAN.pas | ❌ Not implemented | 0% |
| **Order Parsing** | DIP_PARS.pas | ⚠️ Basic validation only | 10% |
| **Conflict Resolution** | DIP_EVAL.pas | ✅ **Fully implemented** | 95% |
| **Retreat Resolution** | DIP_WINT.pas | ❌ Not implemented | 0% |
| **Winter Adjustments** | DIP_WINT.pas | ❌ Not implemented | 0% |
| **Output Generation** | DIP_VORD.pas | ⚠️ Basic logging only | 20% |

## Key Architectural Decisions

### ✅ Improvements in Python Implementation
1. **Immutable Results**: `ConflictResolution` vs Pascal in-place modification
2. **Separate Pattfields**: `Set[str]` vs special field entries
3. **Type Safety**: Pydantic models vs Pascal records
4. **Modern Parsing**: Space-separated format vs complex tokenization

### 📋 Missing Components for Complete Implementation
1. **Geography Validation**: Border checking, coast handling
2. **Retreat Phase**: Interactive/automatic retreat resolution
3. **SC Counting**: Supply center ownership tracking
4. **Winter Phase**: Build/disband with home SC validation
5. **Multi-turn Orchestration**: Game state persistence

### 🎯 Recommended Next Steps
1. **Implement `GeographyService`** - Enable proper move validation
2. **Add retreat resolution** - Handle dislodged units from `ConflictResolution`
3. **Create winter adjustment system** - Build/disband with SC counting
4. **Develop game state management** - Multi-turn persistence

## Key Architectural Insights

### Pascal System Strengths
1. **🗺️ Complete Geography Integration**: Full border validation with recursive convoy pathfinding
2. **📋 Comprehensive Error Handling**: 20+ specific error codes with detailed explanations
3. **🔄 Multi-Phase Validation**: Each phase builds on validated output from previous phase
4. **🎯 Production Ready**: Proven in real games with interactive GM interface
5. **📊 Sophisticated Algorithms**: Graph theory for convoy routes, RHR for retreats

### Python System Innovations
1. **🎯 Modern Type Safety**: Pydantic models vs Pascal records
2. **📦 Clean Architecture**: Immutable results vs in-place modification
3. **🔗 Better Data Separation**: Pattfields as metadata vs special order types
4. **🚀 Performance**: Set operations vs array manipulations
5. **🧪 Comprehensive Testing**: DATC compliance + STPSYR integration

### Critical Missing Components
The **convoy route validation** represents the largest gap between implementations:

**Pascal**: 4-step sophisticated validation process in parsing phase
**Python**: Single-line placeholder in conflict resolution phase

This affects:
- Move legality validation
- Support target reachability
- Convoy route impossibility detection
- Proper error reporting for invalid orders

### Implementation Priority
Based on this analysis, the next Python development priorities should be:

1. **🥇 Geography Service** - Border validation and convoy pathfinding
2. **🥈 Retreat Resolution** - Handle dislodged units with proper territory exclusion
3. **🥉 Winter Adjustments** - Build/disband with SC counting
4. **📊 Complete Order Pipeline** - Scanner → Parser → Conflicter → Winter

The Pascal reference provides a proven architecture for a complete Diplomacy engine, with the current Python implementation providing an excellent foundation for the critical conflict resolution component.