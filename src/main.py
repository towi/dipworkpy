# python
# 3rd party
from fastapi import FastAPI
# local
import model

app = FastAPI()

@app.get("/")
async def root():
    return {"app": "PyDipWork"}

#####################################################


@app.post("/resolve", response_model=model.ConflictResolution)
async def resolve(situation: model.Situation):
    return {"message": "Hello World"}


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

#####################################################

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app
                , host="127.0.0.1"
                , port=8444
                , log_level="trace"
                )
