import inspect
from typing import Any, Callable, Dict, Iterable, Tuple

from fastapi import Request

# FastAPI fills only one Request parameter per endpoint: decorators share it
_HIDDEN_REQUEST_PARAM = "_request"


def request_parameter(func: Callable) -> Tuple[str, bool]:
    """
    Name of the Request parameter FastAPI will fill for `func`, and whether
    `func` itself receives it (declared by the endpoint or an inner decorator).
    """
    for param in inspect.signature(func).parameters.values():
        if param.annotation is Request:
            return param.name, True
    return _HIDDEN_REQUEST_PARAM, False


def take_request(kwargs: Dict[str, Any], name: str, forward: bool) -> Request:
    """Read the request from the call kwargs, removing it unless `func` expects it."""
    return kwargs[name] if forward else kwargs.pop(name)


def hidden_request_parameter() -> inspect.Parameter:
    return inspect.Parameter(_HIDDEN_REQUEST_PARAM, inspect.Parameter.KEYWORD_ONLY, annotation=Request)


def expose_signature(
    wrapper: Callable,
    func: Callable,
    add: Iterable[inspect.Parameter] = (),
    remove: Iterable[str] = ()
) -> None:
    """
    Set the signature FastAPI reads on `wrapper`: the one of `func`, without
    the `remove` parameters and with the `add` ones (keyword-only, injected
    by FastAPI). The wrapper must pop the added parameters before calling func.
    """
    signature = inspect.signature(func)
    removed = set(remove)
    kept = [param for param in signature.parameters.values() if param.name not in removed]
    wrapper.__signature__ = signature.replace(parameters=[*kept, *add])
