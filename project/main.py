# std python
# 3rd party
import uvicorn
# local
import dipworkpy

if __name__ == "__main__":
    uvicorn.run(dipworkpy.app
                , host="127.0.0.1"
                , port=8444
                , log_level="trace"
                )
