# Welcome to Planetstore

Planetstore is a sub-module developed as a component of a generic
[scaffolding](https://github.com/web2py/py4web/tree/master/apps/_scaffold)
[py4web](http://py4web.com/) application and it's part of the
[Planet Suite](https://manuelep.github.io/planet-suite/).

> **Note**
> Please refer to the
> [py4web official documentation](http://py4web.com/_documentation/static/index.html#chapter-01)
> for framework installation, setup and basics concepts about implementing applications
> and about what the *apps* folder is.

# Description

This module implements a database model inspired to the OpenstreetMap database,
optimized for storing informations, with more a very flexible json structure that
able to host and model any kind of data.

It supports OpenstreetMap and geojson as main data structure for import.

# How to's

## Include Planetstore in your custom application

Py4web applications are nothing more than native [python modules](https://docs.python.org/3/tutorial/modules.html)
and the Planetstore code repository is structured in the same way so can be used actually as
a *submodule* that can be nested in custom applications.

You can link the module to your code using [Git submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
but the minimal requirement is to copy/clone the [Planetstore repository](https://github.com/manuelep/planetstore)
nested in your `root` project folder.

### Requirements

Please refer to the `requirements.txt` file for an updated list of required python
modules and install them using:

```sh
pip install -r [path/to/apps/<your app>/planetstore/]requirements.txt
```

### Setup

1. Create a *settings_private.py* in your app `root` folder with the subsequent
content adapted to your needs:

        ::python
        SETUP_MODE = True

        # logger settings
        LOGGERS = [
            "debug:stdout" # or "info:stdout"
        ]  # syntax "severity:filename" filename can be stderr or stdout

        # db settings
        DB_URI = "postgres://<PG user>:<password>@<host name>/<db name>"
        # DB_POOL_SIZE = 10
        # DB_MIGRATE = <True/False> # True if not specified

1. Run the script for creating and setting up the database extensions and model:

        ::sh
        cd path/to/apps
        python -m <your app>.planetstore.setup.createdb

    > **WARNING**
    > the script will ask for necessary PostgreSQL power user credentials

1. Run the script for setting up views (*named queries*)

        ::sh
        python -m <your app>.planetstore.setup.createviews

1. **Comment out the SETUP_MODE variable definition in private settings file or set its value to False.**

# Doc

Please refer to the [repository wiki](https://github.com/manuelep/planetstore/wiki)
for the module detailed documentation.
