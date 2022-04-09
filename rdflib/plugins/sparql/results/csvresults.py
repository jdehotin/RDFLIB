"""

This module implements a parser and serializer for the CSV SPARQL result
formats

http://www.w3.org/TR/sparql11-results-csv-tsv/

"""

import codecs
import csv
from typing import IO, TYPE_CHECKING, Optional, TextIO, Union

from rdflib import Variable, BNode, URIRef, Literal

from rdflib.query import Result, ResultSerializer, ResultParser

from rdflib.util import as_textio


class CSVResultParser(ResultParser):
    def __init__(self):
        self.delim = ","

    def parse(self, source, content_type=None):

        r = Result("SELECT")

        if isinstance(source.read(0), bytes):
            # if reading from source returns bytes do utf-8 decoding
            source = codecs.getreader("utf-8")(source)

        reader = csv.reader(source, delimiter=self.delim)
        r.vars = [Variable(x) for x in next(reader)]
        r.bindings = []

        for row in reader:
            r.bindings.append(self.parseRow(row, r.vars))

        return r

    def parseRow(self, row, v):
        return dict(
            (var, val)
            for var, val in zip(v, [self.convertTerm(t) for t in row])
            if val is not None
        )

    def convertTerm(self, t):
        if t == "":
            return None
        if t.startswith("_:"):
            return BNode(t)  # or generate new IDs?
        if t.startswith("http://") or t.startswith("https://"):  # TODO: more?
            return URIRef(t)
        return Literal(t)


class CSVResultSerializer(ResultSerializer):
    def __init__(self, result):
        ResultSerializer.__init__(self, result)

        self.delim = ","
        if result.type != "SELECT":
            raise Exception("CSVSerializer can only serialize select query results")

    def serialize(
        self, stream: Union[IO[bytes], TextIO], encoding: Optional[str] = None, **kwargs
    ):

        # the serialiser writes bytes in the given encoding
        # in py3 csv.writer is unicode aware and writes STRINGS,
        # so we encode afterwards

        with as_textio(stream, encoding=encoding) as stream:
            out = csv.writer(stream, delimiter=self.delim)
            if TYPE_CHECKING:
                assert self.result.vars is not None
            vs = [self.serializeTerm(v, encoding) for v in self.result.vars]
            out.writerow(vs)
            for row in self.result.bindings:
                out.writerow(
                    [self.serializeTerm(row.get(v), encoding) for v in self.result.vars]
                )

    def serializeTerm(self, term, encoding):
        if term is None:
            return ""
        else:
            return term
