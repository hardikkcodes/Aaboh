-- The production target is PostgreSQL + PostGIS.
-- Geometry currently travels as GeoJSON through a portable field so that the
-- application can also run on SQLite during local development (see DECISIONS.md
-- ADR-003). Enabling PostGIS here keeps the production database ready for the
-- documented migration to native geometry columns.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
