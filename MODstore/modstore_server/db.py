"""Compatibility shim: tests and catalog_public_index import ``get_session_factory`` from here."""

from modstore_server.models import get_session_factory

__all__ = ["get_session_factory"]
