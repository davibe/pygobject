# -*- Mode: Python; py-indent-offset: 4 -*-
# pygobject - Python bindings for the GObject library
# Copyright (C) 2007 Johan Dahlin
#
#   gi/_propertyhelper.py: GObject property wrapper/helper
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301
# USA

import sys

import gi._gi
_gobject = gi._gi._gobject

from ._constants import \
    TYPE_NONE, TYPE_INTERFACE, TYPE_CHAR, TYPE_UCHAR, \
    TYPE_BOOLEAN, TYPE_INT, TYPE_UINT, TYPE_LONG, \
    TYPE_ULONG, TYPE_INT64, TYPE_UINT64, TYPE_ENUM, TYPE_FLAGS, \
    TYPE_FLOAT, TYPE_DOUBLE, TYPE_STRING, \
    TYPE_POINTER, TYPE_BOXED, TYPE_PARAM, TYPE_OBJECT, \
    TYPE_PYOBJECT, TYPE_GTYPE, TYPE_STRV, TYPE_VARIANT

G_MAXFLOAT = _gobject.G_MAXFLOAT
G_MAXDOUBLE = _gobject.G_MAXDOUBLE
G_MININT = _gobject.G_MININT
G_MAXINT = _gobject.G_MAXINT
G_MAXUINT = _gobject.G_MAXUINT
G_MINLONG = _gobject.G_MINLONG
G_MAXLONG = _gobject.G_MAXLONG
G_MAXULONG = _gobject.G_MAXULONG

if sys.version_info >= (3, 0):
    _basestring = str
    _long = int
else:
    _basestring = basestring
    _long = long


class Property(object):
    """
    Creates a new property which in conjunction with GObject subclass will
    create a property proxy:

         class MyObject(GObject.GObject):
         ... prop = GObject.Property(type=str)

         obj = MyObject()
         obj.prop = 'value'

         obj.prop  # now is 'value'

    The API is similar to the builtin property:

    class AnotherObject(GObject.GObject):
        @GObject.Property
        def prop(self):
            '''Read only property.'''
            return ...

        @GObject.Property(type=int)
        def propInt(self):
            '''Read-write integer property.'''
            return ...

        @propInt.setter
        def propInt(self, value):
            ...
    """
    _type_from_pytype_lookup = {
        # Put long_ first in case long_ and int are the same so int clobbers long_
        _long: TYPE_LONG,
        int: TYPE_INT,
        bool: TYPE_BOOLEAN,
        float: TYPE_DOUBLE,
        str: TYPE_STRING,
        object: TYPE_PYOBJECT,
    }

    _min_value_lookup = {
        TYPE_UINT: 0,
        TYPE_ULONG: 0,
        TYPE_UINT64: 0,
        # Remember that G_MINFLOAT and G_MINDOUBLE are something different.
        TYPE_FLOAT: -G_MAXFLOAT,
        TYPE_DOUBLE: -G_MAXDOUBLE,
        TYPE_INT: G_MININT,
        TYPE_LONG: G_MINLONG,
        TYPE_INT64: -2 ** 63,
    }

    _max_value_lookup = {
        TYPE_UINT: G_MAXUINT,
        TYPE_ULONG: G_MAXULONG,
        TYPE_INT64: 2 ** 63 - 1,
        TYPE_UINT64: 2 ** 64 - 1,
        TYPE_FLOAT: G_MAXFLOAT,
        TYPE_DOUBLE: G_MAXDOUBLE,
        TYPE_INT: G_MAXINT,
        TYPE_LONG: G_MAXLONG,
    }

    _default_lookup = {
        TYPE_INT: 0,
        TYPE_UINT: 0,
        TYPE_LONG: 0,
        TYPE_ULONG: 0,
        TYPE_INT64: 0,
        TYPE_UINT64: 0,
        TYPE_STRING: '',
        TYPE_FLOAT: 0.0,
        TYPE_DOUBLE: 0.0,
    }

    class __metaclass__(type):
        def __repr__(self):
            return "<class 'GObject.Property'>"

    def __init__(self, getter=None, setter=None, type=None, default=None,
                 nick='', blurb='', flags=_gobject.PARAM_READWRITE,
                 minimum=None, maximum=None):
        """
        @param  getter: getter to get the value of the property
        @type   getter: callable
        @param  setter: setter to set the value of the property
        @type   setter: callable
        @param    type: type of property
        @type     type: type
        @param default: default value
        @param    nick: short description
        @type     nick: string
        @param   blurb: long description
        @type    blurb: string
        @param flags:    parameter flags, one of:
        - gobject.PARAM_READABLE
        - gobject.PARAM_READWRITE
        - gobject.PARAM_WRITABLE
        - gobject.PARAM_CONSTRUCT
        - gobject.PARAM_CONSTRUCT_ONLY
        - gobject.PARAM_LAX_VALIDATION
        @keyword minimum:  minimum allowed value (int, float, long only)
        @keyword maximum:  maximum allowed value (int, float, long only)
        """

        self.name = None

        if type is None:
            type = object
        self.type = self._type_from_python(type)
        self.default = self._get_default(default)
        self._check_default()

        if not isinstance(nick, _basestring):
            raise TypeError("nick must be a string")
        self.nick = nick

        if not isinstance(blurb, _basestring):
            raise TypeError("blurb must be a string")
        self.blurb = blurb
        # Always clobber __doc__ with blurb even if blurb is empty because
        # we don't want the lengthy Property class documentation showing up
        # on instances.
        self.__doc__ = blurb
        self.flags = flags

        # Call after setting blurb for potential __doc__ usage.
        if getter and not setter:
            setter = self._readonly_setter
        elif setter and not getter:
            getter = self._writeonly_getter
        elif not setter and not getter:
            getter = self._default_getter
            setter = self._default_setter
        self.getter(getter)
        # do not call self.setter() here, as this defines the property name
        # already
        self.fset = setter

        if minimum is not None:
            if minimum < self._get_minimum():
                raise TypeError(
                    "Minimum for type %s cannot be lower than %d" %
                    (self.type, self._get_minimum()))
        else:
            minimum = self._get_minimum()
        self.minimum = minimum
        if maximum is not None:
            if maximum > self._get_maximum():
                raise TypeError(
                    "Maximum for type %s cannot be higher than %d" %
                    (self.type, self._get_maximum()))
        else:
            maximum = self._get_maximum()
        self.maximum = maximum

        self._exc = None

    def __repr__(self):
        return '<GObject Property %s (%s)>' % (
            self.name or '(uninitialized)',
            _gobject.type_name(self.type))

    def __get__(self, instance, klass):
        if instance is None:
            return self

        self._exc = None
        value = instance.get_property(self.name)
        if self._exc:
            exc = self._exc
            self._exc = None
            raise exc

        return value

    def __set__(self, instance, value):
        if instance is None:
            raise TypeError

        self._exc = None
        instance.set_property(self.name, value)
        if self._exc:
            exc = self._exc
            self._exc = None
            raise exc

    def __call__(self, fget):
        """Allows application of the getter along with init arguments."""
        return self.getter(fget)

    def getter(self, fget):
        """Set the getter function to fget. For use as a decorator."""
        if fget.__doc__:
            # Always clobber docstring and blurb with the getter docstring.
            self.blurb = fget.__doc__
            self.__doc__ = fget.__doc__
        self.fget = fget
        return self

    def setter(self, fset):
        """Set the setter function to fset. For use as a decorator."""
        self.fset = fset
        # with a setter decorator, we must ignore the name of the method in
        # install_properties, as this does not need to be a valid property name
        # and does not define the property name. So set the name here.
        if not self.name:
            self.name = self.fget.__name__
        return self

    def _type_from_python(self, type_):
        if type_ in self._type_from_pytype_lookup:
            return self._type_from_pytype_lookup[type_]
        elif (isinstance(type_, type) and
              issubclass(type_, (_gobject.GObject,
                                 _gobject.GEnum,
                                 _gobject.GFlags,
                                 _gobject.GBoxed,
                                 _gobject.GInterface))):
            return type_.__gtype__
        elif type_ in (TYPE_NONE, TYPE_INTERFACE, TYPE_CHAR, TYPE_UCHAR,
                       TYPE_INT, TYPE_UINT, TYPE_BOOLEAN, TYPE_LONG,
                       TYPE_ULONG, TYPE_INT64, TYPE_UINT64,
                       TYPE_FLOAT, TYPE_DOUBLE, TYPE_POINTER,
                       TYPE_BOXED, TYPE_PARAM, TYPE_OBJECT, TYPE_STRING,
                       TYPE_PYOBJECT, TYPE_GTYPE, TYPE_STRV, TYPE_VARIANT):
            return type_
        else:
            raise TypeError("Unsupported type: %r" % (type_,))

    def _get_default(self, default):
        if default is not None:
            return default
        return self._default_lookup.get(self.type, None)

    def _check_default(self):
        ptype = self.type
        default = self.default
        if (ptype == TYPE_BOOLEAN and (default not in (True, False))):
            raise TypeError(
                "default must be True or False, not %r" % (default,))
        elif ptype == TYPE_PYOBJECT:
            if default is not None:
                raise TypeError("object types does not have default values")
        elif ptype == TYPE_GTYPE:
            if default is not None:
                raise TypeError("GType types does not have default values")
        elif _gobject.type_is_a(ptype, TYPE_ENUM):
            if default is None:
                raise TypeError("enum properties needs a default value")
            elif not _gobject.type_is_a(default, ptype):
                raise TypeError("enum value %s must be an instance of %r" %
                                (default, ptype))
        elif _gobject.type_is_a(ptype, TYPE_FLAGS):
            if not _gobject.type_is_a(default, ptype):
                raise TypeError("flags value %s must be an instance of %r" %
                                (default, ptype))
        elif _gobject.type_is_a(ptype, TYPE_STRV) and default is not None:
            if not isinstance(default, list):
                raise TypeError("Strv value %s must be a list" % repr(default))
            for val in default:
                if type(val) not in (str, bytes):
                    raise TypeError("Strv value %s must contain only strings" % str(default))
        elif _gobject.type_is_a(ptype, TYPE_VARIANT) and default is not None:
            if not hasattr(default, '__gtype__') or not _gobject.type_is_a(default, TYPE_VARIANT):
                raise TypeError("variant value %s must be an instance of %r" %
                                (default, ptype))

    def _get_minimum(self):
        return self._min_value_lookup.get(self.type, None)

    def _get_maximum(self):
        return self._max_value_lookup.get(self.type, None)

    #
    # Getter and Setter
    #

    def _default_setter(self, instance, value):
        setattr(instance, '_property_helper_' + self.name, value)

    def _default_getter(self, instance):
        return getattr(instance, '_property_helper_' + self.name, self.default)

    def _readonly_setter(self, instance, value):
        self._exc = TypeError("%s property of %s is read-only" % (
            self.name, type(instance).__name__))

    def _writeonly_getter(self, instance):
        self._exc = TypeError("%s property of %s is write-only" % (
            self.name, type(instance).__name__))

    #
    # Public API
    #

    def get_pspec_args(self):
        ptype = self.type
        if ptype in (TYPE_INT, TYPE_UINT, TYPE_LONG, TYPE_ULONG,
                     TYPE_INT64, TYPE_UINT64, TYPE_FLOAT, TYPE_DOUBLE):
            args = self.minimum, self.maximum, self.default
        elif (ptype == TYPE_STRING or ptype == TYPE_BOOLEAN or
              ptype.is_a(TYPE_ENUM) or ptype.is_a(TYPE_FLAGS) or
              ptype.is_a(TYPE_VARIANT)):
            args = (self.default,)
        elif ptype in (TYPE_PYOBJECT, TYPE_GTYPE):
            args = ()
        elif ptype.is_a(TYPE_OBJECT) or ptype.is_a(TYPE_BOXED):
            args = ()
        else:
            raise NotImplementedError(ptype)

        return (self.type, self.nick, self.blurb) + args + (self.flags,)


def install_properties(cls):
    """
    Scans the given class for instances of Property and merges them
    into the classes __gproperties__ dict if it exists or adds it if not.
    """
    gproperties = cls.__dict__.get('__gproperties__', {})

    props = []
    for name, prop in cls.__dict__.items():
        if isinstance(prop, Property):  # not same as the built-in
            # if a property was defined with a decorator, it may already have
            # a name; if it was defined with an assignment (prop = Property(...))
            # we set the property's name to the member name
            if not prop.name:
                prop.name = name
            # we will encounter the same property multiple times in case of
            # custom setter methods
            if prop.name in gproperties:
                if gproperties[prop.name] == prop.get_pspec_args():
                    continue
                raise ValueError('Property %s was already found in __gproperties__' % prop.name)
            gproperties[prop.name] = prop.get_pspec_args()
            props.append(prop)

    if not props:
        return

    cls.__gproperties__ = gproperties

    if 'do_get_property' in cls.__dict__ or 'do_set_property' in cls.__dict__:
        for prop in props:
            if prop.fget != prop._default_getter or prop.fset != prop._default_setter:
                raise TypeError(
                    "GObject subclass %r defines do_get/set_property"
                    " and it also uses a property with a custom setter"
                    " or getter. This is not allowed" %
                    (cls.__name__,))

    def obj_get_property(self, pspec):
        name = pspec.name.replace('-', '_')
        prop = getattr(cls, name, None)
        if prop:
            return prop.fget(self)
    cls.do_get_property = obj_get_property

    def obj_set_property(self, pspec, value):
        name = pspec.name.replace('-', '_')
        prop = getattr(cls, name, None)
        if prop:
            prop.fset(self, value)
    cls.do_set_property = obj_set_property
