# std python
# 3rd party
from fastapi import FastAPI
# local
import dipworkpy.model as model

debug = True

app = FastAPI()

@app.get("/")
async def root():
    return {"app": "DipWorkPy"}

#####################################################


@app.post("/cfl_resolve", response_model=model.ConflictResolution)
async def resolve(situation: model.Situation):
    import dipworkpy.impl_resolve
    return dipworkpy.impl_resolve(situation)


@app.post("/check", response_model=model.ConflictCheck)
async def check(situation: model.Situation):
    fields = {o.current for o in situation.orders}
    fields.update({o.target for o in situation.orders})
    return {
        "nations": { o.nation for o in situation.orders },
        "utypes": { o.utype for o in situation.orders },
        "afields": fields,
        "orders": {
            "mve": len([o.order for o in situation.orders  if o.order=="mve"]),
            "hld": len([o.order for o in situation.orders  if o.order=="hld"]),
            "sup": len([o.order for o in situation.orders  if o.order=="sup"]),
            "con": len([o.order for o in situation.orders  if o.order=="con"]),
        },
        "order_errors": len([o.order for o in situation.orders  if o.order not in {"mve", "hld", "sup", "con"}]),
    }
