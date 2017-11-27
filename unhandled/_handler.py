
import abc
import os
import re
import sys
import datetime
from pprint import pformat

import six

__all__ = ['BaseHandler', 'VerboseExceptionHandler', 'SimpleExceptionHandler']


class BaseHandler(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def test(self, exc_type, exc_value, exc_traceback):
        return True

    @abc.abstractmethod
    def handle(self, exc_type, exc_value, exc_traceback):
        pass


class VerboseExceptionHandler(BaseHandler):
    def __init__(self):
        self.exc_type = None
        self.exc_value = None
        self.tb = None

    def test(self, exc_type, exc_value, exc_traceback):
        return True

    def handle(self, exc_type, exc_value, exc_traceback):
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.tb = exc_traceback

        return self.get_traceback_text()

    def get_traceback_data(self):
        """Return a dictionary containing traceback information."""
        frames = self.get_traceback_frames()
        for i, frame in enumerate(frames):
            if 'vars' in frame:
                frame_vars = []
                for k, v in frame['vars']:
                    v = pformat(v)
                    # Trim large blobs of data
                    if len(v) > 4096:
                        v = '%s... <trimmed %d bytes string>' % (v[0:4096], len(v))
                    frame_vars.append((k, v))
                frame['vars'] = frame_vars
            frames[i] = frame

        user_str = os.getenv('USERNAME')

        c = {
            'frames': frames,
            'sys_executable': sys.executable,
            'sys_version_info': '%d.%d.%d' % sys.version_info[0:3],
            'server_time': datetime.datetime.now(),
            'sys_path': sys.path,
        }

        # Check whether exception info is available
        if self.exc_type:
            c['exception_type'] = self.exc_type.__name__
        if self.exc_value:
            c['exception_value'] = str(self.exc_value)
        if frames:
            c['lastframe'] = frames[-1]
        return c

    def get_traceback_text(self):
        """Return plain text version of debug 500 HTTP error page."""
        c = self.get_traceback_data()
        text = '''Python Executable: {sys_executable}
Python Version: {sys_version_info}
Python Path: {sys_path}
Server time: {server_time}

Traceback:
{frametext}

{exception_type}: {exception_value}
'''

        frames = '\n'.join(map(self.render_frame, c['frames']))

        return text.format(frametext=frames, **c)

    def _get_lines_from_file(self, filename, lineno, context_lines, loader=None, module_name=None):
        """
        Returns context_lines before and after lineno from file.
        Returns (pre_context_lineno, pre_context, context_line, post_context).
        """
        source = None
        if loader is not None and hasattr(loader, "get_source"):
            try:
                source = loader.get_source(module_name)
            except ImportError:
                pass
            if source is not None:
                source = source.splitlines()
        if source is None:
            try:
                with open(filename, 'rb') as fp:
                    source = fp.read().splitlines()
            except (OSError, IOError):
                pass
        if source is None and filename == '<stdin>':
            return lineno, [], '<unknown>', []
        if source is None and filename == '<maya console>':
            return lineno - 1, [], '<unknown>', []
        if source is None:
            return None, [], None, []

        # If we just read the source from a file, or if the loader did not
        # apply tokenize.detect_encoding to decode the source into a Unicode
        # string, then we should do that ourselves.
        if isinstance(source[0], six.binary_type):
            encoding = 'ascii'
            for line in source[:2]:
                # File coding may be specified. Match pattern from PEP-263
                # (http://www.python.org/dev/peps/pep-0263/)
                match = re.search(br'coding[:=]\s*([-\w.]+)', line)
                if match:
                    encoding = match.group(1).decode('ascii')
                    break
            source = [six.text_type(sline, encoding, 'replace') for sline in source]

        lower_bound = max(0, lineno - context_lines)
        upper_bound = lineno + context_lines + 1

        pre_context = source[lower_bound:lineno]
        context_line = source[lineno]
        post_context = source[lineno + 1:upper_bound]

        return lower_bound, pre_context, context_line, post_context

    def get_traceback_frames(self):
        def explicit_or_implicit_cause(exc_value):
            explicit = getattr(exc_value, '__cause__', None)
            implicit = getattr(exc_value, '__context__', None)
            return explicit or implicit

        # Get the exception and all its causes
        exceptions = []
        exc_value = self.exc_value
        while exc_value:
            exceptions.append(exc_value)
            exc_value = explicit_or_implicit_cause(exc_value)

        frames = []
        # No exceptions were supplied to ExceptionReporter
        if not exceptions:
            return frames

        # In case there's just one exception (always in Python 2,
        # sometimes in Python 3), take the traceback from self.tb (Python 2
        # doesn't have a __traceback__ attribute on Exception)
        exc_value = exceptions.pop()
        tb = self.tb if six.PY2 or not exceptions else exc_value.__traceback__

        while tb is not None:
            # Support for __traceback_hide__ which is used by a few libraries
            # to hide internal frames.
            if tb.tb_frame.f_locals.get('__traceback_hide__'):
                tb = tb.tb_next
                continue
            filename = tb.tb_frame.f_code.co_filename
            function = tb.tb_frame.f_code.co_name
            lineno = tb.tb_lineno - 1
            loader = tb.tb_frame.f_globals.get('__loader__')
            module_name = tb.tb_frame.f_globals.get('__name__') or ''
            pre_context_lineno, pre_context, context_line, post_context = self._get_lines_from_file(
                filename, lineno, 2, loader, module_name,
            )
            if pre_context_lineno is not None:
                frames.append({
                    'exc_cause': explicit_or_implicit_cause(exc_value),
                    'exc_cause_explicit': getattr(exc_value, '__cause__', True),
                    'tb': tb,
                    'type': 'user',
                    'filename': filename,
                    'function': function,
                    'lineno': lineno if filename == '<maya console>' else lineno + 1,
                    'vars': list(tb.tb_frame.f_locals.items()),
                    'id': id(tb),
                    'pre_context': pre_context,
                    'context_line': context_line,
                    'post_context': post_context,
                    'pre_context_lineno': pre_context_lineno + 1,
                })

            # If the traceback for current exception is consumed, try the
            # other exception.
            if six.PY2:
                tb = tb.tb_next
            elif not tb.tb_next and exceptions:
                exc_value = exceptions.pop()
                tb = exc_value.__traceback__
            else:
                tb = tb.tb_next

        return frames

    def render_frame(self, frame):
        sep = '*' * 80
        arrow = '--->'
        text = """{sep}
File "{filename}", line {lineno}, in {function}
{pre}{arrow} {context_lineno} {context_line}
{post}

Local Variables:
{locals}
"""
        vars = ''
        for k, v in frame['vars']:
            vars += '{k: >12}: {v}\n'.format(k=k, v=v)

        pre = ''
        num = frame['pre_context_lineno']
        for line in frame['pre_context']:
            pre += '{0} {1} {2}\n'.format(' '*len(arrow), num, line)
            num += 1

        post = ''
        context_lineno = num
        num += 1
        for line in frame['post_context']:
            post += '{0} {1} {2}\n'.format(' ' * len(arrow), num, line)
            num += 1

        # pre = '\n'.join(frame['pre_context'])
        # post = '\n'.join(frame['post_context'])

        return text.format(sep=sep, locals=vars, pre=pre, post=post, arrow=arrow, context_lineno=context_lineno, **frame)


class SimpleExceptionHandler(BaseHandler):
    def test(self, exc_type, exc_value, exc_traceback):
        return 'name' not in str(exc_value).lower()

    def handle(self, exc_type, exc_value, exc_traceback):
        return str(exc_value)
