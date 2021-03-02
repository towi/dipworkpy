# std python
# 3rd party
from fastapi import FastAPI
# local
import dipworkpy.model as model

app = FastAPI()

# currently only a dummy
@app.get("/")
async def root():
    return {"app": "DipWorkPy"}

#####################################################

# This executes a resolution of conflicts.
# Syntactic and semantic checks must have been done before. There are a lot
# of assumptions that the agorithm relies on (to be documented). For example
# the geography os currently assumed to be valid -- if "A Lon-Mos" is given here
# it is assumed to be a valid move.
@app.post("/dip_eval", response_model=model.ConflictResolution)
async def resolve(situation: model.Situation):
    from dipworkpy.conflict_game import conflict_game
    return conflict_game(situation)


# Syntax and semantic checks. Currently only a bare placeholder.
@app.post("/check", response_model=model.ConflictCheck)
async def check(situation: model.Situation):
    fields = {o.current for o in situation.orders}
    fields.update({o.dest for o in situation.orders})
    return {
        "nations": { o.nation for o in situation.orders },
        "utypes": { o.utype for o in situation.orders },
        "afields": fields,
        "orders": { ot : len([o.order for o in situation.orders  if o.order==ot])  for ot in model.OrderType},
        "order_errors": 0,
    }
