# Copyright (c) 2015 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import absolute_import

import logging

import opentracing
from opentracing.ext import tags
from opentracing_instrumentation import get_current_span
from ._singleton import singleton

log = logging.getLogger(__name__)


@singleton
def install_patches():
    import urllib
    import urlparse

    log.info('Instrumenting urllib methods for tracing')

    class TracedURLOpener(urllib.FancyURLopener):

        def open(self, fullurl, data=None):
            parsed_url = urlparse.urlparse(fullurl)
            host = parsed_url.hostname or None
            port = parsed_url.port or None

            if get_current_span() is None:
                span = opentracing.tracer.begin_trace(
                    operation_name='urllib'
                )  # TODO pass client=True
            else:
                span = get_current_span().start_child(operation_name='http')

            # use span as context manager so that its finish() method is called
            with span:
                span.add_tag('http.url', fullurl)
                if host:
                    span.add_tag(tags.PEER_HOST_IPV4, host)
                if port:
                    span.add_tag(tags.PEER_PORT, port)
                # TODO add callee service name
                # TODO add headers to propagate trace
                # cannot use super here, this is an old style class
                fileobj = urllib.FancyURLopener.open(self, fullurl, data)
                if fileobj.getcode() is not None:
                    span.add_tag('status_code', str(fileobj.getcode()))

            return fileobj

        def retrieve(self, url, filename=None, reporthook=None, data=None):
            raise NotImplementedError

    urllib._urlopener = TracedURLOpener()