# -*- coding: utf-8 -*-

from .tools import First
from ..models import db

from os import path
import inspect

def __replace_view(name, query):
    """ """
    sql = """CREATE OR REPLACE VIEW {name} AS {query}"""
    db.executesql(sql.format(
        name = name,
        query = query
    ))

def setup_view(name, query, *fields, **options):
    """ """
    if isinstance(query, str):
        __replace_view(name, query)
    else:
        __replace_view(
            name,
            db(query)._select(*fields, **options)
        )

def setup_views():
    """"""
    # db._adapter.reconnect()

    setup_view("data_source", db.info.id>0,
        "min(info.id) as id",
        db.info.source_name,
        groupby = db.info.source_name
    )

    setup_view("addresses",
        (db.info.id>0) & "(info.tags::jsonb ? 'addr:street')::boolean",
        db.info.id.with_alias('id'),
        db.info.source_name,
        "info.tags->>'addr:city' as city",
        "info.tags->>'addr:street' as street",
        # "info.properties->>'codvia' as codvia",
        distinct = "info.tags->>'addr:street'",
        orderby = "info.tags->>'addr:street'"
    )

    housenumber = "(info.tags->>'addr:housenumber')"
    street = "(info.tags->>'addr:street')"
    city = "(info.tags->>'addr:city')"

    setup_view("housenumbers",
        (db.info.id>0) & "(info.tags::jsonb ? 'addr:street')::boolean",
        db.info.id.with_alias('id'),
        db.info.source_name,
        housenumber + ' as housenumber',
        street + ' as street',
        city + ' as city'
    )

    # setup_view("addons",
    #     (db.data_source.source_name==db.addon.source_name),
    #     db.addon.id.with_alias("id"),
    #     # Data source informations
    #     db.data_source.id.with_alias("src_id"),
    #     db.data_source.source_name.with_alias("source_name"),
    #     # Addon properties informations
    #     db.addon.source_id.with_alias("source_id"),
    #     db.addon.properties.with_alias("properties")
    # )

    setup_view("points",
        (db.info.id==db.node.info_id) & \
            (db.data_source.source_name==db.info.source_name) & \
            "(((info.tags IS NOT NULL) AND (info.tags::text <> '{}'::text)) or ((info.properties IS NOT NULL) AND (info.properties::text <> '{}'::text)))",

        db.info.id.with_alias("id"),
        # Data source informations
        db.data_source.id.with_alias("src_id"),
        db.data_source.source_name,
        # Geometries
        db.node.geom.with_alias("geom"),
        # Feature properties informations
        db.info.source_id,
        db.info.tags,
        db.info.properties,
        "json_build_array(ST_X(node.geom),ST_Y(node.geom)) as crds",
        db.node.id.with_alias("node_id")
    )

    way_query = (db.info.id == db.way_node.info_id) & \
        (db.node.id == db.way_node.node_id) & \
        (db.data_source.source_name == db.info.source_name)

    base_geom_fields = [
        # Data source informations
        First(db.data_source.id, alias='src_id'),
        First(db.data_source.source_name, alias='source_name'),
        # Feature properties informations
        First(db.info.tags, 'json', alias='tags'),
        First(db.info.properties, 'json', alias='properties'),
        First(db.info.source_id, 'text', alias='source_id'),
    ]

    setup_view("ways", way_query & "(info.tags::jsonb ? 'highway')::boolean",
        First(db.info.id, alias='id'),
        "ST_MakeLine(node.geom ORDER BY way_node.sorting) as geom",
        *base_geom_fields,
        groupby = db.way_node.info_id
    )


    setup_view("graph", """SELECT
        -- snode.info_id::text||'-'||tnode.info_id::text as id,
        swnode.id,
        data_source.id as src_id,
        info.source_id,
        data_source.source_name,
        ST_MakeLine(ARRAY[snode.geom, tnode.geom]) as geom,
        sinfo.id as sinfo_id,
        snode.id as snode_id,
        sinfo.tags as stags,
        tinfo.id as tinfo_id,
        tnode.id as tnode_id,
        tinfo.tags as ttags,
        info.tags,
        info.properties,
        ST_Distance(ST_Transform(snode.geom, 3857), ST_Transform(tnode.geom, 3857)) as len,
        snode.geom as snode,
        tnode.geom as tnode
    FROM
        info,
        info as sinfo,
        info as tinfo,
        node as snode,
        node as tnode,
        data_source,
        way_node as swnode,
        way_node as twnode
    WHERE
        data_source.source_name = info.source_name AND
        info.id = swnode.info_id AND
        sinfo.id = snode.info_id AND
        tinfo.id = tnode.info_id AND
        snode.id = swnode.node_id AND
    	tnode.id = twnode.node_id AND
        swnode.info_id = twnode.info_id AND
        swnode.sorting+1 = twnode.sorting AND
        (info.tags::jsonb ? 'highway')::boolean""")

    polys_query_template = """SELECT
        subq.id,
        subq.way_info_id,
        subq.src_id,
        subq.source_name,
        subq.tags,
        subq.properties,
        subq.source_id,
        ST_BuildArea(subq.way) as geom,
        subq.way,
        st_centroid(subq.way) AS centroid
    FROM
        ({}) AS subq
    WHERE
        ST_IsClosed(subq.way) AND
        ST_ASText(ST_BuildArea(subq.way)) like 'POLYGON%'
    -- (((subq.tags::jsonb ? 'area')::boolean AND (subq.tags->>'area' <> 'no')) OR
    -- (subq.tags::jsonb ?| array['landuse', 'boundary', 'building'])::boolean)
    ;"""

    setup_view("polys", polys_query_template.format(db(
        way_query
    )._select(
        # Record identifier
        First(db.info.id, alias='id'),
        db.way_node.info_id.with_alias('way_info_id'),
        # Geometries
        "ST_MakeLine(node.geom ORDER BY way_node.sorting) as way",
        *base_geom_fields,
        groupby = db.way_node.info_id
    )[:-1]))

    setup_view("_splitted_polys", """SELECT *,
        st_centroid(subq.geom) AS centroid
    FROM (
        SELECT
            wayinfo.id,
            way_node.info_id as way_info_id,
            -- Data source informations
            data_source.id as src_id,
            data_source.source_name,
            relinfo.id as relation_id,
            -- Geometries
            ST_MakeLine(node.geom ORDER BY way_node.sorting) as geom,
            -- Feature properties informations
            (array_agg(relinfo.tags))[1] as tags,
            (array_agg(relinfo.properties))[1] as properties,
            wayinfo.source_id as source_id,
            relinfo.source_id as relation_source_id,
            relation.role
        FROM
            data_source,
            info as relinfo,
            info as wayinfo,
            node,
            way_node,
            relation
        WHERE
            data_source.source_name = wayinfo.source_name AND
            node.id = way_node.node_id AND
            wayinfo.id = way_node.info_id AND
            relation.member_id = wayinfo.id AND
            relinfo.id = relation.info_id AND
            (relation.role = 'outer' OR relation.role = 'inner')
            --relation.role = 'outer'
        GROUP BY
            wayinfo.id,
            data_source.id,
            data_source.source_name,
            relinfo.id,
            relation.role,
            wayinfo.source_id,
            way_node.info_id
        ORDER BY relation_id, relation.role DESC
    ) as subq WHERE ST_IsClosed(subq.geom);""")

    setup_view("mpolys", """SELECT *,
        ST_MakePolygon(polys[1], polys[2:array_length(polys, 1)]) as geom,
        ST_Centroid(polys[1]) AS centroid
        FROM (SELECT
                percentile_disc(0) WITHIN GROUP (ORDER BY id) as id,
                percentile_disc(0) WITHIN GROUP (ORDER BY src_id) as src_id,
                percentile_disc(0) WITHIN GROUP (ORDER BY way_info_id) as way_info_id,
                percentile_disc(0) WITHIN GROUP (ORDER BY source_name) as source_name,
                percentile_disc(0) WITHIN GROUP (ORDER BY source_id) as source_id,
                (array_agg(tags))[1] as tags,
                (array_agg(properties))[1] as properties,
                array_agg(geom ORDER BY role DESC) as polys
            FROM _splitted_polys
            GROUP BY relation_id
            ORDER BY relation_id
        ) as subq""")

    db.commit()

def setup_functions():
    here = path.dirname(path.abspath(inspect.getfile(inspect.currentframe()))) # script directory
    with open(path.join(here, 'mercantile.sql')) as pgmercantile:
        sql = pgmercantile.read()
    db.executesql(sql)
    db.commit()
