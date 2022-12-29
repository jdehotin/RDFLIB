import math
import sys
from typing import Set, Tuple

from rdflib import Graph, Literal, RDFS
from rdflib.namespace import Namespace
from rdflib.plugins.sparql.processor import processUpdate
from rdflib.term import Node, URIRef


def triple_set(graph: Graph) -> Set[Tuple[Node, Node, Node]]:
    return set(graph.triples((None, None, None)))


class TestSPARQLParser:
    def test_insert_recursionlimit(self) -> None:
        # These values are experimentally determined
        # to cause the RecursionError reported in
        # https://github.com/RDFLib/rdflib/issues/1336
        resource_count = math.ceil(sys.getrecursionlimit() / (33 - 3))
        self.do_insert(resource_count)

    def test_insert_large(self) -> None:
        self.do_insert(200)

    def do_insert(self, resource_count: int) -> None:
        EGV = Namespace("http://example.org/vocab#")
        EGI = Namespace("http://example.org/instance#")
        prop0, prop1, prop2 = EGV["prop0"], EGV["prop1"], EGV["prop2"]
        g0 = Graph()
        for index in range(resource_count):
            resource = EGI[f"resource{index}"]
            g0.add((resource, prop0, Literal(index)))
            g0.add((resource, prop1, Literal("example resource")))
            g0.add((resource, prop2, Literal(f"resource #{index}")))

        g0ntriples = g0.serialize(format="ntriples")
        g1 = Graph()

        assert triple_set(g0) != triple_set(g1)

        processUpdate(g1, f"INSERT DATA {{ {g0ntriples!s} }}")

        assert triple_set(g0) == triple_set(g1)


def test_thingy():
    graph = Graph()
    graph.add(
        (URIRef("http://example.com/something"), RDFS.label, Literal("Some label"))
    )

    results = list(
        graph.query(
            """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT *
    WHERE {
        {
            SELECT *
            WHERE {
                    {
                        SELECT ?label
                        WHERE {
                            [] rdfs:label ?label.
                        }
                    }
            }
        }
    }
            """
        )
    )

    assert len(results) == 1
    assert results[0][0] == Literal("Some label")
