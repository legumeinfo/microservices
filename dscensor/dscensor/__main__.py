import logging
from pathlib import Path
from typing import List, Union

from aiohttp import web
from rororo import setup_openapi, setup_settings

from dscensor import http_server
from dscensor.directed_graph import DirectedGraphController
from dscensor.settings import Settings


def create_app(
    argv: Union[List[str], None] = None,
    *,
    settings: Union[Settings, None] = None,
) -> web.Application:
    """Create aiohttp applicaiton for OpenAPI 3 Schema.

    OpenAPI specification from: ``api/dscensor.yaml``.

    This aiohttp application is ready to be run as:

    .. code-block:: bash

        dscensor

    After application is running, feel free to use Swagger UI to check the
    results. The OpenAPI schema will be available at:


    This app was modeled after https://github.com/playpauseandstop/rororo
    """
    # Instantiate settings
    if settings is None:
        settings = Settings.from_environ()

    # Store the settings within the app
    app = setup_settings(
        web.Application(),
        settings,
        loggers=("aiohttp", "aiohttp_middlewares", "dscensor", "rororo"),
        remove_root_handlers=True,
    )

    app[settings.dscensor_app_key] = DirectedGraphController(
        logging.getLogger("dscensor"), settings.input_nodes
    )

    # Setup OpenAPI schema support for aiohttp application
    parent = Path(__file__).parent.parent
    api_path = f"{parent}/openapi/dscensor/{settings.api_version}/dscensor.yaml"
    return setup_openapi(
        # Where first param is an application instance
        app,
        # Second is path to OpenAPI 3 Schema
        api_path,
        # And after list of operations
        http_server.operations,
        is_validate_response=False,  # disable as spec has no error definitions atm
        # Enable CORS middleware as it ensures that every aiohttp response
        # will use proper CORS headers
        cors_middleware_kwargs={"allow_all": True},
    )


def run_app(host="0.0.0.0", port=8080):
    """Runs app so you dont have to."""
    web.run_app(create_app())
