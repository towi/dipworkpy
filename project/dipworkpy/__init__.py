# std python
# 3rd party
from fastapi import FastAPI
# local
import dipworkpy.model as model

app = FastAPI()

@app.get("/")
async def root():
    return {"app": "DipWorkPy"}

#####################################################


@app.post("/dip_eval", response_model=model.ConflictResolution)
async def resolve(situation: model.Situation):
    from dipworkpy.conflict_game import conflict_game
    return conflict_game(situation)


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
