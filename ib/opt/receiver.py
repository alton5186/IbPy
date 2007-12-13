#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# Defines Receiver class to handle inbound data.
#
# The Receiver class is built programatically.  Message types are
# defined in the ib.opt.message module, and those types are used to
# construct methods on the Receiver class during its definition.
# Refer to the ReceiverType metaclass for details.
##
import sys
import traceback

from ib.lib.overloading import overloaded
from ib.opt.message import registry, wrapperMethods

# micro optimizations
from __builtin__ import KeyError, dict


def messageMethod(name, argnames):
    """ Creates method for dispatching messages.

    @param name name of method as string
    @param argnames list of method argument names
    @return newly created method (as closure)
    """
    def inner(self, *args):
        params = dict(zip(argnames, args))
        self.dispatch(name, params)
    inner.__name__ = name
    return inner


class ReceiverType(type):
    """ Metaclass to add EWrapper methods to Receiver class.

    """
    def __new__(cls, name, bases, namespace):
        """ Creates a new type.

        @param name name of new type as string
        @param bases tuple of base classes
        @param namespace dictionary with namespace for new type
        @return generated type
        """
        for mname, margs in wrapperMethods():
            namespace[mname] = messageMethod(mname, margs)
        return type(name, bases, namespace)


class Receiver(object):
    """ Receiver -> dispatches messages to interested callables

    Instances implement the EWrapper interface but do not subclass it.
    """
    __metaclass__ = ReceiverType


    def __init__(self, listeners=None, types=None):
        """ Constructor.

        @param listeners=None mapping of existing listeners
        @param types=None method name to message type lookup
        """
        self.listeners = listeners if listeners else {}
        self.types = types if types else registry

    def dispatch(self, name, mapping):
        """ Send message to each listener.

        @param name method name
        @param mapping values for message instance
        @return None
        """
        try:
            mtype = self.types[name]
            listeners = self.listeners[self.key(mtype)]
        except (KeyError, ):
            pass
        else:
            message = mtype(**mapping)
            for listener in listeners:
                try:
                    listener(message)
                except (Exception, ):
                    self.unregister(listener, mtype)
                    excinfo = sys.exc_info()
                    stdout = sys.stdout
                    line = '-' * 76
                    errmsg = ('Exception in IbPy message dispatch.\n'
                              'Handler %s unregistered for %s.' % (listener, name))
                    print >> stdout, line
                    print >> stdout, errmsg
                    print >> stdout, line
                    traceback.print_tb(excinfo[2])
                    print >> stdout

    def register(self, listener, *types):
        """ Associate listener with message types created by this Receiver.

        @param listener callable to receive messages
        @param *types zero or more message types to associate with listener
        @return None
        """
        for mtype in types:
            key = self.key(mtype)
            listeners = self.listeners.setdefault(key, [])
            if listener not in listeners:
                listeners.append(listener)


    def registerAll(self, listener):
        """ Associate listener with all messages created by this Receiver.

        @param listener callable to receive messages
        @return None
        """
        self.register(listener, *self.types.values())

    def unregister(self, listener, *types):
        """ Disassociate listener with message types created by this Receiver.

        @param listener callable to no longer receive messages
        @param *types zero or more message types to disassociate with listener
        @return None
        """
        for mtype in types:
            try:
                listeners = self.listeners[self.key(mtype)]
            except (KeyError, ):
                pass
            else:
                if listener in listeners:
                    listeners.remove(listener)

    def unregisterAll(self, listener):
        """ Disassociate listener with all messages created by this Receiver.

        @param listener callable to no longer receive messages
        @return None
        """
        self.unregister(listener, *self.types.values())

    @staticmethod
    def key(obj):
        """ Generates lookup key for given object.

        @param obj any object
        @return obj name or string representation
        """
        try:
            return obj.__name__
        except (AttributeError, ):
            return str(obj)

    @overloaded
    def error(self, e):
        """ Dispatch an error generated by the reader.

        Error message types can't be associated in the default manner
        with this family of methods, so we define these three here
        by hand.

        @param e some error value
        @return None
        """
        self.dispatch('error', dict(errorMsg=e))

    @error.register(object, str)
    def error_0(self, strval):
        """ Dispatch an error given a string value.

        @param strval some error value as string
        @return None
        """
        self.dispatch('error', dict(errorMsg=strval))

    @error.register(object, int, int, str)
    def error_1(self, id, errorCode, errorMsg):
        """ Dispatch an error given an id, code and message.

        @param id error id
        @param errorCode error code
        @param errorMsg error message
        @return None
        """
        params = dict(id=id, errorCode=errorCode, errorMsg=errorMsg)
        self.dispatch('error', params)
