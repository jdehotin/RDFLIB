import pytest
import os
from rdflib import (
    logger,
    Graph,
    ConjunctiveGraph,
    Dataset,
    URIRef,
)
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID


michel = URIRef("urn:michel")
tarek = URIRef("urn:tarek")
bob = URIRef("urn:bob")
likes = URIRef("urn:likes")
hates = URIRef("urn:hates")
pizza = URIRef("urn:pizza")
cheese = URIRef("urn:cheese")

c1 = URIRef("urn:context-1")
c2 = URIRef("urn:context-2")

sportquads = open(
    os.path.join(os.path.dirname(__file__), "consistent_test_data", "sportquads.nq")
).read()


def pytest_assertdatasetcontexts_compare(op, left, right):
    if (
        isinstance(left, list)
        and isinstance(left[0], Graph)
        and isinstance(right, list)
        and isinstance(right[0], Graph)
        and op == "=="
    ):
        return [
            "Comparing Dataset contexts:",
            "   vals: {} != {}".format(left.val, right.val),
        ]


"""

# urbanmatthias commented on 14 Oct 2020

It seems to me that RDFLib behaves differently with graphs
than it does with sets.

While |= performs an in-place union when used with sets,
RDFLib creates a new Graph when used with Graphs.

---

# ashleysommer commented on 15 Oct 2020

Hi @urbanmatthias

Yep, you're right. That union operator does work differently on a Graph than
it does on a set, and it does look like its that way on purpose.

I don't know what is more "correct" here.

I think the idea behind creating a new graph on this operation is to avoid
polluting an existing graph. Or the graph a might be read-only, so the most
consistent and reliable way of completing the union would be to create a new
graph and union into that.

Note, I found in my testing that a += c does do what you'd expect a |= c to
do. But I think that is wrong too, because += should add a single triple or a
list of triples, where |= should union the graphs as it does for a set.

My thoughts for changes in RDFLib v6.0.0 are:

- `a |= c` (where a is a graph and c is a second graph) should should modify
  and write into a, without creating a new graph

++++++++++++++++++++++++++++++++++++++++++++++++++
operator.__ior__(a, b)

    a = ior(a, b) is equivalent to a |= b.
++++++++++++++++++++++++++++++++++++++++++++++++++

- `a += (s, p, o)` should be the same as `a.add((s,p,o))`

- `a += [(s1,p1,o1), (s2,p2,o2)]` should be the same as `a.addN([(s1,p1,o1), (s2,p2,o2)])`

++++++++++++++++++++++++++++++++++++++++++++++++++
operator.__iadd__(a, b)

    a = iadd(a, b) is equivalent to a += b.
++++++++++++++++++++++++++++++++++++++++++++++++++

Implemented as:
==================================================

def __iadd__(self, other):

    '''Add all triples in Graph other to Graph.
    BNode IDs are not changed.'''

    self.addN((s, p, o, self) for s, p, o in other)
    return self

==================================================

BUT

==================================================

def __add__(self, other):
    '''Set-theoretic union
    BNode IDs are not changed.'''

    try:
        retval = type(self)()
    except TypeError:
        retval = Graph()
    for (prefix, uri) in set(list(self.namespaces()) + list(other.namespaces())):
        retval.bind(prefix, uri)
    for x in self:
        retval.add(x)
    for y in other:
        retval.add(y)
    return retval

==================================================
---

#  FlorianLudwig commented on 15 Oct 2020

Some more context from the python stdlib:

The `<operator>=` like `+=` or `|=` are called "in place" in python and for
mutable objects (like sets) it means that the left-hand object is changed.

I don't think the python convention is that "in place" means the left-hand
MUST be mutated (so the current implementation is not wrong) but CAN or
SHOULD(for performance reasons).

I think the idea behind creating a new graph on this operation is to avoid
polluting an existing graph.

As in-place operators do "pollute" objects with standard types I don't think
this is a behaviour is expected. If needed, `a = a + c` can still be used.

Or the graph a might be read-only, so the most consistent and reliable way of
completing the union would be to create a new graph and union into that.

The standard library does create new objects for immutable objects, like tuples:

>>> a = (1, 2)
>>> a + (3, 4)
(1, 2, 3, 4)

>>> a += (3, 4)
>>> a
(1, 2, 3, 4)

---

# white-gecko commented on 15 Oct 2020

I think changing this for v6 would be a good idea. I would expect the in-place
operators to actually work in-place.

Actually I do not understand, what could be the difference between `+=` and `|=`
on graphs. I would expect both to behave in the same way, also if left and
right are graphs or left is a graph and right is a triple. Is there a
difference for sets between `+=` and `|=`?

# FlorianLudwig commented on 15 Oct 2020

@white-gecko
sets do not support `+=`

# jbmchuck commented on 15 Oct 2020 •

Updating `|=` to perform an in-place union would be nice. I believe it's doing
an update rather than a union if we are going by set's semantics.

I'd like if RDFLib could keep current `|=` behavior but as | and/or
Graph.union - this would mirror the behavior of set and would give a
migration path for code relying on `|=`'s current behavior.

"""

# Think about __iadd__, __isub__ etc. for ConjunctiveGraph
# https://github.com/RDFLib/rdflib/issues/225

# Currently all operations are done on the default graph, i.e. if you add
# another graph, even if it's a conjunctive graph, all triples are added
# to the default graph.

# It may make sense to check if the other thing added is ALSO a
# conjunctive graph and merge the contexts:


# @pytest.mark.skip
def test_operators_with_dataset_and_graph():

    ds = Dataset()
    ds.add((tarek, likes, pizza))
    ds.add((tarek, likes, michel))

    g = Graph()
    g.add([tarek, likes, pizza])
    g.add([tarek, likes, cheese])

    logger.debug(
        f"sub\n"
        f"ds:\n{ds.serialize(format='json-ld')}\n"
        f"g\n{g.serialize(format='json-ld')})\n"
        f"(ds+g)\n{(ds + g).serialize(format='json-ld')})"
    )
    assert len(ds + g) == 3  # adds cheese as liking

    logger.debug(
        "sub\n"
        f"ds:\n{ds.serialize(format='json-ld')}\n"
        f"g\n{g.serialize(format='json-ld')})\n"
        # f"(ds+g)\n{(ds - g).serialize(format='json-ld')})"
    )

    with pytest.raises(ValueError):  # too many values to unpack (expected 3)
        assert len(ds - g) == 1  # removes pizza

    logger.debug(
        "mul\n"
        f"ds:\n{ds.serialize(format='json-ld')}\n"
        f"g\n{g.serialize(format='json-ld')})\n"
        f"(ds*g)\n{(ds * g).serialize(format='json-ld')})"
    )
    assert len(ds * g) == 1  # only pizza

    logger.debug(
        "xor\n"
        f"ds:\n{ds.serialize(format='json-ld')}\n"
        f"g\n{g.serialize(format='json-ld')})\n"
        # f"(ds^g)\n{(ds ^ g).serialize(format='json-ld')})"
    )

    with pytest.raises(ValueError):  # too many values to unpack (expected 3)
        assert len(ds ^ g) == 2  # removes pizza, adds cheese


# @pytest.mark.skip
def test_operators_with_dataset_and_conjunctivegraph():

    ds = Dataset()
    ds.add((tarek, likes, pizza))
    ds.add((tarek, likes, michel))

    cg = ConjunctiveGraph()
    cg.add([tarek, likes, pizza])
    cg.add([tarek, likes, cheese])

    assert len(ds + cg) == 3  # adds cheese as liking

    assert len(ds - cg) == 1  # removes pizza

    assert len(ds * cg) == 1  # only pizza


# @pytest.mark.skip
def test_operators_with_dataset_and_namedgraph():

    ds = Dataset()
    ds.add((tarek, likes, pizza))
    ds.add((tarek, likes, michel))

    ng = ConjunctiveGraph(identifier=URIRef("context-1"))
    ng.add([tarek, likes, pizza])
    ng.add([tarek, likes, cheese])

    assert len(ds + ng) == 3  # adds cheese as liking

    assert len(ds - ng) == 1  # removes pizza

    assert len(ds * ng) == 1  # only pizza


# @pytest.mark.skip
def test_reversed_operators_with_dataset_and_graph():

    ds = Dataset()
    ds.add((tarek, likes, pizza))
    ds.add((tarek, likes, michel))

    g = Graph()
    g.add([tarek, likes, pizza])
    g.add([tarek, likes, cheese])

    with pytest.raises(ValueError):  # too many values to unpack (expected 3)
        assert len(g + ds) == 3  # adds cheese as liking

    assert len(g - ds) == 1  # removes pizza

    with pytest.raises(ValueError):  # too many values to unpack (expected 3)
        assert len(g * ds) == 1  # only pizza

    with pytest.raises(ValueError):  # too many values to unpack (expected 3)
        assert len(g ^ ds) == 2  # removes pizza, adds cheese


# @pytest.mark.skip
def test_operators_with_two_datasets():

    ds1 = Dataset()
    ds1.add((tarek, likes, pizza))
    ds1.add((tarek, likes, michel))

    ds2 = Dataset()
    ds2.add((tarek, likes, pizza))
    ds2.add((tarek, likes, cheese))

    assert len(ds1 + ds2) == 3  # adds cheese as liking

    assert len(ds1 - ds2) == 1  # removes pizza

    assert len(ds1 * ds2) == 1  # only pizza

    logger.debug(
        "xor, only pizza\n"
        f"ds1: {ds1.serialize(format='json-ld')}\n"
        f"ds2: {ds2.serialize(format='json-ld')}\n"
        f"(ds1 ^ ds2): {(ds1 ^ ds2).serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds1 ^ ds2) == 1  # only pizza


# @pytest.mark.skip
def test_operators_with_two_datasets_default_union():

    ds1 = Dataset(default_union=True)
    ds1.add((tarek, likes, pizza))
    ds1.add((tarek, likes, michel))

    ds2 = Dataset()
    ds2.add((tarek, likes, pizza))
    ds2.add((tarek, likes, cheese))

    assert len(ds1 + ds2) == 3  # adds cheese as liking

    assert len(ds1 - ds2) == 1  # removes pizza

    assert len(ds1 * ds2) == 1  # only pizza

    logger.debug(
        "xor\n"
        f"ds1: {ds1.serialize(format='json-ld')}\n"
        f"ds2: {ds2.serialize(format='json-ld')}\n"
        f"(ds1 ^ ds2): {(ds1 ^ ds2).serialize(format='json-ld')}"
    )

    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds1 ^ ds2) == 1  # only pizza


# @pytest.mark.skip
def test_inplace_operators_with_conjunctivegraph_and_graph():

    cg = ConjunctiveGraph()
    cg.add((tarek, likes, pizza))
    cg.add((tarek, likes, michel))

    g = Graph()
    g.add([tarek, likes, pizza])
    g.add([tarek, likes, cheese])

    cg += g  # now cg contains everything

    logger.debug("_iadd, cg contains everything\n" f"{cg.serialize(format='json-ld')}")

    assert len(cg) == 3

    cg.remove((None, None, None, None))
    assert len(cg) == 0

    cg -= g

    logger.debug(
        "_isub, removes pizza\n"
        f"cg: {cg.serialize(format='json-ld')}\n"
        f"g: {g.serialize(format='json-ld')}\n"
        f"(cg -= g): {cg.serialize(format='json-ld')}"
    )

    with pytest.raises(AssertionError):  # 0 == 1
        assert len(cg) == 1  # removes pizza

    cg.remove((None, None, None, None))
    assert len(cg) == 0

    cg *= g

    logger.debug(
        "_imul, only pizza\n"
        f"cg: {cg.serialize(format='json-ld')}\n"
        f"g: {g.serialize(format='json-ld')}\n"
        f"(cg *= g): {cg.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(cg) == 1  # only pizza


# @pytest.mark.skip
def test_inplace_operators_with_two_conjunctivegraphs():

    cg1 = ConjunctiveGraph()
    cg1.add((tarek, likes, pizza))
    cg1.add((tarek, likes, michel))

    cg2 = ConjunctiveGraph()
    cg2.add((tarek, likes, pizza))
    cg2.add((tarek, likes, cheese))

    cg1 += cg2  # now cg1 contains everything
    # logger.debug(f"_iadd, cg1 contains everything\n{cg1.serialize(format='json-ld')}")

    assert len(cg1) == 3

    cg1.remove((None, None, None, None))
    assert len(cg1) == 0

    # logger.debug(f"_isub, removes pizza\n{cg1.serialize(format='json-ld')}")
    cg1 -= cg2

    logger.debug(
        "_isub\n"
        f"cg1: {cg1.serialize(format='json-ld')}\n"
        f"cg2: {cg2.serialize(format='json-ld')}\n"
        f"(cg1 -= cg2): {cg1.serialize(format='json-ld')}",
    )
    with pytest.raises(AssertionError):
        assert len(cg1) == 1  # removes pizza

    cg1.remove((None, None, None, None))
    assert len(cg1) == 0

    cg1 *= cg2
    logger.debug(
        "_imul\n"
        f"cg1: {cg1.serialize(format='json-ld')}\n"
        f"cg2: {cg2.serialize(format='json-ld')}\n"
        f"(cg1 *= cg2): {cg1.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):
        assert len(cg1) == 1  # only pizza


# @pytest.mark.skip
def test_inplace_operators_with_dataset_and_graph():

    ds = Dataset()
    ds.add((tarek, likes, pizza))
    ds.add((tarek, likes, michel))

    g = Graph()
    g.add([tarek, likes, pizza])
    g.add([tarek, likes, cheese])

    ds += g  # now ds contains everything
    # logger.debug(f"_iadd, ds contains everything\n{ds.serialize(format='json-ld')}")

    assert len(ds) == 3

    ds.remove((None, None, None, None))
    assert len(ds) == 0

    ds -= g
    # logger.debug(f"_isub, removes pizza\n{ds.serialize(format='json-ld')}")

    logger.debug(
        "_isub\n"
        f"ds: {ds.serialize(format='json-ld')}\n"
        f"g: {g.serialize(format='json-ld')}\n"
        f"(ds -= g): {ds.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds) == 1  # removes pizza

    ds.remove((None, None, None, None))
    assert len(ds) == 0

    ds *= g
    # logger.debug(f"_imul, only pizza\n{ds.serialize(format='json-ld')}")

    logger.debug(
        "_imul\n"
        f"ds: {ds.serialize(format='json-ld')}\n"
        f"g: {g.serialize(format='json-ld')}\n"
        f"(ds *= g): {ds.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds) == 1  # only pizza


# @pytest.mark.skip
def test_inplace_operators_with_dataset_and_conjunctivegraph():

    ds = Dataset()
    ds.add((tarek, likes, pizza))
    ds.add((tarek, likes, michel))

    cg = ConjunctiveGraph()
    cg.add([tarek, likes, pizza])
    cg.add([tarek, likes, cheese])

    ds += cg  # now ds contains everything
    # logger.debug(f"_iadd, ds contains everything\n{ds.serialize(format='json-ld')}")

    assert len(ds) == 3

    ds.remove((None, None, None, None))
    assert len(ds) == 0

    ds -= cg
    # logger.debug(f"_isub, removes pizza\n{ds.serialize(format='json-ld')}")

    logger.debug(
        "_isub\n"
        "ds: {ds.serialize(format='json-ld')}\n"
        f"cg: {cg.serialize(format='json-ld')}\n"
        f"(ds -= cg): {ds.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds) == 1  # removes pizza

    ds.remove((None, None, None, None))
    assert len(ds) == 0

    ds *= cg
    # logger.debug(f"_imul, only pizza\n{ds.serialize(format='json-ld')}")

    logger.debug(
        "_imul\n"
        f"ds: {ds.serialize(format='json-ld')}\n"
        f"cg: {cg.serialize(format='json-ld')}\n"
        f"(ds *= cg): {ds.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds) == 1  # only pizza


# @pytest.mark.skip
def test_inplace_operators_with_dataset_and_namedgraph():

    ds = Dataset()
    ds.add((tarek, likes, pizza))
    ds.add((tarek, likes, michel))

    cg = ConjunctiveGraph(identifier=URIRef("context-1"))
    cg.add((tarek, likes, pizza))
    cg.add((tarek, likes, cheese))

    ds += cg  # now ds contains everything
    # logger.debug(f"_iadd, ds contains everything\n{ds.serialize(format='json-ld')}")

    assert len(ds) == 3

    ds.remove((None, None, None, None))
    assert len(ds) == 0

    ds -= cg
    # logger.debug(f"_isub, removes pizza\n{ds.serialize(format='json-ld')}")

    logger.debug(
        "_isub\n"
        f"ds: {ds.serialize(format='json-ld')}\n"
        f"cg: {cg.serialize(format='json-ld')}\n"
        f"(ds -= cg): {ds.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds) == 1  # removes pizza

    ds.remove((None, None, None, None))
    assert len(ds) == 0

    ds *= cg
    # logger.debug(f"_imul, only pizza\n{ds.serialize(format='json-ld')}")

    logger.debug(
        "_imul\n"
        f"ds: {ds.serialize(format='json-ld')}\n"
        f"cg: {cg.serialize(format='json-ld')}\n"
        f"(ds *= cg): {ds.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds) == 1  # only pizza


# @pytest.mark.skip
def test_inplace_operators_with_two_datasets():

    ds1 = Dataset()
    ds1.add((tarek, likes, pizza))
    ds1.add((tarek, likes, michel))

    ds2 = Dataset()
    ds2.add((tarek, likes, pizza))
    ds2.add((tarek, likes, cheese))

    # WITHOUT Dataset.__iadd__()
    # with pytest.raises(
    #     ValueError
    # ):  # ValueError: too many values to unpack (expected 3)
    #     ds1 += ds2  # now ds1 contains everything
    #     assert len(ds1) == 3

    # WITH Dataset.__iadd__()
    try:
        # logger.debug(
        #     f"sub\nds1:\n{ds1.serialize(format='json-ld')}\nds2\n{ds2.serialize(format='json-ld')})"
        # )
        ds1 += ds2  # now ds1 contains everything
        # logger.debug(f"_iadd, ds1 contains everything\n{ds1.serialize(format='json-ld')}")
    except Exception as e:
        assert repr(e) in [
            "AssertionError('Context associated with urn:tarek urn:likes urn:pizza is None!')",
            "AssertionError('Context associated with urn:tarek urn:likes urn:michel is None!')",
            "AssertionError('Context associated with urn:tarek urn:likes urn:cheese is None!')",
        ]

    ds1.remove((None, None, None, None))
    assert len(ds1) == 0

    ds1 -= ds2
    # logger.debug(f"_isub, removes pizza\n{ds1.serialize(format='json-ld')}")

    logger.debug(
        "_isub\n"
        f"ds1: {ds1.serialize(format='json-ld')}\n"
        f"ds2: {ds2.serialize(format='json-ld')}\n"
        f"(ds1 -= ds2): {ds1.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds1) == 1  # removes pizza

    ds1.remove((None, None, None, None))
    assert len(ds1) == 0

    ds1 *= ds2
    # logger.debug(f"_imul, only pizza\n{ds1.serialize(format='json-ld')}")

    logger.debug(
        "_mul\n"
        f"ds1: {ds1.serialize(format='json-ld')}\n"
        f"ds2: {ds2.serialize(format='json-ld')}\n"
        f"(ds1 *= ds2): {ds1.serialize(format='json-ld')}"
    )
    with pytest.raises(AssertionError):  # 0 == 1
        assert len(ds1) == 1  # only pizza


# if __name__ == "__main__":
#     test_inplace_operators_with_dataset_and_graph()
