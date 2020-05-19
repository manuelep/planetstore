# -*- coding: utf-8 -*-

import csv, io
# from swissknife.log import timeLoggerDecorator

class BulkCopyer(object):
    """
    Courtesy of: https://www.citusdata.com/blog/2017/11/08/faster-bulk-loading-in-postgresql-with-copy/
    TODO: https://stackoverflow.com/a/8150329/1039510
    https://stackoverflow.com/a/9166750/1039510
    """

    # def __nextid(self):
    #     """ [1] TODO:
    #     https://github.com/web2py/pydal/blob/60e97e7cfd1da98f3cf38b2023965226d42e5e5b/pydal/adapters/postgres.py#L179
    #     """
    #     last_row = self.table._db(self.table).select(self.table.id, orderby=~self.table.id, limitby=(0,1,)).first()
    #     import pdb; pdb.set_trace()
    #     return 0 if last_row is None else last_row.id
    #     return self.db.executesql("select nextval('{}_id_seq')".format(self.table_name))[0][0]-1

    def __init__(self, table):
        """
        table @DAL.Table : "db.graph_path"
        """
        super(BulkCopyer, self).__init__()

        self.db = table._db
        self.adapter = table._db._adapter
        self.table_name = table._tablename
        self.table = table
        csv.register_dialect('custom', delimiter='\t', quotechar="", quoting=csv.QUOTE_NONE)
        self.csv = io.StringIO()
        self.writer = csv.DictWriter(self.csv, fieldnames=table.fields(), dialect='custom')

    def __enter__(self):
        # self.maxid = self.__nextid()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        # self.csv.seek(0)

        if traceback is None:
            # foo = {}
            # if not current.plugins.planetstore.log_level is None:
            #     foo['level'] = current.plugins.planetstore.log_level

            # with timeLoggerDecorator("Coping to {}".format(self.table_name), **foo):
            content = self.csv.getvalue()
            if content:
                try:
                    self.adapter.cursor.copy_from(io.StringIO(content), self.table_name, null='NULL')
                except Exception as err:
                    self.db.rollback()
                    with open("/tmp/{}".format(self.table_name), "w") as foo:
                        foo.write(self.csv.getvalue())
                    raise
                else:
                #     maxid = self.db(self.table).select(self.table.id.max().with_alias('maxid')).first().maxid
                #     nextid = self.__nextid()
                #     if nextid<=maxcid:
                #         self.db.executesql(syncquery(self.table_name))
                    self.db.commit()
        else:
            raise

    def writerow(self, d):
        """ -> [1] """
        # self.maxid += 1
        d['id'] = self.db.executesql("select nextval('{}_id_seq')".format(self.table_name))[0][0]
        self.writer.writerow(d)
        return d['id']
