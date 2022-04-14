import pytest

from rdflib import URIRef
from rdflib.graph import Dataset


def test_issue353_nquads_default_graph():

    data = """
    <http://example.org/s1> <http://example.org/p1> <http://example.org/o1> .
    <http://example.org/s2> <http://example.org/p2> <http://example.org/o2> .
    <http://example.org/s3> <http://example.org/p3> <http://example.org/o3> <http://example.org/g3> .
    """
    publicID = URIRef("http://example.org/g0")

    ds = Dataset()
    ds.parse(data=data, format="nquads", publicID=publicID)

    # Union
    assert len(list(ds.quads((None, None, None, None)))) == 3

    # Specified publicID
    assert len(list(ds.quads((None, None, None, publicID)))) == 2

    # Named graph from data
    assert len(list(ds.quads((None, None, None, URIRef("http://example.org/g3"))))) == 1
