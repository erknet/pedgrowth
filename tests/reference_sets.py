"""Test-only reference collections; never installed in runtime packages."""

from pedgrowth.data.who2006.tables import WHO_TABLES as WHO_2006_TABLES
from pedgrowth.data.who2007.tables import WHO_2007_TABLES

WHO_TABLES = [*WHO_2006_TABLES, *WHO_2007_TABLES]
