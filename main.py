import secrets
import uuid
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha512
from typing import List, Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()
app.username = "4dm1n"
app.password = "NotSoSecurePa$$"
app.secret_key = "T00Sh0rtAppS3cretK3y"
app.api_token: List[str] = []
app.session_token: List[str] = []
app.token_limits = 3


def add_token(token: str, cache_ns: str):
    tokens = getattr(app, cache_ns)
    if len(tokens) >= app.token_limits:
        tokens.pop(0)
    tokens.append(token)
    setattr(app, cache_ns, tokens)


def remove_token(token: str, cache_ns: str):
    tokens = getattr(app, cache_ns)
    try:
        index = tokens.index(token)
        tokens.pop(index)
        setattr(app, cache_ns, tokens)
    except ValueError:
        return None


def generate_token(request: Request):
    return sha512(
        bytes(
            f"{uuid.uuid4().hex}{app.secret_key}{request.headers['authorization']}",
            "utf-8",
        )
    ).hexdigest()


def auth_basic_auth(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    correct_user = secrets.compare_digest(credentials.username, app.username)
    correct_pass = secrets.compare_digest(credentials.password, app.password)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials"
        )

    return True


def auth_session(session_token: str = Cookie(None)):
    if app.session_token and session_token in app.session_token:
        return session_token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials"
    )


def auth_token(token: Optional[str] = None):
    if app.api_token and token in app.api_token:
        return token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials"
    )


@contextmanager
def response_class(format: str):
    resp_cls = PlainTextResponse
    if format == "json":
        resp_cls = JSONResponse
    if format == "html":
        resp_cls = HTMLResponse

    yield resp_cls


@contextmanager
def response_welcome_msg(format: str):
    resp_msg = "Welcome!"
    if format == "json":
        resp_msg = {"message": "Welcome!"}
    if format == "html":
        resp_msg = "<h1>Welcome!</h1>"

    yield resp_ms


@app.get("/hello", response_class=HTMLResponse)
def read_root_hello():
    return f"""
    <html>
        <head>
            <title></title>
        </head>
        <body>
            <h1>Hello! Today date is { datetime.now().date() }</h1>
        </body>
    </html>
    """


@app.post("/login_session", status_code=201, response_class=HTMLResponse)
def create_session(
    request: Request, response: Response, auth: bool = Depends(auth_basic_auth)
):
    token = generate_token(request)
    add_token(token, "session_token")
    response.set_cookie(key="session_token", value=token)
    return ""


@app.post("/login_token", status_code=201)
def create_token(request: Request, auth: bool = Depends(auth_basic_auth)):
    token = generate_token(request)
    add_token(token, "api_token")
    return {"token": token}


@app.get("/welcome_session")
def show_welcome_session(received_token: str = Depends(auth_session), format: str = ""):
    with response_class(format) as resp_cls:
        with response_welcome_msg(format) as resp_msg:
            return resp_cls(content=resp_msg)


@app.get("/welcome_token")
def show_welcome_token(received_token: str = Depends(auth_token), format: str = ""):
    with response_class(format) as resp_cls:
        with response_welcome_msg(format) as resp_msg:
            return resp_cls(content=resp_msg)


@app.get("/logged_out")
def logged_out(format: str = ""):
    with response_class(format) as resp_cls:
        if format == "json":
            return resp_cls(content={"message": "Logged out!"})
        if format == "html":
            return resp_cls(content="<h1>Logged out!</h1>")

        return resp_cls(content="Logged out!")


@app.delete("/logout_session")
def logout_session(received_token: str = Depends(auth_session), format: str = ""):
    remove_token(received_token, "session_token")
    return RedirectResponse(
        url=f"/logged_out?format={format}", status_code=status.HTTP_302_FOUND
    )


@app.delete("/logout_token")
def logout_token(received_token: str = Depends(auth_token), format: str = ""):
    remove_token(received_token, "api_token")
    return RedirectResponse(
        url=f"/logged_out?format={format}", status_code=status.HTTP_302_FOUND
    )