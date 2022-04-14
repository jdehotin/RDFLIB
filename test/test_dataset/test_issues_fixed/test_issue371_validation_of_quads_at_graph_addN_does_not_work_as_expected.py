import pytest

from rdflib import Dataset, URIRef
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore

michel = URIRef("urn:example:michel")
tarek = URIRef("urn:example:tarek")
likes = URIRef("urn:example:likes")
pizza = URIRef("urn:example:pizza")
cheese = URIRef("urn:example:cheese")

c1 = URIRef("urn:example:context-1")
c2 = URIRef("urn:example:context-2")


try:
    from urllib.request import urlopen

    assert len(urlopen("http://localhost:3030").read()) > 0
    skip = False
except Exception:
    skip = True


@pytest.mark.skipif(skip, reason="sparql endpoint is unavailable.")
def test_issue371_validation_of_quads_at_graph_addN_does_not_work_as_expected():

    ds = Dataset()

    ds.addN([(tarek, likes, pizza, c1), (michel, likes, cheese, c2)])

    quads = ds.quads((None, None, None, None))  # Fourth term is identifier

    store = SPARQLUpdateStore(
        query_endpoint="http://localhost:3030/db/sparql",
        update_endpoint="http://localhost:3030/db/update",
    )

    store.addN(quads)  # Fourth term is identifier

    store.update("CLEAR ALL")
