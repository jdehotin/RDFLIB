"""
Parser plugin interface.

This module defines the parser plugin interface and contains other
related parser support code.

The module is mainly useful for those wanting to write a parser that
can plugin to rdflib. If you are wanting to invoke a parser you likely
want to do so through the Graph class parse method.

"""

import codecs
import os
import pathlib
import sys

from io import BytesIO, TextIOBase, TextIOWrapper, StringIO, BufferedIOBase
from typing import Any, Dict, Optional, Union

from urllib.request import Request
from urllib.request import url2pathname
from urllib.request import urlopen
from urllib.error import HTTPError
import urllib.parse

from xml.sax import xmlreader

from rdflib import __version__
from rdflib.term import URIRef
from rdflib.namespace import Namespace

__all__ = [
    "Parser",
    "InputSource",
    "StringInputSource",
    "URLInputSource",
    "FileInputSource",
    "PythonInputSource",
]


def _iri2uri(iri):
    """
    Convert an IRI to a URI (Python 3).
    https://stackoverflow.com/a/42309027

    https://stackoverflow.com/a/40654295

    netloc should be encoded using IDNA;
    non-ascii URL path should be encoded to UTF-8 and then percent-escaped;
    non-ascii query parameters should be encoded to the encoding of a page
    URL was extracted from (or to the encoding server uses), then
    percent-escaped.

    >>> _iri2uri("https://dbpedia.org/resource/Almería")
    'https://dbpedia.org/resource/Almer%C3%ADa'
    """

    uri = ""

    if isinstance(iri, str):
        (scheme, netloc, path, query, fragment) = urllib.parse.urlsplit(iri)
        scheme = urllib.parse.quote(scheme)
        netloc = netloc.encode("idna").decode("utf-8")
        path = urllib.parse.quote(path)
        # query = urllib.parse.quote(query)

        # ^^^^^ The encoding of "=" as "%3D" causes the failure of
        # test/test_graph.py::GraphTestCase::testGuessFormatForParse
        # in that https://linked.data.gov.au/def/agrif?_format=text/turtle
        # becomes https://linked.data.gov.au/def/agrif?_format%3dtext/turtle
        # which yields a text/html mimetype, triggering a "no plugin found"
        # Exception. So, either decode the "%3D" or skip the conversion of
        # query params altogether.
        query = urllib.parse.unquote(urllib.parse.quote(query))

        fragment = urllib.parse.quote(fragment)
        uri = urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))

    # urllib omits the empty fragment identifier, so it has to be explicitly restored
    if iri.endswith("#") and not uri.endswith("#"):
        uri += "#"

    return uri


class Parser(object):
    __slots__ = ()

    def __init__(self):
        pass

    def parse(self, source, sink):
        pass


class BytesIOWrapper(BufferedIOBase):
    __slots__ = ("wrapped", "encoded", "encoding")

    def __init__(self, wrapped: str, encoding="utf-8"):
        super(BytesIOWrapper, self).__init__()
        self.wrapped = wrapped
        self.encoding = encoding
        self.encoded = None

    def read(self, *args, **kwargs):
        if self.encoded is None:
            b, blen = codecs.getencoder(self.encoding)(self.wrapped)
            self.encoded = BytesIO(b)
        return self.encoded.read(*args, **kwargs)

    def read1(self, *args, **kwargs):
        if self.encoded is None:
            b = codecs.getencoder(self.encoding)(self.wrapped)
            self.encoded = BytesIO(b)
        return self.encoded.read1(*args, **kwargs)

    def readinto(self, *args, **kwargs):
        raise NotImplementedError()

    def readinto1(self, *args, **kwargs):
        raise NotImplementedError()

    def write(self, *args, **kwargs):
        raise NotImplementedError()


class InputSource(xmlreader.InputSource, object):
    """
    TODO:
    """

    def __init__(self, system_id=None):
        xmlreader.InputSource.__init__(self, system_id=system_id)
        self.content_type = None
        self.auto_close = False  # see Graph.parse(), true if opened by us

    def close(self):
        c = self.getCharacterStream()
        if c and hasattr(c, "close"):
            try:
                c.close()
            except Exception:
                pass
        f = self.getByteStream()
        if f and hasattr(f, "close"):
            try:
                f.close()
            except Exception:
                pass


class PythonInputSource(InputSource):
    """
    Constructs an RDFLib Parser InputSource from a Python data structure,
    for example, loaded from JSON with json.load or json.loads:

    >>> import json
    >>> as_string = \"\"\"{
    ...   "@context" : {"ex" : "http://example.com/ns#"},
    ...   "@graph": [{"@type": "ex:item", "@id": "#example"}]
    ... }\"\"\"
    >>> as_python = json.loads(as_string)
    >>> source = create_input_source(data=as_python)
    >>> isinstance(source, PythonInputSource)
    True
    """

    def __init__(self, data, system_id=None):
        self.content_type = None
        self.auto_close = False  # see Graph.parse(), true if opened by us
        self.public_id = None
        self.system_id = system_id
        self.data = data

    def getPublicId(self):
        return self.public_id

    def setPublicId(self, public_id):
        self.public_id = public_id

    def getSystemId(self):
        return self.system_id

    def setSystemId(self, system_id):
        self.system_id = system_id

    def close(self):
        self.data = None


class StringInputSource(InputSource):
    """
    Constructs an RDFLib Parser InputSource from a Python String or Bytes
    """

    def __init__(self, value, encoding="utf-8", system_id=None):
        super(StringInputSource, self).__init__(system_id)
        if isinstance(value, str):
            stream = StringIO(value)
            self.setCharacterStream(stream)
            self.setEncoding(encoding)
            b_stream = BytesIOWrapper(value, encoding)
            self.setByteStream(b_stream)
        else:
            stream = BytesIO(value)
            self.setByteStream(stream)
            c_stream = TextIOWrapper(stream, encoding)
            self.setCharacterStream(c_stream)
            self.setEncoding(c_stream.encoding)


headers = {
    "User-agent": "rdflib-%s (http://rdflib.net/; eikeon@eikeon.com)" % __version__
}


class URLInputSource(InputSource):
    """
    TODO:
    """

    def __init__(self, system_id=None, format=None):
        super(URLInputSource, self).__init__(system_id)
        self.url = system_id

        # copy headers to change
        myheaders = dict(headers)
        if format == "application/rdf+xml":
            myheaders["Accept"] = "application/rdf+xml, */*;q=0.1"
        elif format == "n3":
            myheaders["Accept"] = "text/n3, */*;q=0.1"
        elif format == "turtle":
            myheaders["Accept"] = "text/turtle,application/x-turtle, */*;q=0.1"
        elif format == "nt":
            myheaders["Accept"] = "text/plain, */*;q=0.1"
        elif format == "json-ld":
            myheaders[
                "Accept"
            ] = "application/ld+json, application/json;q=0.9, */*;q=0.1"
        else:
            myheaders["Accept"] = (
                "application/rdf+xml,text/rdf+n3;q=0.9,"
                + "application/xhtml+xml;q=0.5, */*;q=0.1"
            )

        req = Request(system_id, None, myheaders)

        def _urlopen(req: Request):
            try:
                return urlopen(req)
            except HTTPError as ex:
                # 308 (Permanent Redirect) is not supported by current python version(s)
                # See https://bugs.python.org/issue40321
                # This custom error handling should be removed once all
                # supported versions of python support 308.
                if ex.code == 308:
                    req.full_url = ex.headers.get("Location")
                    return _urlopen(req)
                else:
                    raise

        file = _urlopen(req)
        # Fix for issue 130 https://github.com/RDFLib/rdflib/issues/130
        self.url = file.geturl()  # in case redirections took place
        self.setPublicId(self.url)
        self.content_type = file.info().get("content-type")
        if self.content_type is not None:
            self.content_type = self.content_type.split(";", 1)[0]
        self.setByteStream(file)
        # TODO: self.setEncoding(encoding)
        self.response_info = file.info()  # a mimetools.Message instance

    def __repr__(self):
        return self.url


class FileInputSource(InputSource):
    def __init__(self, file):
        base = pathlib.Path.cwd().as_uri()
        system_id = URIRef(pathlib.Path(file.name).absolute().as_uri(), base=base)
        super(FileInputSource, self).__init__(system_id)
        self.file = file
        if isinstance(file, TextIOBase):  # Python3 unicode fp
            self.setCharacterStream(file)
            self.setEncoding(file.encoding)
            try:
                b = file.buffer
                self.setByteStream(b)
            except (AttributeError, LookupError):
                self.setByteStream(file)
        else:
            self.setByteStream(file)
            # We cannot set characterStream here because
            # we do not know the Raw Bytes File encoding.

    def __repr__(self):
        return repr(self.file)


def create_input_source(
    source=None,
    publicID=None,
    location=None,
    file=None,
    data: Optional[Union[str, bytes, bytearray, Dict[Any, Any]]] = None,
    format=None,
):
    """
    Return an appropriate InputSource instance for the given
    parameters.
    """

    # test that exactly one of source, location, file, and data is not None.
    non_empty_arguments = list(
        filter(
            lambda v: v is not None,
            [source, location, file, data],
        )
    )

    if len(non_empty_arguments) != 1:
        raise ValueError(
            "exactly one of source, location, file or data must be given",
        )

    input_source = None

    if source is not None:
        if isinstance(source, InputSource):
            input_source = source
        else:
            if isinstance(source, str):
                location = source
            elif isinstance(source, pathlib.PurePath):
                location = str(source)
            elif isinstance(source, bytes):
                data = source
            elif hasattr(source, "read") and not isinstance(source, Namespace):
                f = source
                input_source = InputSource()
                if hasattr(source, "encoding"):
                    input_source.setCharacterStream(source)
                    input_source.setEncoding(source.encoding)
                    try:
                        b = file.buffer
                        input_source.setByteStream(b)
                    except (AttributeError, LookupError):
                        input_source.setByteStream(source)
                else:
                    input_source.setByteStream(f)
                if f is sys.stdin:
                    input_source.setSystemId("file:///dev/stdin")
                elif hasattr(f, "name"):
                    input_source.setSystemId(f.name)
            else:
                raise Exception(
                    "Unexpected type '%s' for source '%s'" % (type(source), source)
                )

    absolute_location = None  # Further to fix for issue 130

    auto_close = False  # make sure we close all file handles we open

    if location is not None:
        (
            absolute_location,
            auto_close,
            file,
            input_source,
        ) = _create_input_source_from_location(
            file=file,
            format=format,
            input_source=input_source,
            location=location,
        )

    if file is not None:
        input_source = FileInputSource(file)

    if data is not None:
        if isinstance(data, dict):
            input_source = PythonInputSource(data)
            auto_close = True
        elif isinstance(data, (str, bytes, bytearray)):
            input_source = StringInputSource(data)
            auto_close = True
        else:
            raise RuntimeError(f"parse data can only str, or bytes. not: {type(data)}")

    if input_source is None:
        raise Exception("could not create InputSource")
    else:
        input_source.auto_close |= auto_close
        if publicID is not None:  # Further to fix for issue 130
            input_source.setPublicId(publicID)
        # Further to fix for issue 130
        elif input_source.getPublicId() is None:
            input_source.setPublicId(absolute_location or "")
        return input_source


def _create_input_source_from_location(file, format, input_source, location):
    # Fix for Windows problem https://github.com/RDFLib/rdflib/issues/145 and
    # https://github.com/RDFLib/rdflib/issues/1430
    # NOTE: using pathlib.Path.exists on a URL fails on windows as it is not a
    # valid path. However os.path.exists() returns false for a URL on windows
    # which is why it is being used instead.
    if os.path.exists(location):
        location = pathlib.Path(location).absolute().as_uri()

    base = pathlib.Path.cwd().as_uri()

    location = _iri2uri(location)
    absolute_location = URIRef(location, base=base)

    if absolute_location.startswith("file:///"):
        filename = url2pathname(absolute_location.replace("file:///", "/"))
        file = open(filename, "rb")
    else:
        input_source = URLInputSource(absolute_location, format)

    auto_close = True
    # publicID = publicID or absolute_location  # Further to fix
    # for issue 130

    return absolute_location, auto_close, file, input_source
