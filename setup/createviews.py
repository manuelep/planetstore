# -*- coding: utf-8 -*-

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        description = """
        To be run with command line (add -h for help):

        <you>:~/<path>/<to>/apps$ python -m <app>.planet.setup.createviews -h

        """,
        formatter_class = argparse.RawTextHelpFormatter
    )

    try:
        from ...settings import DB_FOLDER, APP_NAME
        from ..settings import DB_URI
    except Exception as err:
        # raise
        message = """You are running this script without the necessary environment.
        Please read the documentation here below."""
        print(err)
        parser.print_help()
        raise Exception(message)
    else:
        from .postgresql import setup_views
        # TODO: Cache postgresq super user credentials
        # from diskcache import Cache
        # from .postgresql import setup_views

    # parser.add_argument("-d", "--db",
    #     help = 'Setup DB and exit',
    #     action = 'store_true',
    #     default = False,
    #     dest = 'db_setup'
    # )

    args = parser.parse_args()

    setup_views()
    print("That's it!")
