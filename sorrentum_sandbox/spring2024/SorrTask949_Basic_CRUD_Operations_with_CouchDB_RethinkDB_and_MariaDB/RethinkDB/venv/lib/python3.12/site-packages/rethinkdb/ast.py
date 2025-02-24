# Copyright 2018 RethinkDB
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file incorporates work covered by the following copyright:
# Copyright 2010-2016 RethinkDB, all rights reserved.

__all__ = ["expr", "RqlQuery", "ReQLEncoder", "ReQLDecoder", "Repl"]


import base64
import binascii
import datetime
import json
import sys
import threading

from rethinkdb import ql2_pb2
from rethinkdb.errors import (QueryPrinter, ReqlDriverCompileError,
                              ReqlDriverError, T)

if sys.version_info < (3, 3):
    # python < 3.3 uses collections
    import collections
else:
    # but collections is deprecated from python >= 3.3
    import collections.abc as collections

P_TERM = ql2_pb2.Term.TermType

try:
    unicode
except NameError:
    unicode = str

try:
    xrange
except NameError:
    xrange = range


def dict_items(dictionary):
    return list(dictionary.items())


class Repl(object):
    thread_data = threading.local()
    repl_active = False

    @classmethod
    def get(cls):
        if "repl" in cls.thread_data.__dict__:
            return cls.thread_data.repl
        else:
            return None

    @classmethod
    def set(cls, conn):
        cls.thread_data.repl = conn
        cls.repl_active = True

    @classmethod
    def clear(cls):
        if "repl" in cls.thread_data.__dict__:
            del cls.thread_data.repl
        cls.repl_active = False


# This is both an external function and one used extensively
# internally to convert coerce python values to RQL types


def expr(val, nesting_depth=20):
    """
    Convert a Python primitive into a RQL primitive value
    """
    if not isinstance(nesting_depth, int):
        raise ReqlDriverCompileError("Second argument to `r.expr` must be a number.")

    if nesting_depth <= 0:
        raise ReqlDriverCompileError("Nesting depth limit exceeded.")

    if isinstance(val, RqlQuery):
        return val
    elif isinstance(val, collections.Callable):
        return Func(val)
    elif isinstance(val, (datetime.datetime, datetime.date)):
        if not hasattr(val, "tzinfo") or not val.tzinfo:
            raise ReqlDriverCompileError(
                """Cannot convert %s to ReQL time object
            without timezone information. You can add timezone information with
            the third party module \"pytz\" or by constructing ReQL compatible
            timezone values with r.make_timezone(\"[+-]HH:MM\"). Alternatively,
            use one of ReQL's bultin time constructors, r.now, r.time,
            or r.iso8601.
            """
                % (type(val).__name__)
            )
        return ISO8601(val.isoformat())
    elif isinstance(val, RqlBinary):
        return Binary(val)
    elif isinstance(val, (str, unicode)):
        return Datum(val)
    elif isinstance(val, bytes):
        return Binary(val)
    elif isinstance(val, collections.Mapping):
        # MakeObj doesn't take the dict as a keyword args to avoid
        # conflicting with the `self` parameter.
        obj = {}
        for k, v in dict_items(val):
            obj[k] = expr(v, nesting_depth - 1)
        return MakeObj(obj)
    elif isinstance(val, collections.Iterable):
        val = [expr(v, nesting_depth - 1) for v in val]
        return MakeArray(*val)
    else:
        return Datum(val)


class RqlQuery(object):
    # Instantiate this AST node with the given pos and opt args
    def __init__(self, *args, **optargs):
        self._args = [expr(e) for e in args]

        self.optargs = {}
        for key, value in dict_items(optargs):
            self.optargs[key] = expr(value)

    # Send this query to the server to be executed
    def run(self, c=None, **global_optargs):
        if c is None:
            c = Repl.get()
            if c is None:
                if Repl.repl_active:
                    raise ReqlDriverError(
                        "RqlQuery.run must be given a connection to run on. A default connection has been set with "
                        "`repl()` on another thread, but not this one."
                    )
                else:
                    raise ReqlDriverError(
                        "RqlQuery.run must be given a connection to run on."
                    )

        return c._start(self, **global_optargs)

    def __str__(self):
        printer = QueryPrinter(self)
        return printer.print_query()

    def __repr__(self):
        return "<RqlQuery instance: %s >" % str(self)

    # Compile this query to a json-serializable object
    def build(self):
        res = [self.term_type, self._args]
        if len(self.optargs) > 0:
            res.append(self.optargs)
        return res

    # The following are all operators and methods that operate on
    # Rql queries to build up more complex operations

    # Comparison operators
    def __eq__(self, other):
        return Eq(self, other)

    def __ne__(self, other):
        return Ne(self, other)

    def __lt__(self, other):
        return Lt(self, other)

    def __le__(self, other):
        return Le(self, other)

    def __gt__(self, other):
        return Gt(self, other)

    def __ge__(self, other):
        return Ge(self, other)

    # Numeric operators
    def __invert__(self):
        return Not(self)

    def __add__(self, other):
        return Add(self, other)

    def __radd__(self, other):
        return Add(other, self)

    def __sub__(self, other):
        return Sub(self, other)

    def __rsub__(self, other):
        return Sub(other, self)

    def __mul__(self, other):
        return Mul(self, other)

    def __rmul__(self, other):
        return Mul(other, self)

    def __div__(self, other):
        return Div(self, other)

    def __rdiv__(self, other):
        return Div(other, self)

    def __truediv__(self, other):
        return Div(self, other)

    def __rtruediv__(self, other):
        return Div(other, self)

    def __mod__(self, other):
        return Mod(self, other)

    def __rmod__(self, other):
        return Mod(other, self)

    def __and__(self, other):
        query = And(self, other)
        query.set_infix()
        return query

    def __rand__(self, other):
        query = And(other, self)
        query.set_infix()
        return query

    def __or__(self, other):
        query = Or(self, other)
        query.set_infix()
        return query

    def __ror__(self, other):
        query = Or(other, self)
        query.set_infix()
        return query

    # Non-operator versions of the above

    def eq(self, *args):
        return Eq(self, *args)

    def ne(self, *args):
        return Ne(self, *args)

    def lt(self, *args):
        return Lt(self, *args)

    def le(self, *args):
        return Le(self, *args)

    def gt(self, *args):
        return Gt(self, *args)

    def ge(self, *args):
        return Ge(self, *args)

    def add(self, *args):
        return Add(self, *args)

    def sub(self, *args):
        return Sub(self, *args)

    def mul(self, *args):
        return Mul(self, *args)

    def div(self, *args):
        return Div(self, *args)

    def mod(self, *args):
        return Mod(self, *args)

    def bit_and(self, *args):
        return BitAnd(self, *args)

    def bit_or(self, *args):
        return BitOr(self, *args)

    def bit_xor(self, *args):
        return BitXor(self, *args)

    def bit_not(self, *args):
        return BitNot(self, *args)

    def bit_sal(self, *args):
        return BitSal(self, *args)

    def bit_sar(self, *args):
        return BitSar(self, *args)

    def floor(self, *args):
        return Floor(self, *args)

    def ceil(self, *args):
        return Ceil(self, *args)

    def round(self, *args):
        return Round(self, *args)

    def and_(self, *args):
        return And(self, *args)

    def or_(self, *args):
        return Or(self, *args)

    def not_(self, *args):
        return Not(self, *args)

    # N.B. Cannot use 'in' operator because it must return a boolean
    def contains(self, *args):
        return Contains(self, *[func_wrap(arg) for arg in args])

    def has_fields(self, *args):
        return HasFields(self, *args)

    def with_fields(self, *args):
        return WithFields(self, *args)

    def keys(self, *args):
        return Keys(self, *args)

    def values(self, *args):
        return Values(self, *args)

    def changes(self, *args, **kwargs):
        return Changes(self, *args, **kwargs)

    # Polymorphic object/sequence operations
    def pluck(self, *args):
        return Pluck(self, *args)

    def without(self, *args):
        return Without(self, *args)

    def do(self, *args):
        return FunCall(self, *args)

    def default(self, *args):
        return Default(self, *args)

    def update(self, *args, **kwargs):
        return Update(self, *[func_wrap(arg) for arg in args], **kwargs)

    def replace(self, *args, **kwargs):
        return Replace(self, *[func_wrap(arg) for arg in args], **kwargs)

    def delete(self, *args, **kwargs):
        return Delete(self, *args, **kwargs)

    # Rql type inspection
    def coerce_to(self, *args):
        return CoerceTo(self, *args)

    def ungroup(self, *args):
        return Ungroup(self, *args)

    def type_of(self, *args):
        return TypeOf(self, *args)

    def merge(self, *args):
        return Merge(self, *[func_wrap(arg) for arg in args])

    def append(self, *args):
        return Append(self, *args)

    def prepend(self, *args):
        return Prepend(self, *args)

    def difference(self, *args):
        return Difference(self, *args)

    def set_insert(self, *args):
        return SetInsert(self, *args)

    def set_union(self, *args):
        return SetUnion(self, *args)

    def set_intersection(self, *args):
        return SetIntersection(self, *args)

    def set_difference(self, *args):
        return SetDifference(self, *args)

    # Operator used for get attr / nth / slice. Non-operator versions below
    # in cases of ambiguity
    def __getitem__(self, index):
        if isinstance(index, slice):
            if index.stop:
                return Slice(self, index.start or 0, index.stop, bracket_operator=True)
            else:
                return Slice(
                    self,
                    index.start or 0,
                    -1,
                    right_bound="closed",
                    bracket_operator=True,
                )
        else:
            return Bracket(self, index, bracket_operator=True)

    def __iter__(*args, **kwargs):
        raise ReqlDriverError(
            "__iter__ called on an RqlQuery object.\n"
            "To iterate over the results of a query, call run first.\n"
            "To iterate inside a query, use map or for_each."
        )

    def get_field(self, *args):
        return GetField(self, *args)

    def nth(self, *args):
        return Nth(self, *args)

    def to_json(self, *args):
        return ToJsonString(self, *args)

    def to_json_string(self, *args):
        return ToJsonString(self, *args)

    def match(self, *args):
        return Match(self, *args)

    def split(self, *args):
        return Split(self, *args)

    def upcase(self, *args):
        return Upcase(self, *args)

    def downcase(self, *args):
        return Downcase(self, *args)

    def is_empty(self, *args):
        return IsEmpty(self, *args)

    def offsets_of(self, *args):
        return OffsetsOf(self, *[func_wrap(arg) for arg in args])

    def slice(self, *args, **kwargs):
        return Slice(self, *args, **kwargs)

    def skip(self, *args):
        return Skip(self, *args)

    def limit(self, *args):
        return Limit(self, *args)

    def reduce(self, *args):
        return Reduce(self, *[func_wrap(arg) for arg in args])

    def sum(self, *args):
        return Sum(self, *[func_wrap(arg) for arg in args])

    def avg(self, *args):
        return Avg(self, *[func_wrap(arg) for arg in args])

    def min(self, *args, **kwargs):
        return Min(self, *[func_wrap(arg) for arg in args], **kwargs)

    def max(self, *args, **kwargs):
        return Max(self, *[func_wrap(arg) for arg in args], **kwargs)

    def map(self, *args):
        if len(args) > 0:
            # `func_wrap` only the last argument
            return Map(self, *(args[:-1] + (func_wrap(args[-1]),)))
        else:
            return Map(self)

    def fold(self, *args, **kwargs):
        if len(args) > 0:
            # `func_wrap` only the last argument before optional arguments
            # Also `func_wrap` keyword arguments

            # Nice syntax not supported by python2.6
            kwfuncargs = {}
            for arg_name in kwargs:
                kwfuncargs[arg_name] = func_wrap(kwargs[arg_name])
            return Fold(self, *(args[:-1] + (func_wrap(args[-1]),)), **kwfuncargs)
        else:
            return Fold(self)

    def filter(self, *args, **kwargs):
        return Filter(self, *[func_wrap(arg) for arg in args], **kwargs)

    def concat_map(self, *args):
        return ConcatMap(self, *[func_wrap(arg) for arg in args])

    def order_by(self, *args, **kwargs):
        args = [arg if isinstance(arg, (Asc, Desc)) else func_wrap(arg) for arg in args]
        return OrderBy(self, *args, **kwargs)

    def between(self, *args, **kwargs):
        return Between(self, *args, **kwargs)

    def distinct(self, *args, **kwargs):
        return Distinct(self, *args, **kwargs)

    # NB: Can't overload __len__ because Python doesn't
    #     allow us to return a non-integer
    def count(self, *args):
        return Count(self, *[func_wrap(arg) for arg in args])

    def union(self, *args, **kwargs):
        func_kwargs = {}
        for key in kwargs:
            func_kwargs[key] = func_wrap(kwargs[key])
        return Union(self, *args, **func_kwargs)

    def inner_join(self, *args):
        return InnerJoin(self, *args)

    def outer_join(self, *args):
        return OuterJoin(self, *args)

    def eq_join(self, *args, **kwargs):
        return EqJoin(self, *[func_wrap(arg) for arg in args], **kwargs)

    def zip(self, *args):
        return Zip(self, *args)

    def group(self, *args, **kwargs):
        return Group(self, *[func_wrap(arg) for arg in args], **kwargs)

    def branch(self, *args):
        return Branch(self, *args)

    def for_each(self, *args):
        return ForEach(self, *[func_wrap(arg) for arg in args])

    def info(self, *args):
        return Info(self, *args)

    # Array only operations
    def insert_at(self, *args):
        return InsertAt(self, *args)

    def splice_at(self, *args):
        return SpliceAt(self, *args)

    def delete_at(self, *args):
        return DeleteAt(self, *args)

    def change_at(self, *args):
        return ChangeAt(self, *args)

    def sample(self, *args):
        return Sample(self, *args)

    # Time support

    def to_iso8601(self, *args):
        return ToISO8601(self, *args)

    def to_epoch_time(self, *args):
        return ToEpochTime(self, *args)

    def during(self, *args, **kwargs):
        return During(self, *args, **kwargs)

    def date(self, *args):
        return Date(self, *args)

    def time_of_day(self, *args):
        return TimeOfDay(self, *args)

    def timezone(self, *args):
        return Timezone(self, *args)

    def year(self, *args):
        return Year(self, *args)

    def month(self, *args):
        return Month(self, *args)

    def day(self, *args):
        return Day(self, *args)

    def day_of_week(self, *args):
        return DayOfWeek(self, *args)

    def day_of_year(self, *args):
        return DayOfYear(self, *args)

    def hours(self, *args):
        return Hours(self, *args)

    def minutes(self, *args):
        return Minutes(self, *args)

    def seconds(self, *args):
        return Seconds(self, *args)

    def in_timezone(self, *args):
        return InTimezone(self, *args)

    # Geospatial support
    def to_geojson(self, *args):
        return ToGeoJson(self, *args)

    def distance(self, *args, **kwargs):
        return Distance(self, *args, **kwargs)

    def intersects(self, *args):
        return Intersects(self, *args)

    def includes(self, *args):
        return Includes(self, *args)

    def fill(self, *args):
        return Fill(self, *args)

    def polygon_sub(self, *args):
        return PolygonSub(self, *args)


# These classes define how nodes are printed by overloading `compose`
def needs_wrap(arg):
    return isinstance(arg, (Datum, MakeArray, MakeObj))


class RqlBoolOperQuery(RqlQuery):
    def __init__(self, *args, **optargs):
        self.infix = False
        RqlQuery.__init__(self, *args, **optargs)

    def set_infix(self):
        self.infix = True

    def compose(self, args, optargs):
        t_args = [
            T("r.expr(", args[i], ")") if needs_wrap(self._args[i]) else args[i]
            for i in xrange(len(args))
        ]

        if self.infix:
            return T("(", T(*t_args, intsp=[" ", self.st_infix, " "]), ")")
        else:
            return T("r.", self.statement, "(", T(*t_args, intsp=", "), ")")


class RqlBiOperQuery(RqlQuery):
    def compose(self, args, optargs):
        t_args = [
            T("r.expr(", args[i], ")") if needs_wrap(self._args[i]) else args[i]
            for i in xrange(len(args))
        ]
        return T("(", T(*t_args, intsp=[" ", self.statement, " "]), ")")


class RqlBiCompareOperQuery(RqlBiOperQuery):
    def __init__(self, *args, **optargs):
        RqlBiOperQuery.__init__(self, *args, **optargs)

        for arg in args:
            try:
                if arg.infix:
                    err = (
                        "Calling '%s' on result of infix bitwise operator:\n"
                        "%s.\n"
                        "This is almost always a precedence error.\n"
                        "Note that `a < b | b < c` <==> `a < (b | b) < c`.\n"
                        "If you really want this behavior, use `.or_` or "
                        "`.and_` instead."
                    )
                    raise ReqlDriverCompileError(
                        err % (self.statement, QueryPrinter(self).print_query())
                    )
            except AttributeError:
                pass  # No infix attribute, so not possible to be an infix bool operator


class RqlTopLevelQuery(RqlQuery):
    def compose(self, args, optargs):
        args.extend([T(key, "=", value) for key, value in dict_items(optargs)])
        return T("r.", self.statement, "(", T(*(args), intsp=", "), ")")


class RqlMethodQuery(RqlQuery):
    def compose(self, args, optargs):
        if len(args) == 0:
            return T("r.", self.statement, "()")

        if needs_wrap(self._args[0]):
            args[0] = T("r.expr(", args[0], ")")

        restargs = args[1:]
        restargs.extend([T(k, "=", v) for k, v in dict_items(optargs)])
        restargs = T(*restargs, intsp=", ")

        return T(args[0], ".", self.statement, "(", restargs, ")")


class RqlBracketQuery(RqlMethodQuery):
    def __init__(self, *args, **optargs):
        if "bracket_operator" in optargs:
            self.bracket_operator = optargs["bracket_operator"]
            del optargs["bracket_operator"]
        else:
            self.bracket_operator = False

        RqlMethodQuery.__init__(self, *args, **optargs)

    def compose(self, args, optargs):
        if self.bracket_operator:
            if needs_wrap(self._args[0]):
                args[0] = T("r.expr(", args[0], ")")
            return T(args[0], "[", T(*args[1:], intsp=[","]), "]")
        else:
            return RqlMethodQuery.compose(self, args, optargs)


class RqlTzinfo(datetime.tzinfo):
    def __init__(self, offsetstr):
        hours, minutes = map(int, offsetstr.split(":"))

        self.offsetstr = offsetstr
        self.delta = datetime.timedelta(hours=hours, minutes=minutes)

    def __getinitargs__(self):
        return (self.offsetstr,)

    def __copy__(self):
        return RqlTzinfo(self.offsetstr)

    def __deepcopy__(self, memo):
        return RqlTzinfo(self.offsetstr)

    def utcoffset(self, dt):
        return self.delta

    def tzname(self, dt):
        return self.offsetstr

    def dst(self, dt):
        return datetime.timedelta(0)


# Python only allows immutable built-in types to be hashed, such as
# for keys in a dict This means we can't use lists or dicts as keys in
# grouped data objects, so we convert them to tuples and frozensets,
# respectively.  This may make it a little harder for users to work
# with converted grouped data, unless they do a simple iteration over
# the result
def recursively_make_hashable(obj):
    if isinstance(obj, list):
        return tuple([recursively_make_hashable(i) for i in obj])
    elif isinstance(obj, dict):
        return frozenset(
            [(k, recursively_make_hashable(v)) for k, v in dict_items(obj)]
        )
    return obj


class ReQLEncoder(json.JSONEncoder):
    """
    Default JSONEncoder subclass to handle query conversion.
    """

    def __init__(self):
        json.JSONEncoder.__init__(
            self,
            ensure_ascii=False,
            allow_nan=False,
            check_circular=False,
            separators=(",", ":"),
        )

    def default(self, obj):
        if isinstance(obj, RqlQuery):
            return obj.build()
        return json.JSONEncoder.default(self, obj)


class ReQLDecoder(json.JSONDecoder):
    """
    Default JSONDecoder subclass to handle pseudo-type conversion.
    """

    def __init__(self, reql_format_opts=None):
        json.JSONDecoder.__init__(self, object_hook=self.convert_pseudotype)
        self.reql_format_opts = reql_format_opts or {}

    def convert_time(self, obj):
        if "epoch_time" not in obj:
            raise ReqlDriverError(
                (
                    "pseudo-type TIME object %s does not "
                    + 'have expected field "epoch_time".'
                )
                % json.dumps(obj)
            )

        if "timezone" in obj:
            return datetime.datetime.fromtimestamp(
                obj["epoch_time"], RqlTzinfo(obj["timezone"])
            )
        else:
            return datetime.datetime.utcfromtimestamp(obj["epoch_time"])

    @staticmethod
    def convert_grouped_data(obj):
        if "data" not in obj:
            raise ReqlDriverError(
                (
                    "pseudo-type GROUPED_DATA object"
                    + ' %s does not have the expected field "data".'
                )
                % json.dumps(obj)
            )
        return dict([(recursively_make_hashable(k), v) for k, v in obj["data"]])

    @staticmethod
    def convert_binary(obj):
        if "data" not in obj:
            raise ReqlDriverError(
                (
                    "pseudo-type BINARY object %s does not have "
                    + 'the expected field "data".'
                )
                % json.dumps(obj)
            )
        return RqlBinary(base64.b64decode(obj["data"].encode("utf-8")))

    def convert_pseudotype(self, obj):
        reql_type = obj.get("$reql_type$")
        if reql_type is not None:
            if reql_type == "TIME":
                time_format = self.reql_format_opts.get("time_format")
                if time_format is None or time_format == "native":
                    # Convert to native python datetime object
                    return self.convert_time(obj)
                elif time_format != "raw":
                    raise ReqlDriverError(
                        'Unknown time_format run option "%s".' % time_format
                    )
            elif reql_type == "GROUPED_DATA":
                group_format = self.reql_format_opts.get("group_format")
                if group_format is None or group_format == "native":
                    return self.convert_grouped_data(obj)
                elif group_format != "raw":
                    raise ReqlDriverError(
                        'Unknown group_format run option "%s".' % group_format
                    )
            elif reql_type == "GEOMETRY":
                # No special support for this. Just return the raw object
                return obj
            elif reql_type == "BINARY":
                binary_format = self.reql_format_opts.get("binary_format")
                if binary_format is None or binary_format == "native":
                    return self.convert_binary(obj)
                elif binary_format != "raw":
                    raise ReqlDriverError(
                        'Unknown binary_format run option "%s".' % binary_format
                    )
            else:
                raise ReqlDriverError("Unknown pseudo-type %s" % reql_type)
        # If there was no pseudotype, or the relevant format is raw, return
        # the original object
        return obj


# This class handles the conversion of RQL terminal types in both directions
# Going to the server though it does not support R_ARRAY or R_OBJECT as those
# are alternately handled by the MakeArray and MakeObject nodes. Why do this?
# MakeArray and MakeObject are more flexible, allowing us to construct array
# and object expressions from nested RQL expressions. Constructing pure
# R_ARRAYs and R_OBJECTs would require verifying that at all nested levels
# our arrays and objects are composed only of basic types.
class Datum(RqlQuery):
    def __init__(self, val):
        super(Datum, self).__init__()
        self.data = val

    def build(self):
        return self.data

    def compose(self, args, optargs):
        return repr(self.data)


class MakeArray(RqlQuery):
    term_type = P_TERM.MAKE_ARRAY

    def compose(self, args, optargs):
        return T("[", T(*args, intsp=", "), "]")


class MakeObj(RqlQuery):
    term_type = P_TERM.MAKE_OBJ

    # We cannot inherit from RqlQuery because of potential conflicts with
    # the `self` parameter. This is not a problem for other RqlQuery sub-
    # classes unless we add a 'self' optional argument to one of them.
    # TODO: @gabor-boros Figure out is the above still an issue or not.
    def __init__(self, obj_dict):
        super(MakeObj, self).__init__()
        for key, value in dict_items(obj_dict):
            if not isinstance(key, (str, unicode)):
                raise ReqlDriverCompileError("Object keys must be strings.")
            self.optargs[key] = expr(value)

    def build(self):
        return self.optargs

    def compose(self, args, optargs):
        return T(
            "r.expr({",
            T(
                *[T(repr(key), ": ", value) for key, value in dict_items(optargs)],
                intsp=", "
            ),
            "})",
        )


class Var(RqlQuery):
    term_type = P_TERM.VAR

    def compose(self, args, optargs):
        return "var_" + args[0]


class JavaScript(RqlTopLevelQuery):
    term_type = P_TERM.JAVASCRIPT
    statement = "js"


class Http(RqlTopLevelQuery):
    term_type = P_TERM.HTTP
    statement = "http"


class UserError(RqlTopLevelQuery):
    term_type = P_TERM.ERROR
    statement = "error"


class Random(RqlTopLevelQuery):
    term_type = P_TERM.RANDOM
    statement = "random"


class Changes(RqlMethodQuery):
    term_type = P_TERM.CHANGES
    statement = "changes"


class Default(RqlMethodQuery):
    term_type = P_TERM.DEFAULT
    statement = "default"


class ImplicitVar(RqlQuery):
    term_type = P_TERM.IMPLICIT_VAR

    def __call__(self, *args, **kwargs):
        raise TypeError("'r.row' is not callable, use 'r.row[...]' instead")

    def compose(self, args, optargs):
        return "r.row"


class Eq(RqlBiCompareOperQuery):
    term_type = P_TERM.EQ
    statement = "=="


class Ne(RqlBiCompareOperQuery):
    term_type = P_TERM.NE
    statement = "!="


class Lt(RqlBiCompareOperQuery):
    term_type = P_TERM.LT
    statement = "<"


class Le(RqlBiCompareOperQuery):
    term_type = P_TERM.LE
    statement = "<="


class Gt(RqlBiCompareOperQuery):
    term_type = P_TERM.GT
    statement = ">"


class Ge(RqlBiCompareOperQuery):
    term_type = P_TERM.GE
    statement = ">="


class Not(RqlQuery):
    term_type = P_TERM.NOT

    def compose(self, args, optargs):
        if isinstance(self._args[0], Datum):
            args[0] = T("r.expr(", args[0], ")")
        return T("(~", args[0], ")")


class Add(RqlBiOperQuery):
    term_type = P_TERM.ADD
    statement = "+"


class Sub(RqlBiOperQuery):
    term_type = P_TERM.SUB
    statement = "-"


class Mul(RqlBiOperQuery):
    term_type = P_TERM.MUL
    statement = "*"


class Div(RqlBiOperQuery):
    term_type = P_TERM.DIV
    statement = "/"


class Mod(RqlBiOperQuery):
    term_type = P_TERM.MOD
    statement = "%"


class BitAnd(RqlBoolOperQuery):
    term_type = P_TERM.BIT_AND
    statement = "bit_and"


class BitOr(RqlBoolOperQuery):
    term_type = P_TERM.BIT_OR
    statement = "bit_or"


class BitXor(RqlBoolOperQuery):
    term_type = P_TERM.BIT_XOR
    statement = "bit_xor"


class BitNot(RqlMethodQuery):
    term_type = P_TERM.BIT_NOT
    statement = "bit_not"


class BitSal(RqlBoolOperQuery):
    term_type = P_TERM.BIT_SAL
    statement = "bit_sal"


class BitSar(RqlBoolOperQuery):
    term_type = P_TERM.BIT_SAR
    statement = "bit_sar"


class Floor(RqlMethodQuery):
    term_type = P_TERM.FLOOR
    statement = "floor"


class Ceil(RqlMethodQuery):
    term_type = P_TERM.CEIL
    statement = "ceil"


class Round(RqlMethodQuery):
    term_type = P_TERM.ROUND
    statement = "round"


class Append(RqlMethodQuery):
    term_type = P_TERM.APPEND
    statement = "append"


class Prepend(RqlMethodQuery):
    term_type = P_TERM.PREPEND
    statement = "prepend"


class Difference(RqlMethodQuery):
    term_type = P_TERM.DIFFERENCE
    statement = "difference"


class SetInsert(RqlMethodQuery):
    term_type = P_TERM.SET_INSERT
    statement = "set_insert"


class SetUnion(RqlMethodQuery):
    term_type = P_TERM.SET_UNION
    statement = "set_union"


class SetIntersection(RqlMethodQuery):
    term_type = P_TERM.SET_INTERSECTION
    statement = "set_intersection"


class SetDifference(RqlMethodQuery):
    term_type = P_TERM.SET_DIFFERENCE
    statement = "set_difference"


class Slice(RqlBracketQuery):
    term_type = P_TERM.SLICE
    statement = "slice"

    # Slice has a special bracket syntax, implemented here
    def compose(self, args, optargs):
        if self.bracket_operator:
            if needs_wrap(self._args[0]):
                args[0] = T("r.expr(", args[0], ")")
            return T(args[0], "[", args[1], ":", args[2], "]")
        else:
            return RqlBracketQuery.compose(self, args, optargs)


class Skip(RqlMethodQuery):
    term_type = P_TERM.SKIP
    statement = "skip"


class Limit(RqlMethodQuery):
    term_type = P_TERM.LIMIT
    statement = "limit"


class GetField(RqlBracketQuery):
    term_type = P_TERM.GET_FIELD
    statement = "get_field"


class Bracket(RqlBracketQuery):
    term_type = P_TERM.BRACKET
    statement = "bracket"


class Contains(RqlMethodQuery):
    term_type = P_TERM.CONTAINS
    statement = "contains"


class HasFields(RqlMethodQuery):
    term_type = P_TERM.HAS_FIELDS
    statement = "has_fields"


class WithFields(RqlMethodQuery):
    term_type = P_TERM.WITH_FIELDS
    statement = "with_fields"


class Keys(RqlMethodQuery):
    term_type = P_TERM.KEYS
    statement = "keys"


class Values(RqlMethodQuery):
    term_type = P_TERM.VALUES
    statement = "values"


class Object(RqlMethodQuery):
    term_type = P_TERM.OBJECT
    statement = "object"


class Pluck(RqlMethodQuery):
    term_type = P_TERM.PLUCK
    statement = "pluck"


class Without(RqlMethodQuery):
    term_type = P_TERM.WITHOUT
    statement = "without"


class Merge(RqlMethodQuery):
    term_type = P_TERM.MERGE
    statement = "merge"


class Between(RqlMethodQuery):
    term_type = P_TERM.BETWEEN
    statement = "between"


class DB(RqlTopLevelQuery):
    term_type = P_TERM.DB
    statement = "db"

    def table_list(self, *args):
        return TableList(self, *args)

    def config(self, *args):
        return Config(self, *args)

    def wait(self, *args, **kwargs):
        return Wait(self, *args, **kwargs)

    def reconfigure(self, *args, **kwargs):
        return Reconfigure(self, *args, **kwargs)

    def rebalance(self, *args, **kwargs):
        return Rebalance(self, *args, **kwargs)

    def grant(self, *args, **kwargs):
        return Grant(self, *args, **kwargs)

    def table_create(self, *args, **kwargs):
        return TableCreate(self, *args, **kwargs)

    def table_drop(self, *args):
        return TableDrop(self, *args)

    def table(self, *args, **kwargs):
        return Table(self, *args, **kwargs)


class FunCall(RqlQuery):
    term_type = P_TERM.FUNCALL

    # This object should be constructed with arguments first, and the
    # function itself as the last parameter.  This makes it easier for
    # the places where this object is constructed.  The actual wire
    # format is function first, arguments last, so we flip them around
    # before passing it down to the base class constructor.
    def __init__(self, *args):
        if len(args) == 0:
            raise ReqlDriverCompileError("Expected 1 or more arguments but found 0.")
        args = [func_wrap(args[-1])] + list(args[:-1])
        RqlQuery.__init__(self, *args)

    def compose(self, args, optargs):
        if len(args) != 2:
            return T("r.do(", T(T(*(args[1:]), intsp=", "), args[0], intsp=", "), ")")

        if isinstance(self._args[1], Datum):
            args[1] = T("r.expr(", args[1], ")")

        return T(args[1], ".do(", args[0], ")")


class Table(RqlQuery):
    term_type = P_TERM.TABLE
    statement = "table"

    def insert(self, *args, **kwargs):
        return Insert(self, *[expr(arg) for arg in args], **kwargs)

    def get(self, *args):
        return Get(self, *args)

    def get_all(self, *args, **kwargs):
        return GetAll(self, *args, **kwargs)

    def set_write_hook(self, *args, **kwargs):
        return SetWriteHook(self, *args, **kwargs)

    def get_write_hook(self, *args, **kwargs):
        return GetWriteHook(self, *args, **kwargs)

    def index_create(self, *args, **kwargs):
        if len(args) > 1:
            args = [args[0]] + [func_wrap(arg) for arg in args[1:]]
        return IndexCreate(self, *args, **kwargs)

    def index_drop(self, *args):
        return IndexDrop(self, *args)

    def index_rename(self, *args, **kwargs):
        return IndexRename(self, *args, **kwargs)

    def index_list(self, *args):
        return IndexList(self, *args)

    def index_status(self, *args):
        return IndexStatus(self, *args)

    def index_wait(self, *args):
        return IndexWait(self, *args)

    def status(self, *args):
        return Status(self, *args)

    def config(self, *args):
        return Config(self, *args)

    def wait(self, *args, **kwargs):
        return Wait(self, *args, **kwargs)

    def reconfigure(self, *args, **kwargs):
        return Reconfigure(self, *args, **kwargs)

    def rebalance(self, *args, **kwargs):
        return Rebalance(self, *args, **kwargs)

    def sync(self, *args):
        return Sync(self, *args)

    def grant(self, *args, **kwargs):
        return Grant(self, *args, **kwargs)

    def get_intersecting(self, *args, **kwargs):
        return GetIntersecting(self, *args, **kwargs)

    def get_nearest(self, *args, **kwargs):
        return GetNearest(self, *args, **kwargs)

    def uuid(self, *args, **kwargs):
        return UUID(self, *args, **kwargs)

    def compose(self, args, optargs):
        args.extend([T(k, "=", v) for k, v in dict_items(optargs)])
        if isinstance(self._args[0], DB):
            return T(args[0], ".table(", T(*(args[1:]), intsp=", "), ")")
        else:
            return T("r.table(", T(*(args), intsp=", "), ")")


class Get(RqlMethodQuery):
    term_type = P_TERM.GET
    statement = "get"


class GetAll(RqlMethodQuery):
    term_type = P_TERM.GET_ALL
    statement = "get_all"


class GetIntersecting(RqlMethodQuery):
    term_type = P_TERM.GET_INTERSECTING
    statement = "get_intersecting"


class GetNearest(RqlMethodQuery):
    term_type = P_TERM.GET_NEAREST
    statement = "get_nearest"


class UUID(RqlMethodQuery):
    term_type = P_TERM.UUID
    statement = "uuid"


class Reduce(RqlMethodQuery):
    term_type = P_TERM.REDUCE
    statement = "reduce"


class Sum(RqlMethodQuery):
    term_type = P_TERM.SUM
    statement = "sum"


class Avg(RqlMethodQuery):
    term_type = P_TERM.AVG
    statement = "avg"


class Min(RqlMethodQuery):
    term_type = P_TERM.MIN
    statement = "min"


class Max(RqlMethodQuery):
    term_type = P_TERM.MAX
    statement = "max"


class Map(RqlMethodQuery):
    term_type = P_TERM.MAP
    statement = "map"


class Fold(RqlMethodQuery):
    term_type = P_TERM.FOLD
    statement = "fold"


class Filter(RqlMethodQuery):
    term_type = P_TERM.FILTER
    statement = "filter"


class ConcatMap(RqlMethodQuery):
    term_type = P_TERM.CONCAT_MAP
    statement = "concat_map"


class OrderBy(RqlMethodQuery):
    term_type = P_TERM.ORDER_BY
    statement = "order_by"


class Distinct(RqlMethodQuery):
    term_type = P_TERM.DISTINCT
    statement = "distinct"


class Count(RqlMethodQuery):
    term_type = P_TERM.COUNT
    statement = "count"


class Union(RqlMethodQuery):
    term_type = P_TERM.UNION
    statement = "union"


class Nth(RqlBracketQuery):
    term_type = P_TERM.NTH
    statement = "nth"


class Match(RqlMethodQuery):
    term_type = P_TERM.MATCH
    statement = "match"


class ToJsonString(RqlMethodQuery):
    term_type = P_TERM.TO_JSON_STRING
    statement = "to_json_string"


class Split(RqlMethodQuery):
    term_type = P_TERM.SPLIT
    statement = "split"


class Upcase(RqlMethodQuery):
    term_type = P_TERM.UPCASE
    statement = "upcase"


class Downcase(RqlMethodQuery):
    term_type = P_TERM.DOWNCASE
    statement = "downcase"


class OffsetsOf(RqlMethodQuery):
    term_type = P_TERM.OFFSETS_OF
    statement = "offsets_of"


class IsEmpty(RqlMethodQuery):
    term_type = P_TERM.IS_EMPTY
    statement = "is_empty"


class Group(RqlMethodQuery):
    term_type = P_TERM.GROUP
    statement = "group"


class InnerJoin(RqlMethodQuery):
    term_type = P_TERM.INNER_JOIN
    statement = "inner_join"


class OuterJoin(RqlMethodQuery):
    term_type = P_TERM.OUTER_JOIN
    statement = "outer_join"


class EqJoin(RqlMethodQuery):
    term_type = P_TERM.EQ_JOIN
    statement = "eq_join"


class Zip(RqlMethodQuery):
    term_type = P_TERM.ZIP
    statement = "zip"


class CoerceTo(RqlMethodQuery):
    term_type = P_TERM.COERCE_TO
    statement = "coerce_to"


class Ungroup(RqlMethodQuery):
    term_type = P_TERM.UNGROUP
    statement = "ungroup"


class TypeOf(RqlMethodQuery):
    term_type = P_TERM.TYPE_OF
    statement = "type_of"


class Update(RqlMethodQuery):
    term_type = P_TERM.UPDATE
    statement = "update"


class Delete(RqlMethodQuery):
    term_type = P_TERM.DELETE
    statement = "delete"


class Replace(RqlMethodQuery):
    term_type = P_TERM.REPLACE
    statement = "replace"


class Insert(RqlMethodQuery):
    term_type = P_TERM.INSERT
    statement = "insert"


class DbCreate(RqlTopLevelQuery):
    term_type = P_TERM.DB_CREATE
    statement = "db_create"


class DbDrop(RqlTopLevelQuery):
    term_type = P_TERM.DB_DROP
    statement = "db_drop"


class DbList(RqlTopLevelQuery):
    term_type = P_TERM.DB_LIST
    statement = "db_list"


class TableCreate(RqlMethodQuery):
    term_type = P_TERM.TABLE_CREATE
    statement = "table_create"


class TableCreateTL(RqlTopLevelQuery):
    term_type = P_TERM.TABLE_CREATE
    statement = "table_create"


class TableDrop(RqlMethodQuery):
    term_type = P_TERM.TABLE_DROP
    statement = "table_drop"


class TableDropTL(RqlTopLevelQuery):
    term_type = P_TERM.TABLE_DROP
    statement = "table_drop"


class TableList(RqlMethodQuery):
    term_type = P_TERM.TABLE_LIST
    statement = "table_list"


class TableListTL(RqlTopLevelQuery):
    term_type = P_TERM.TABLE_LIST
    statement = "table_list"


class SetWriteHook(RqlMethodQuery):
    term_type = P_TERM.SET_WRITE_HOOK
    statement = "set_write_hook"


class GetWriteHook(RqlMethodQuery):
    term_type = P_TERM.GET_WRITE_HOOK
    statement = "get_write_hook"


class IndexCreate(RqlMethodQuery):
    term_type = P_TERM.INDEX_CREATE
    statement = "index_create"


class IndexDrop(RqlMethodQuery):
    term_type = P_TERM.INDEX_DROP
    statement = "index_drop"


class IndexRename(RqlMethodQuery):
    term_type = P_TERM.INDEX_RENAME
    statement = "index_rename"


class IndexList(RqlMethodQuery):
    term_type = P_TERM.INDEX_LIST
    statement = "index_list"


class IndexStatus(RqlMethodQuery):
    term_type = P_TERM.INDEX_STATUS
    statement = "index_status"


class IndexWait(RqlMethodQuery):
    term_type = P_TERM.INDEX_WAIT
    statement = "index_wait"


class Config(RqlMethodQuery):
    term_type = P_TERM.CONFIG
    statement = "config"


class Status(RqlMethodQuery):
    term_type = P_TERM.STATUS
    statement = "status"


class Wait(RqlMethodQuery):
    term_type = P_TERM.WAIT
    statement = "wait"


class Reconfigure(RqlMethodQuery):
    term_type = P_TERM.RECONFIGURE
    statement = "reconfigure"


class Rebalance(RqlMethodQuery):
    term_type = P_TERM.REBALANCE
    statement = "rebalance"


class Sync(RqlMethodQuery):
    term_type = P_TERM.SYNC
    statement = "sync"


class Grant(RqlMethodQuery):
    term_type = P_TERM.GRANT
    statement = "grant"


class GrantTL(RqlTopLevelQuery):
    term_type = P_TERM.GRANT
    statement = "grant"


class Branch(RqlTopLevelQuery):
    term_type = P_TERM.BRANCH
    statement = "branch"


class Or(RqlBoolOperQuery):
    term_type = P_TERM.OR
    statement = "or_"
    st_infix = "|"


class And(RqlBoolOperQuery):
    term_type = P_TERM.AND
    statement = "and_"
    st_infix = "&"


class ForEach(RqlMethodQuery):
    term_type = P_TERM.FOR_EACH
    statement = "for_each"


class Info(RqlMethodQuery):
    term_type = P_TERM.INFO
    statement = "info"


class InsertAt(RqlMethodQuery):
    term_type = P_TERM.INSERT_AT
    statement = "insert_at"


class SpliceAt(RqlMethodQuery):
    term_type = P_TERM.SPLICE_AT
    statement = "splice_at"


class DeleteAt(RqlMethodQuery):
    term_type = P_TERM.DELETE_AT
    statement = "delete_at"


class ChangeAt(RqlMethodQuery):
    term_type = P_TERM.CHANGE_AT
    statement = "change_at"


class Sample(RqlMethodQuery):
    term_type = P_TERM.SAMPLE
    statement = "sample"


class Json(RqlTopLevelQuery):
    term_type = P_TERM.JSON
    statement = "json"


class Args(RqlTopLevelQuery):
    term_type = P_TERM.ARGS
    statement = "args"


# Use this class as a wrapper to 'bytes' so we can tell the difference
# in Python2 (when reusing the result of a previous query).
class RqlBinary(bytes):
    def __new__(cls, *args, **kwargs):
        return bytes.__new__(cls, *args, **kwargs)

    def __repr__(self):
        excerpt = binascii.hexlify(self[0:6]).decode("utf-8")
        excerpt = " ".join([excerpt[i : i + 2] for i in xrange(0, len(excerpt), 2)])
        excerpt = (
            ", '%s%s'" % (excerpt, "..." if len(self) > 6 else "")
            if len(self) > 0
            else ""
        )
        return "<binary, %d byte%s%s>" % (
            len(self),
            "s" if len(self) != 1 else "",
            excerpt,
        )


class Binary(RqlTopLevelQuery):
    # Note: this term isn't actually serialized, it should exist only
    # in the client
    term_type = P_TERM.BINARY
    statement = "binary"

    def __init__(self, data):
        # We only allow 'bytes' objects to be serialized as binary
        # Python 2 - `bytes` is equivalent to `str`, either will be accepted
        # Python 3 - `unicode` is equivalent to `str`, neither will be accepted
        if isinstance(data, RqlQuery):
            RqlTopLevelQuery.__init__(self, data)
        elif isinstance(data, unicode):
            raise ReqlDriverCompileError(
                "Cannot convert a unicode string to binary, "
                "use `unicode.encode()` to specify the "
                "encoding."
            )
        elif not isinstance(data, bytes):
            raise ReqlDriverCompileError(
                (
                    "Cannot convert %s to binary, convert the "
                    "object to a `bytes` object first."
                )
                % type(data).__name__
            )
        else:
            self.base64_data = base64.b64encode(data)

            # Kind of a hack to get around composing
            self._args = []
            self.optargs = {}

    def compose(self, args, optargs):
        if len(self._args) == 0:
            return T("r.", self.statement, "(bytes(<data>))")
        else:
            return RqlTopLevelQuery.compose(self, args, optargs)

    def build(self):
        if len(self._args) == 0:
            return {"$reql_type$": "BINARY", "data": self.base64_data.decode("utf-8")}
        else:
            return RqlTopLevelQuery.build(self)


class Range(RqlTopLevelQuery):
    term_type = P_TERM.RANGE
    statement = "range"


class ToISO8601(RqlMethodQuery):
    term_type = P_TERM.TO_ISO8601
    statement = "to_iso8601"


class During(RqlMethodQuery):
    term_type = P_TERM.DURING
    statement = "during"


class Date(RqlMethodQuery):
    term_type = P_TERM.DATE
    statement = "date"


class TimeOfDay(RqlMethodQuery):
    term_type = P_TERM.TIME_OF_DAY
    statement = "time_of_day"


class Timezone(RqlMethodQuery):
    term_type = P_TERM.TIMEZONE
    statement = "timezone"


class Year(RqlMethodQuery):
    term_type = P_TERM.YEAR
    statement = "year"


class Month(RqlMethodQuery):
    term_type = P_TERM.MONTH
    statement = "month"


class Day(RqlMethodQuery):
    term_type = P_TERM.DAY
    statement = "day"


class DayOfWeek(RqlMethodQuery):
    term_type = P_TERM.DAY_OF_WEEK
    statement = "day_of_week"


class DayOfYear(RqlMethodQuery):
    term_type = P_TERM.DAY_OF_YEAR
    statement = "day_of_year"


class Hours(RqlMethodQuery):
    term_type = P_TERM.HOURS
    statement = "hours"


class Minutes(RqlMethodQuery):
    term_type = P_TERM.MINUTES
    statement = "minutes"


class Seconds(RqlMethodQuery):
    term_type = P_TERM.SECONDS
    statement = "seconds"


class Time(RqlTopLevelQuery):
    term_type = P_TERM.TIME
    statement = "time"


class ISO8601(RqlTopLevelQuery):
    term_type = P_TERM.ISO8601
    statement = "iso8601"


class EpochTime(RqlTopLevelQuery):
    term_type = P_TERM.EPOCH_TIME
    statement = "epoch_time"


class Now(RqlTopLevelQuery):
    term_type = P_TERM.NOW
    statement = "now"


class InTimezone(RqlMethodQuery):
    term_type = P_TERM.IN_TIMEZONE
    statement = "in_timezone"


class ToEpochTime(RqlMethodQuery):
    term_type = P_TERM.TO_EPOCH_TIME
    statement = "to_epoch_time"


class GeoJson(RqlTopLevelQuery):
    term_type = P_TERM.GEOJSON
    statement = "geojson"


class ToGeoJson(RqlMethodQuery):
    term_type = P_TERM.TO_GEOJSON
    statement = "to_geojson"


class Point(RqlTopLevelQuery):
    term_type = P_TERM.POINT
    statement = "point"


class Line(RqlTopLevelQuery):
    term_type = P_TERM.LINE
    statement = "line"


class Polygon(RqlTopLevelQuery):
    term_type = P_TERM.POLYGON
    statement = "polygon"


class Distance(RqlMethodQuery):
    term_type = P_TERM.DISTANCE
    statement = "distance"


class Intersects(RqlMethodQuery):
    term_type = P_TERM.INTERSECTS
    statement = "intersects"


class Includes(RqlMethodQuery):
    term_type = P_TERM.INCLUDES
    statement = "includes"


class Circle(RqlTopLevelQuery):
    term_type = P_TERM.CIRCLE
    statement = "circle"


class Fill(RqlMethodQuery):
    term_type = P_TERM.FILL
    statement = "fill"


class PolygonSub(RqlMethodQuery):
    term_type = P_TERM.POLYGON_SUB
    statement = "polygon_sub"


# Returns True if IMPLICIT_VAR is found in the subquery
def _ivar_scan(query):
    if not isinstance(query, RqlQuery):
        return False
    if isinstance(query, ImplicitVar):
        return True
    if any([_ivar_scan(arg) for arg in query._args]):
        return True
    if any([_ivar_scan(arg) for k, arg in dict_items(query.optargs)]):
        return True
    return False


# Called on arguments that should be functions
def func_wrap(val):
    val = expr(val)
    if _ivar_scan(val):
        return Func(lambda x: val)
    return val


class Func(RqlQuery):
    term_type = P_TERM.FUNC
    lock = threading.Lock()
    nextVarId = 1

    def __init__(self, lmbd):
        super(Func, self).__init__()
        vrs = []
        vrids = []
        try:
            code = lmbd.func_code
        except AttributeError:
            code = lmbd.__code__
        for i in xrange(code.co_argcount):
            Func.lock.acquire()
            var_id = Func.nextVarId
            Func.nextVarId += 1
            Func.lock.release()
            vrs.append(Var(var_id))
            vrids.append(var_id)

        self.vrs = vrs
        self._args.extend([MakeArray(*vrids), expr(lmbd(*vrs))])

    def compose(self, args, optargs):
        return T(
            "lambda ",
            T(
                *[v.compose([v._args[0].compose(None, None)], []) for v in self.vrs],
                intsp=", "
            ),
            ": ",
            args[1],
        )


class Asc(RqlTopLevelQuery):
    term_type = P_TERM.ASC
    statement = "asc"


class Desc(RqlTopLevelQuery):
    term_type = P_TERM.DESC
    statement = "desc"


class Literal(RqlTopLevelQuery):
    term_type = P_TERM.LITERAL
    statement = "literal"
