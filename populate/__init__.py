# -*- coding: utf-8 -*-

def with_alias(func):
    def wrapper(col, *args, **kwargs):

        try:
            alias = kwargs.pop('alias')
        except KeyError:
            alias = True

        sql = func(col, *args, **kwargs)

        if not alias:
            return sql
        elif alias is True:
            name = col.name if not isinstance(col, str) else col
        else:
            name = alias
        return sql + ' as {}'.format(name)
    return wrapper

class ArrayAgg(object):
    """docstring for ArrayAgg."""

    type = 'array'

    def __init__(self, col, cast=None, orderby=None, alias=None):
        super(ArrayAgg, self).__init__()
        self.store = dict(
            col = col,
            orderby = "" if orderby is None else " ORDER BY {}".format(orderby.strip()),
            cast = "" if cast is None else "::{}".format(cast.strip().lstrip(':')),
            alias = "" if alias is None else " AS {}".format(alias.strip())
        )

    def __bool__(self):
        return True

    def __str__(self):
        return "array_agg({col}{orderby}){cast}{alias}".format(**self.store)

    # @with_alias
    # def __call__(self):
    #     return self.__str__()

class First(ArrayAgg):
    """docstring for First."""

    type = "unknown"

    def __init__(self, *args, **kwargs):
        super(First, self).__init__(*args, **kwargs)

    def __str__(self):
        return "(array_agg({col}{orderby}))[1]{cast}{alias}".format(**self.store)
