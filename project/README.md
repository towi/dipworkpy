# DipWorkPy

Started as a rewrite of DipWork written in Pascal back in the 90s.

Directory structure of this project follows roughly

https://docs.python-guide.org/writing/structure/


## Starting up

Make sure you are in the ´project` folder

    cd project/

Create a virtual environment so you dont pollute your system:

    python -m venv venv
    
Switch into that venv, eg on Windows:

    .\venv\Scripts\activate.bat
    
or on Unix-ishs:

    source venv/Scripts/activate

Install the required... um... requirements (inside the venv)

    pip install -r requirements.txt

Play around.

> **Alternative: Use poetry**
> 
> I just added `poetry`: 
> 
>     poetry shell
>     poetry install
> 
> should also be able to get you started.


For example start the REST server by calling main

    python main.py
    
This will start-up a server framework which you can send REST requests to.

Only one of the many possibilities is the take a look at the JSON-schema by then browsing to
 
  * http://127.0.0.1:8444/docs
  * or http://127.0.0.1:8444/redoc
  * or downloading that spec from http://127.0.0.1:8444/openapi.json

You can send REST Requests to that interface.



## Collection of notes

 * I use `pydantic` (fastapi and starlet) for a REST Api plus a Schema. Not finished yet, but I started it...
 * The fact that I am useing uvicorn and/or async is also a just a a try. 
   You can do the same with Flask and or Cherrypy. You will see that I don't use it much here and try not
   to bind myself to any (asynchronous or not) framework (not least because I am no expert in those), because
   the focus of this project is definitly not high-throughput...
 * ...
 
