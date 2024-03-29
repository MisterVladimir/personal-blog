# -*- coding: utf-8 -*-

import os
import pathlib
import shlex
import shutil
import sys
from typing import TypedDict

from invoke import task, Context
from invoke.main import program
from pelican import main as pelican_main
from pelican.server import ComplexHTTPRequestHandler, RootedHTTPServer
from pelican.settings import DEFAULT_CONFIG, get_settings_from_file

OPEN_BROWSER_ON_SERVE = True
_REPO_ROOT = pathlib.Path(__file__).parent
SETTINGS_FILE_BASE = _REPO_ROOT.joinpath("personal_blog", "pelican_config.py")
SETTINGS = {}
SETTINGS.update(DEFAULT_CONFIG)
LOCAL_SETTINGS = get_settings_from_file(str(SETTINGS_FILE_BASE))
SETTINGS.update(LOCAL_SETTINGS)


class ConfigDict(TypedDict):
    settings_base: str
    settings_publish: str
    deploy_path: str
    host: str
    port: int


CONFIG: ConfigDict = {
    "settings_base": str(SETTINGS_FILE_BASE),
    "settings_publish": str(_REPO_ROOT.joinpath("personal_blog", "publish_config.py")),
    # Output path. Can be absolute or relative to tasks.py. Default: 'output'
    "deploy_path": SETTINGS["OUTPUT_PATH"],
    # Host and port for `serve`
    "host": "localhost",
    "port": 8000,
}


@task
def clean(c):
    """Remove generated files"""
    if os.path.isdir(CONFIG["deploy_path"]):
        shutil.rmtree(CONFIG["deploy_path"])
        os.makedirs(CONFIG["deploy_path"])


@task()
def build(c, clean=True):  # type: (Context, bool) -> None
    """Build local version of site"""
    pelican_cmd = "-s {settings_base}".format(**CONFIG)
    if clean:
        pelican_cmd += " -e DELETE_OUTPUT_DIRECTORY=true"
    pelican_run(pelican_cmd)


@task
def serve(c):
    """Serve site at https://$HOST:$PORT/ (default is localhost:8000)"""

    class AddressReuseTCPServer(RootedHTTPServer):
        allow_reuse_address = True

    server = AddressReuseTCPServer(
        CONFIG["deploy_path"],
        (CONFIG["host"], CONFIG["port"]),
        ComplexHTTPRequestHandler,
    )

    if OPEN_BROWSER_ON_SERVE:
        # Open site in default browser
        import webbrowser

        webbrowser.open("http://{host}:{port}".format(**CONFIG))

    sys.stderr.write("Serving at {host}:{port} ...\n".format(**CONFIG))
    server.serve_forever()


@task()
def build_prod(c):
    """Build production version of site"""
    pelican_run("-s {settings_publish}".format(**CONFIG))


@task
def livereload(c):
    """Automatically reload browser tab upon file modification."""
    from livereload import Server

    def cached_build():
        cmd = "-s {settings_base} -e CACHE_CONTENT=true LOAD_CONTENT_CACHE=true"
        pelican_run(cmd.format(**CONFIG))

    cached_build()
    server = Server()
    theme_path = SETTINGS["THEME"]
    watched_globs = [
        CONFIG["settings_base"],
        "{}/templates/**/*.html".format(theme_path),
    ]

    content_file_extensions = [".md", ".rst"]
    for extension in content_file_extensions:
        content_glob = "{0}/**/*{1}".format(SETTINGS["PATH"], extension)
        watched_globs.append(content_glob)

    static_file_extensions = [".css", ".js"]
    for extension in static_file_extensions:
        static_file_glob = "{0}/static/**/*{1}".format(theme_path, extension)
        watched_globs.append(static_file_glob)

    for glob in watched_globs:
        server.watch(glob, cached_build)

    if OPEN_BROWSER_ON_SERVE:
        # Open site in default browser
        import webbrowser

        webbrowser.open("http://{host}:{port}".format(**CONFIG))

    server.serve(host=CONFIG["host"], port=CONFIG["port"], root=CONFIG["deploy_path"])


def pelican_run(cmd):  # type: (str) -> None
    # ``program.core.remainder`` is all args after the "--"
    # Its type is ``str``.
    # allows to pass-through args to pelican
    cmd += " " + program.core.remainder
    pelican_main(shlex.split(cmd))
