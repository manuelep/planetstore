CREATE OR REPLACE FUNCTION public.T_sinh(x double precision)
RETURNS double precision LANGUAGE sql IMMUTABLE STRICT AS $$
  -- sinh function has been introduced in version 12 of PostgreSQL
  SELECT (exp(x)-exp(-1*x))/2
$$;

CREATE OR REPLACE FUNCTION public.T_truncate(pnt geometry)
RETURNS geometry LANGUAGE plpgsql IMMUTABLE STRICT AS $$
  DECLARE
    lon double precision;
    lat double precision;
    -- srid integer;

  BEGIN
    lon := GREATEST(ST_X(pnt), -180.0);
    lon := LEAST(ST_X(pnt), 180.0);
    lat := GREATEST(ST_Y(pnt), -90.0);
    lat := LEAST(ST_Y(pnt), 90.0);

    RETURN ST_SetSRID(ST_MakePoint(lon, lat), 4326);
  END
$$;

CREATE OR REPLACE FUNCTION public.T_ul(tile geometry)
RETURNS geometry LANGUAGE plpgsql IMMUTABLE STRICT AS $$
  -- Returns the upper left point of a tile
  DECLARE
    xtile integer;
    ytile integer;
    zoom integer;
    Z2 double precision;
    lon double precision;
    lat double precision;
    lat_rad double precision;

  BEGIN
    xtile := ST_X(tile);
    ytile := ST_Y(tile);
    zoom := ST_Z(tile);

    Z2 := pow(2, zoom);
    lon := (xtile / Z2 * 360.0) - 180.0;
    lat_rad := atan(T_sinh(pi() * (1 - 2 * ytile / Z2)));
    lat := degrees(lat_rad);

    RETURN ST_SetSRID(ST_MakePoint(lon, lat), 4326);
  END
$$;

CREATE OR REPLACE FUNCTION public.T_bounds(tile geometry)
RETURNS geometry LANGUAGE plpgsql IMMUTABLE STRICT AS $$
  -- Returns the bounding box polygon of a tile
  DECLARE
    xtile integer;
    ytile integer;
    zoom integer;
    bl geometry;
    ur geometry;

  BEGIN
    xtile := ST_X(tile);
    ytile := ST_Y(tile);
    zoom := ST_Z(tile);

    bl = T_ul(ST_MakePoint(xtile, ytile - 1, zoom));
    ur = T_ul(ST_MakePoint(xtile + 1, ytile, zoom));

    RETURN ST_SetSRID(ST_MakeEnvelope(ST_X(bl), ST_Y(bl), ST_X(ur), ST_Y(ur)), 4326);
  END
$$;

CREATE OR REPLACE FUNCTION public.T_uxy(pnt geometry, truncated boolean default FALSE)
RETURNS geometry LANGUAGE plpgsql IMMUTABLE STRICT AS $$
  DECLARE
    sinlat double precision;
    x double precision;
    y double precision;

  BEGIN

    IF truncated THEN
      pnt = T_truncate(pnt);
    END IF;

    sinlat := sin(radians(ST_Y(pnt)));

    IF sinlat=1 THEN
      RETURN NULL;
    ELSE
      x = ST_X(pnt) / 360.0 + 0.5;
      y = 0.5 - 0.25*ln((1.0 + sinlat) / (1.0 - sinlat)) / pi();
      RETURN ST_SetSRID(ST_MakePoint(x, y), 3857);
    END IF;
  END
$$;

CREATE OR REPLACE FUNCTION public.T_tile(pnt geometry, zoom integer, truncated boolean default FALSE)
RETURNS geometry LANGUAGE plpgsql IMMUTABLE STRICT AS $$
  -- Get the tile containing a point
  DECLARE
    EPSILON double precision = pow(10, -14);
    pnt_merc geometry;
    Z2 integer;
    xtile integer;
    ytile integer;

  BEGIN
    pnt_merc = T_uxy(pnt, truncated);
    Z2 := pow(2, zoom);

    IF ST_X(pnt_merc)<=0 THEN
      xtile = 0;
    ELSIF ST_X(pnt_merc)>=1 THEN
      xtile = Z2 - 1;
    ELSE
        -- To address loss of precision in round-tripping between tile
        -- and lng/lat, points within EPSILON of the right side of a tile
        -- are counted in the next tile over.
        xtile = (floor((ST_X(pnt_merc) + EPSILON) * Z2))::integer;
    END IF;

    IF ST_Y(pnt_merc)<=0 THEN
      ytile = 0;
    ELSIF ST_Y(pnt_merc)>=1 THEN
      ytile = Z2 - 1;
    ELSE
      ytile = (floor((ST_Y(pnt_merc) + EPSILON) * Z2))::integer;
    END IF;

    RETURN ST_MakePoint(xtile, ytile, zoom);
  END
$$;

CREATE OR REPLACE FUNCTION public.T_tilename(tile geometry)
RETURNS text LANGUAGE sql IMMUTABLE STRICT AS $$
  -- Return the tile coordinate string in the format 'tilex/tiley/zoom'
  SELECT CONCAT_WS('/', ST_X(tile)::text, ST_Y(tile)::text, ST_Z(tile)::text)
$$;
