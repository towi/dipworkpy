# Rule IX.3. interpretation

DipWork has a switch that allows you to modify the interpretation of rule IX.3.
concerning self-dislodgement. 
I don't take any credit for it because I just implemented what Peter Jacobi had worked out.

I got into a discussion with some people and want to document here how we resolved the
points.

So, let's start with what I myself had written about the switch in DipWorks documentation:


## Switch IX_3_INTERPRETATION

Let me translate the [original explanation](ix_3_interpretation-de.md).

> * `En F ENG hld`
> * `Fr F MAO-ENG`
> * `En F IRI S Fr F MAO-ENG`
> * `En F Bre S Fr F MAO-ENG`
> * `Ge F NTH-ENG`
> * `Ge F Bel-ENG`
> 
> Spec:
> 
>  * Kind: Number
>  * Possibilities: 0, 1, 2
>  * Standard recommendation: 0
> 
> If an attacker normally wins a conflict but the unit in the target field
> does not leave it _and_ the nation of the unit in the target field has supported
> the attacker, then the movement of the attacker only succeeds if:
> 
> * 0: Also when ignoring the supports of the nation of the unit in the target field for all attackers it would be dislodged
> * 1: Also when ignoring the supports of the nation of the unit in the target field for all attackers the same attacker would win the conflict.
> * 2: This attack even without the supports of the nation in the target field is stronger than the defending strength.
> 
> In above example `En F ENG` did not move.
> The unit `Fr F MID` first wins the conflict in `ENG`. 
> However, by rule IX.3. the english supports to the attack do not count for dislodgment,
> so they will be ignored in second evaluation step.
> That has the consequence that `Ge F Bel` would win the conflict in `ENG`.
> 
> On option "0" `Fr F MID-ENG` succeeds because "`En F ENG` is dislodged anyway".
> 
> On option "1" neither `Fr F MID-ENG` nor `Ge F Bel-ENG` succeeds because "not the same attacker wins the conflict".
> 
> On option "2" again neither move succeeds: Only `Fr F MID-END` is considered
> ((the winner of the 1st conflict)) and that can not dislodge without the english supports.

The result of "1" and "2" therefore is the same but for different reasons.

---

## Discussion

...tbc...
