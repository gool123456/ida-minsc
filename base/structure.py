import sys,logging
import functools,itertools,operator
import six,types,re,fnmatch

import database,ui,internal
from internal import utils,interface

import idaapi
'''
structure-context

generic tools for working in the context of a structure.
'''

## FIXME: need to add support for a union_t. add_struc takes another parameter
##        that defines whether a structure is a union or not.

# FIXME: Deprcate this __structure_t, and move all multicase functions that use it
#        so that they're defined after the definition of the structure_t.
class __structure_t(object): pass

@utils.multicase()
def name(id):
    '''Return the name of the structure identified by ``id``.'''
    return idaapi.get_struc_name(id)
@utils.multicase(struc=__structure_t)
def name(struc): return name(struc.id)
@utils.multicase(name=basestring)
def name(id, name):
    '''Set the name of the structure identified by ``id`` to ``name``.'''
    return idaapi.set_struc_name(id, name)
@utils.multicase(struc=__structure_t, name=basestring)
def name(struc, name): return name(struc.id, name)

@utils.multicase(id=six.integer_types)
def comment(id, **repeatable):
    """Return the comment for the structure identified by ``id``.
    If the bool ``repeatable`` is specified, return the repeatable comment.
    """
    return idaapi.get_struc_cmt(id, repeatable.get('repeatable',True))
@utils.multicase(struc=__structure_t)
def comment(struc, **repeatable):
    '''Return the comment for the structure ``struc``.'''
    return comment(struc.id, **repeatable)
@utils.multicase(cmt=basestring)
def comment(id=six.integer_types, cmt=basestring, **repeatable):
    """Set the comment for the structure identified by ``id`` to ``cmt``.
    If the bool ``repeatable`` is specified, set the repeatable comment.
    """
    return idaapi.set_struc_cmt(id, cmt, repeatable.get('repeatable',True))
@utils.multicase(struc=__structure_t, cmt=basestring)
def comment(struc, cmt, **repeatable):
    '''Set the comment for the structure ``struc``.'''
    return comment(struc.id, cmt, **repeatable)

@utils.multicase(id=six.integer_types)
def index(id):
    '''Return the index for the structure identified by ``id``.'''
    return idaapi.get_struc_idx(id)
@utils.multicase(struc=__structure_t)
def index(struc):
    '''Return the index for the structure ``struc``.'''
    return index(struc.id)
@utils.multicase(id=six.integer_types, index=six.integer_types)
def index(id, index):
    '''Move the structure identified by ``id`` to the index ``index``.'''
    return idaapi.set_struc_idx(id, index)
@utils.multicase(struc=__structure_t, index=six.integer_types)
def index(struc, index):
    '''Move the structure ``struc`` to the index ``index``.'''
    return index(struc.id, index)

__matcher__ = internal.interface.matcher()
__matcher__.boolean('regex', re.search, 'name')
__matcher__.mapping('index', idaapi.get_struc_idx, 'id')
__matcher__.attribute('identifier', 'id')
__matcher__.attribute('id', 'id')
__matcher__.boolean('like', lambda v, n: fnmatch.fnmatch(n, v), 'name')
__matcher__.boolean('name', operator.eq, 'name')
__matcher__.predicate('predicate')
__matcher__.predicate('pred')

@utils.multicase(string=basestring)
def list(string):
    '''List any structures that match the glob in `string`.'''
    return list(like=string)
@utils.multicase()
def list(**type):
    """List all the structures within the database.

    Search type can be identified by providing a named argument.
    like = glob match
    regex = regular expression
    index = particular index
    identifier = particular id number
    pred = function predicate
    """

    if type:
        for k,v in type.iteritems():
            for st in map(None, __matcher__.match(k, v, iterate())):
                print('[{:d}] {:s} +0x{:x} ({:d} members){:s}'.format(idaapi.get_struc_idx(st.id), st.name, st.size, len(st.members), ' // {:s}'.format(st.comment) if st.comment else ''))
            continue
    else:
        for st in iterate():
            print('[{:d}] {:s} +0x{:x} ({:d} members){:s}'.format(idaapi.get_struc_idx(st.id), st.name, st.size, len(st.members), ' // {:s}'.format(st.comment) if st.comment else ''))
    return

@utils.multicase(string=basestring)
def search(string):
    '''Search through all the structures using globbing.'''
    return search(like=string)
@utils.multicase()
def search(**type):
    """Search through all the structures within the database and return the first result.

    like = glob match
    regex = regular expression
    index = particular index
    identifier or id = internal id number
    """

    searchstring = ', '.join('{:s}={!r}'.format(k,v) for k,v in type.iteritems())
    if len(type) != 1:
        raise LookupError('{:s}.search({:s}) : More than one search type specified.', __name__, searchstring)

    k,v = next(type.iteritems())
    res = map(None,__matcher__.match(k, v, iterate()))
    if len(res) > 1:
        map(logging.info, (('[{:d}] {:s}'.format(idaapi.get_struc_idx(st.id), st.name)) for i,st in enumerate(res)))
        logging.warn('{:s}.search({:s}) : Found {:d} matching results, returning the first one.'.format(__name__, searchstring, len(res)))

    res = next(iter(res), None)
    if res is None:
        raise LookupError('{:s}.search({:s}) : Found 0 matching results.'.format(__name__, searchstring))
    return res

def iterate():
    '''Iterate through all structures defined in the database.'''
    idx = idaapi.get_first_struc_idx()
    while idx != idaapi.get_last_struc_idx():
        identifier = idaapi.get_struc_by_idx(idx)
        yield instance(identifier)
        idx = idaapi.get_next_struc_idx(idx)
    idx = idaapi.get_last_struc_idx()
    yield instance(idaapi.get_struc_by_idx(idx))

@utils.multicase(struc=__structure_t)
def size(struc):
    '''Return the size of the structure ``struc``.'''
    return size(struc.id)
@utils.multicase(id=six.integer_types)
def size(id):
    """Return the size of the structure identified by ``id``."""
    return idaapi.get_struc_size(id)

@utils.multicase(struc=__structure_t)
def members(struc):
    '''Yields the members of the structure ``struc``.'''
    return members(struc.id)
@utils.multicase(id=six.integer_types)
def members(id):
    """Yields the members of the structure identified by ``id``.
    Each iteration yields the ((offset,size),(name,comment)) of each member.
    """

    st = idaapi.get_struc(id)
    if not st:
        # empty structure
        return

    size = idaapi.get_struc_size(st)

    offset = 0
    for i in range(st.memqty):
        m = st.get_member(i)
        ms = idaapi.get_member_size(m)

        left,right = m.soff,m.eoff

        if offset < left:
            yield (offset,left-offset), (None,None)
            offset = left

        yield (offset,ms),(idaapi.get_member_name(m.id), idaapi.get_member_cmt(m.id, 1))
        offset += ms
    return

@utils.multicase(struc=__structure_t, offset=six.integer_types, size=six.integer_types)
def fragment(struc, offset, size):
    '''Yields the members within the structure ``struc``.'''
    return fragment(struc.id, offset, size)
@utils.multicase(id=six.integer_types, offset=six.integer_types, size=six.integer_types)
def fragment(id, offset, size):
    """Yields the members of the structure identified by ``id`` from ``offset`` up to the ``size``.
    Each iteration yields ((offset,size),(name,comment)) for each member within the specified bounds.
    """
    member = members(id)

    # seek
    while True:
        (m_offset,m_size),(m_name,m_cmt) = member.next()

        left,right = m_offset, m_offset+m_size
        if (offset >= left) and (offset < right):
            yield (m_offset,m_size),(m_name,m_cmt)
            size -= m_size
            break
        continue

    # return
    while size > 0:
        (m_offset,m_size),(m_name,m_cmt) = member.next()
        yield (m_offset,m_size),(m_name,m_cmt)
        size -= m_size

    return

def get(name):
    '''Returns an instance of the structure named ``name``.'''
    id = idaapi.get_struc_id(name)
    if id == idaapi.BADADDR:
        try: raise DeprecationWarning
        except: logging.warn('{:s}.get auto-creation is being deprecated'.format(__name__, exc_info=True))
        id = idaapi.add_struc(idaapi.BADADDR, name)
    return instance(id)

@utils.multicase(name=basestring)
def new(name):
    '''Returns a new structure ``name``.'''
    return new(name, 0)
@utils.multicase(name=basestring, offset=six.integer_types)
def new(name, offset):
    '''Returns a new structure ``name`` using ``offset`` as it's base-offset.'''
    id = idaapi.add_struc(idaapi.BADADDR, name)
    assert id != idaapi.BADADDR
    # FIXME: we should probably move the new structure to the end of the list via set_struc_idx
    return instance(id, offset=offset)

@utils.multicase(name=basestring)
def by(name, **options):
    '''Return a structure by it's name.'''
    return by_name(name, **options)
@utils.multicase(n=six.integer_types)
def by(n, **options):
    '''Return a structure by it's index or id.'''
    if n & 0xff000000 == 0xff000000:
        return instance(n, **options)
    return by_index(n, **options)

def by_name(name, **options):
    '''Return a structure by it's name.'''
    id = idaapi.get_struc_id(name)
    if id == idaapi.BADADDR:
        raise LookupError('{:s}.by_name : Unable to locate structure {!r}'.format(__name__, name))
    return instance(id, **options)
byName = utils.alias(by_name)

def by_index(index, **options):
    '''Return a structure by it's index.'''
    id = idaapi.get_struc_by_idx(index)
    if id == idaapi.BADADDR:
        raise IndexError('{:s}.by_index : Unable to locate structure #{:d}'.format(__name__, index))
    return instance(id, **options)
byIndex = utils.alias(by_index)

def instance(identifier, **options):
    '''Returns the structure identified by ``identifier``.'''
    try:
        cache = instance.cache
    except AttributeError:
        instance.cache = {}
        return instance(identifier, **options)
    res = cache.setdefault((identifier,options.get('offset',0)), structure_t(identifier, **options))
    if 'offset' in options:
        res.offset = options['offset']
    return res

### structure_t abstraction
class structure_t(__structure_t):
    """An abstraction around an IDA structure"""
    __slots__ = ('__id', '__members')

    def __init__(self, id, offset=0):
        self.__id = id
        self.__members = members_t(self, baseoffset=offset)

    @property
    def id(self):
        '''Return the identifier for the structure'''
        return self.__id
    @property
    def ptr(self):
        '''Return the structure's idaapi pointer.'''
        return idaapi.get_struc(self.id)
    @property
    def members(self):
        '''Return the members for the structure.'''
        return self.__members

    def __getstate__(self):
        cmtt = idaapi.get_struc_cmt(self.id, True)
        cmtf = idaapi.get_struc_cmt(self.id, False)
        # FIXME: perhaps we should preserve the get_struc_idx result too
        return (self.name,(cmtt,cmtf),self.members)
    def __setstate__(self, state):
        name,(cmtt,cmtf),members = state
        identifier = idaapi.get_struc_id(name)
        if identifier == idaapi.BADADDR:
            logging.warn('{:s}.structure_t.__setstate__ : Creating structure {:s} [{:d} fields]{:s}'.format(__name__, name, len(members), ' // {:s}'.format(cmtf or cmtt) if cmtf or cmtt else ''))
            identifier = idaapi.add_struc(idaapi.BADADDR, name)
        idaapi.set_struc_cmt(identifier, cmtt, True)
        idaapi.set_struc_cmt(identifier, cmtf, False)
        self.__id = identifier
        self.__members = members
        return

    @property
    def name(self):
        '''Return the name for the structure.'''
        return idaapi.get_struc_name(self.id)
    @name.setter
    def name(self, name):
        '''Set the name for the structure to ``name``.'''
        return idaapi.set_struc_name(self.id, name)
    @property
    def comment(self, repeatable=True):
        '''Return the repeatable comment for the structure.'''
        return idaapi.get_struc_cmt(self.id, repeatable)
    @comment.setter
    def comment(self, comment, repeatable=True):
        '''Set the repeatable comment for the structure to ``comment``.'''
        return idaapi.set_struc_cmt(self.id, comment, repeatable)
    @property
    def size(self):
        '''Return the size of the structure.'''
        return idaapi.get_struc_size(self.ptr)
    @property
    def offset(self):
        '''Return the base-offset of the structure.'''
        return self.members.baseoffset
    @offset.setter
    def offset(self, offset):
        '''Set the base-offset of the structure to ``offset``.'''
        res,self.members.baseoffset = self.members.baseoffset,offset
        return res
    @property
    def index(self):
        '''Return the index of the structure.'''
        return idaapi.get_struc_idx(self.id)
    @index.setter
    def index(self, idx):
        '''Set the index of the structure to ``idx``.'''
        return idaapi.set_struc_idx(self.ptr, idx)

    def destroy(self):
        '''Remove the structure from the database.'''
        return idaapi.del_struc(self.ptr)

    def __repr__(self):
        return "<type 'structure' name={!r}{:s} size=+{:x}>{:s}".format(self.name, (' offset={:x}'.format(self.offset) if self.offset > 0 else ''), self.size, ' // {:s}'.format(self.comment) if self.comment else '')

    def field(self, ofs):
        '''Return the member at the specified offset.'''
        return self.members.by_offset(ofs + self.members.baseoffset)

    def copy(self, name):
        '''Copy members into the structure ``name``.'''
        raise NotImplementedError

    def resize(self, size):
        raise NotImplementedError
        # FIXME: re-assign this method as a setter for .size
        res = idaapi.expand_struc(self.ptr, 0, size, recalc=True)
        if not res:
            logging.fatal('{:s}.instance({:s}).resize : Issue resizing {:s} : 0x{:x}'.format(__name__, self.name, size))
        return res

    def __getattr__(self, name):
        return getattr(self.members, name)

    #def resize(self, size):

class members_t(object):
    """An abstraction around the members of a particular IDA structure

    This allows one to treat each member as a dict.
    """
    __slots__ = ('__owner', 'baseoffset')

    # members state
    @property
    def owner(self):
        '''Return the structure_t that owns this members_t.'''
        return self.__owner
    @property
    def ptr(self):
        '''Return the members' idaapi pointer.'''
        return self.__owner.ptr.members
    def __init__(self, owner, baseoffset=0):
        self.__owner = owner
        self.baseoffset = baseoffset

    def __getstate__(self):
        return (self.owner.name,self.baseoffset,map(self.__getitem__,range(len(self))))
    def __setstate__(self, state):
        ownername,baseoffset,_ = state
        identifier = idaapi.get_struc_id(ownername)
        if identifier == idaapi.BADADDR:
            raise LookupError('{:s}.instance({:s}).members.__setstate__ : Failure creating a members_t for structure_t {!r}'.format(__name__, self.owner.name, ownername))
            logging.warn('{:s}.instance({:s}).members.__setstate__ : Creating structure {:s} -- [0x{:x}] {:d} members'.format(__name__, self.owner.name, ownername, baseoffset, len(members)))
            identifier = idaapi.add_struc(idaapi.BADADDR, ownername)
        self.baseoffset = baseoffset
        self.__owner = instance(identifier, offset=baseoffset)
        return

    # fetching members
    def __len__(self):
        '''Return the number of members within the structure.'''
        return 0 if self.owner.ptr is None else self.owner.ptr.memqty
    def __iter__(self):
        for idx in xrange(len(self)):
            yield member_t(self.owner, idx)
        return
    def __getitem__(self, index):
        '''Return the member at the specified ``index``.'''
        if isinstance(index, (int,long)):
            index = self.owner.ptr.memqty + index if index < 0 else index
            res = member_t(self.owner, index) if index >= 0 and index < self.owner.ptr.memqty else None
        elif isinstance(index, str):
            res = self.byname(index)
        elif isinstance(index, slice):
            res = [self.__getitem__(i) for i in range(self.owner.ptr.memqty)].__getitem__(index)
        else:
            raise TypeError, index

        if res is None:
            raise IndexError, index
        return res

    def index(self, member_t):
        '''Return the index of the member ``member_t``.'''
        for i in range(0, self.owner.ptr.memqty):
            if member_t.id == self[i].id:
                return i
            continue
        raise ValueError('{:s}.instance({:s}).members.index : {!r} not in list'.format(__name__, self.owner.name, member_t))

    # searching members
    @utils.multicase(string=basestring)
    def list(self, string):
        '''List any members that match the glob in `string`.'''
        return self.list(like=string)
    @utils.multicase()
    def list(self, **type):
        """List all the members within the structure.

        Search type can be identified by providing a named argument.
        like = glob match
        regex = regular expression
        index = particular index
        identifier = particular id number
        pred = function predicate
        """
        # FIXME: refactor this implementation into a utility module
        #        so that this can be reused elsewhere
        if 'regex' in type:
            match = lambda x: re.search(type['regex'], x.name)
        elif 'index' in type:
            match = lambda x: idaapi.get_struc_idx(x.id) == type['index']
        elif 'identifer' in type:
            match = lambda x: x.id == type['identifier']
        elif 'like' in type:
            match = lambda x: fnmatch.fnmatch(x.name, type['like'])
        elif 'pred' in type:
            match = type['pred']
        else:
            match = bool
        for x in itertools.ifilter(match,self):
            print '[{:d}] {:s} {:x}:+{:x} {!r}({:x},{:x},{:s}){:s}'.format(x.index, x.name, x.offset, x.size, x.type, x.flag, x.dt_type, '' if x.typeid is None else ', {:s}'.format(x.typeid), ' // {:s}'.format(x.comment) if x.comment else '')
        return

    @utils.multicase(name=basestring)
    def by(self, name):
        '''Return the member with the specified ``name``.'''
        return self.by_name(name)
    @utils.multicase(offset=six.integer_types)
    def by(self, offset):
        '''Return the member at the specified ``offset``.'''
        return self.by_offset(offset)

    def by_name(self, name):
        '''Return the member with the specified ``name``.'''
        mem = idaapi.get_member_by_name(self.owner.ptr, str(name))
        if mem is None: raise KeyError('{:s}.instance({:s}).members.by_name : Unable to find member with requested name : {!r}'.format(__name__, self.owner.name, name))
        index = self.index(mem)
        return self[index]
    byname = byName = utils.alias(by_name, 'members_t')
    def by_fullname(self, fullname):
        '''Return the member with the specified ``fullname``.'''
        mem = idaapi.get_member_by_fullname(self.owner.ptr, str(fullname))
        if mem is None: raise KeyError('{:s}.instance({:s}).members.by_fullname : Unable to find member with full name : {!r}'.format(__name__, self.owner.name, fullname))
        index = self.index(mem)
        return self[index]
    byfullname = byFullname = utils.alias(by_fullname, 'members_t')
    def by_offset(self, offset):
        '''Return the member at the specified ``offset``.'''
        min,max = map(lambda sz: sz + self.baseoffset, (idaapi.get_struc_first_offset(self.owner.ptr),idaapi.get_struc_last_offset(self.owner.ptr)))
        if (offset < min) or (offset >= max):
            raise LookupError('{:s}.instance({:s}).members.by_offset : Requested offset {:s} not within bounds (0x{:x},0x{:x})'.format(__name__, self.owner.name, '-0x{:x}'.format(abs(offset)) if offset < 0 else '0x{:x}'.format(offset), min, max))

        mem = idaapi.get_member(self.owner.ptr, offset - self.baseoffset)
        if mem is None:
            raise LookupError('{:s}.instance({:s}).members.by_offset : Unable to find member at offset : {:s}'.format(__name__, self.owner.name, '-0x{:x}'.format(abs(offset)) if offset < 0 else '0x{:x}'.format(offset)))

        index = self.index(mem)
        return self[index]
    byoffset = byOffset = utils.alias(by_offset, 'members_t')

    def near_offset(self, offset):
        '''Return the member near to the specified ``offset``.'''
        offset_repr = '-0x{:x}'.format(abs(offset)) if offset < 0 else '0x{:x}'.format(offset)
        min,max = map(lambda sz: sz + self.baseoffset, (idaapi.get_struc_first_offset(self.owner.ptr),idaapi.get_struc_last_offset(self.owner.ptr)))
        if (offset < min) or (offset >= max):
            logging.warn('{:s}.instance({:s}).members.near_offset : Requested offset {:s} not within bounds (0x{:x},0x{:x}). Trying anyways..'.format(__name__, self.owner.name, '-0x{:x}'.format(offset_repr), min, max))

        res = offset - self.baseoffset
        mem = idaapi.get_member(self.owner.ptr, res)
        if mem is None:
            res_repr = '-0x{:x}'.format(abs(res)) if res < 0 else '0x{:x}'.format(res)
            logging.info('{:s}.instance({:s}).members.near_offset : Unable to locate member at offset {:s}. Trying get_best_fit_member instead.'.format(__name__, self.owner.name, res))
            mem = idaapi.get_best_fit_member(self.owner.ptr, res)

        if mem is None:
            raise LookupError('{:s}.instance({:s}).members.near_offset : Unable to find member near offset : 0x{:x}'.format(__name__, self.owner.name, offset))

        index = self.index(mem)
        return self[index]
    nearoffset = nearOffset = utils.alias(near_offset, 'members_t')

    # adding/removing members
    @utils.multicase(name=basestring)
    def add(self, name, type):
        '''Append the specified member ``name`` with the given ``type`` at the end of the structure'''
        offset = self.owner.size + self.baseoffset
        return self.add(name, type, offset)
    @utils.multicase(name=basestring, offset=six.integer_types)
    def add(self, name, type, offset):
        """Add a member at ``offset`` with the given ``name`` and ``type``.
        To specify a particular size, ``type`` can be a tuple with the second element referring to the size.
        """
        flag,typeid,nbytes = interface.typemap.resolve(type)

        # FIXME: handle .strtype (strings), .ec (enums), .cd (custom)
        opinfo = idaapi.opinfo_t()
        opinfo.tid = typeid
        realoffset = offset - self.baseoffset
        realoffset_repr = '-0x{:x}'.format(abs(realoffset)) if realoffset < 0 else '0x{:x}'.format(realoffset)
        if name is None:
            logging.warn('{:s}.instance({:s}).members.add : name is undefined, defaulting to offset {:s}'.format(__name__, self.owner.name, realoffset_repr))
            name = 'v_{:s}'.format(realoffset)

        res = idaapi.add_struc_member(self.owner.ptr, name, realoffset, flag, opinfo, nbytes)
        if res == idaapi.STRUC_ERROR_MEMBER_OK:
            logging.info('{:s}.instance({:s}).members.add : idaapi.add_struc_member(sptr={!r}, fieldname={:s}, offset={:s}, flag=0x{:x}, mt=0x{:x}, nbytes=0x{:x}) : Success'.format(__name__, self.owner.name, self.owner.name, name, realoffset_repr, flag, typeid, nbytes))
        else:
            error = {
                idaapi.STRUC_ERROR_MEMBER_NAME : 'Duplicate field name',
                idaapi.STRUC_ERROR_MEMBER_OFFSET : 'Invalid offset',
                idaapi.STRUC_ERROR_MEMBER_SIZE : 'Invalid size',
            }
            callee = 'idaapi.add_struc_member(sptr={!r}, fieldname={:s}, offset={:s}, flag=0x{:x}, mt=0x{:x}, nbytes=0x{:x})'.format(self.owner.name, name, realoffset_repr, flag, typeid, nbytes)
            logging.fatal(' : '.join(('members_t.add', callee, error.get(res, 'Error code 0x{:x}'.format(res)))))
            return None

        res = idaapi.get_member(self.owner.ptr, realoffset)
        if res is None:
            logging.fatal("{:s}.instance({:s}.members.add : Failed creating member {!r} {:s}:+0x{:x}".format(__name__, self.owner.name, name, realoffset_repr, nbytes))

        # sloppily figure out what the correct index is
        idx = self.index( idaapi.get_member(self.owner.ptr, realoffset) )
        return member_t(self.owner, idx)

    def pop(self, index):
        '''Remove the member at the specified ``index``.'''
        item = self[index]
        return self.remove(item.offset - self.baseoffset)
    def __delitem__(self, index):
        return self.pop(index)

    @utils.multicase()
    def remove(self, offset):
        '''Remove all the member from the structure at ``offset``.'''
        return idaapi.del_struc_member(self.owner.ptr, offset - self.baseoffset)
    @utils.multicase()
    def remove(self, offset, size):
        '''Remove all the members from the structure from ``offset`` up to ``size``.'''
        ofs = offset - self.baseoffset
        return idaapi.del_struc_members(self.owner.ptr, ofs, ofs+size)

    def __repr__(self):
        '''Display all the fields within the specified structure.'''
        result = []
        for i in xrange(len(self)):
            m = self[i]
            name,t,ofs,size,comment = m.name,m.type,m.offset,m.size,m.comment
            result.append((i,name,t,ofs,size,comment))
        return '{!r}\n{:s}'.format(self.owner, '\n'.join(' [{:d}] {:s} {!r} {{{:x}:+{:x}}}{:s}'.format(i,n,t,o,s,' // {:s}'.format(c) if c else '') for i,n,t,o,s,c in result))

class member_t(object):
    '''Contains information about a particular member within a given structure'''
    __slots__ = ('__owner', '__index')

    def __init__(self, owner, index):
        '''Create a member_t for the field in the structure ``owner`` at ``index``.'''
        self.__index = index
        self.__owner = owner

    def __getstate__(self):
        t = (self.flag,None if self.typeid is None else instance(self.typeid),self.size)
        cmtt = idaapi.get_member_cmt(self.id, True)
        cmtf = idaapi.get_member_cmt(self.id, False)
        ofs = self.offset - self.__owner.members.baseoffset
        return (self.__owner.name,self.__index,self.name,(cmtt,cmtf),ofs,t)
    def __setstate__(self, state):
        ownername,index,name,(cmtt,cmtf),ofs,t = state

        identifier = idaapi.get_struc_id(ownername)
        if identifier == idaapi.BADADDR:
            logging.warn('{:s}.instance({:s}).member_t : Creating structure {:s} -- [0x{:x}] {:s}{:s}'.format(__name__, ownername, ownername, ofs, name, ' // {:s}'.format(cmtt or cmtf) if cmtt or cmtf else ''))
            identifier = idaapi.add_struc(idaapi.BADADDR, ownername)
        self.__owner = owner = instance(identifier, offset=0)

        flag,mytype,nbytes = t

        # FIXME: handle .strtype (strings), .ec (enums), .cd (custom)
        opinfo = idaapi.opinfo_t()
        opinfo.tid = 0 if mytype is None else mytype.id

        res = idaapi.add_struc_member(owner.ptr, name, ofs, flag, opinfo, nbytes)

        # FIXME: handle these errors properly
        # duplicate name
        if res == idaapi.STRUC_ERROR_MEMBER_NAME:
            if idaapi.get_member_by_name(owner.ptr, name).soff != ofs:
                newname = '{:s}_{:x}'.format(name,ofs)
                logging.warn('{:s}.instace({:s}).member_t : Duplicate name found for {:s}, renaming to {:s}'.format(__name__, ownername, name, newname))
                idaapi.set_member_name(owner.ptr, ofs, newname)
            else:
                logging.info('{:s}.instance({:s}).member_t : Field at 0x{:x} contains the same name {:s}'.format(__name__, ownername, ofs, name))
        # duplicate field
        elif res == idaapi.STRUC_ERROR_MEMBER_OFFSET:
            logging.info('{:s}.instance({:s}).member_t : Field already found at 0x{:x}. Overwriting with {:s}'.format(__name__, ownername, ofs, name))
            idaapi.set_member_type(owner.ptr, ofs, flag, opinfo, nbytes)
            idaapi.set_member_name(owner.ptr, ofs, name)
        # invalid size
        elif res == idaapi.STRUC_ERROR_MEMBER_SIZE:
            logging.warn('{:s}.instance({:s}).member_t : Issue creating structure member {:s}.{:s} : 0x{:x}'.format(__name__, ownername, ownername, name, res))
        # unknown
        elif res != idaapi.STRUC_ERROR_MEMBER_OK:
            logging.warn('{:s}.instance({:s}).member_t : Issue creating structure member {:s}.{:s} : 0x{:x}'.format(ownername, ownername, name, res))

        self.__index = index
        self.__owner = owner

        idaapi.set_member_cmt(self.ptr, cmtt, True)
        idaapi.set_member_cmt(self.ptr, cmtf, False)
        return

    # read-only properties
    @property
    def ptr(self):
        '''Return the member's idaapi pointer.'''
        return self.__owner.ptr.get_member(self.__index)
    @property
    def id(self):
        '''Return the `.id` attribute of the member.'''
        return self.ptr.id
    @property
    def size(self):
        '''Return the size of the member.'''
        return idaapi.get_member_size(self.ptr)
    @property
    def offset(self):
        '''Return the member's offset.'''
        return self.ptr.get_soff() + self.__owner.members.baseoffset
    @property
    def flag(self):
        '''Return the member's `.flag` attribute.'''
        m = idaapi.get_member(self.__owner.ptr, self.offset - self.__owner.members.baseoffset)
        return 0 if m is None else m.flag
    @property
    def fullname(self):
        '''Return the member's fullname.'''
        return idaapi.get_member_fullname(self.id)
    @property
    def typeid(self):
        '''Return the `.tid` of the member's type.'''
        opinfo = idaapi.opinfo_t()
        res = idaapi.retrieve_member_info(self.ptr, opinfo)
        return None if res is None else res.tid if res.tid != idaapi.BADADDR else None
    @property
    def index(self):
        '''Return the index of the member.'''
        return self.__index
    @property
    def left(self):
        '''Return the beginning offset of the member.'''
        return self.ptr.soff
    @property
    def right(self):
        '''Return the ending offset of the member.'''
        return self.ptr.eoff

    # read/write properties
    @property
    def name(self):
        '''Return the member's name.'''
        return idaapi.get_member_name(self.id) or ''
    @name.setter
    def name(self, value):
        '''Set the member's name.'''
        return idaapi.set_member_name(self.__owner.ptr, self.offset - self.__owner.members.baseoffset, value)
    @property
    def comment(self):
        '''Return the member's repeable comment.'''
        return idaapi.get_member_cmt(self.id, True)
    @comment.setter
    def comment(self, value):
        '''Set the member's repeatable comment.'''
        return idaapi.set_member_cmt(self.ptr, value, True)
    @property
    def dt_type(self):
        '''Return the member's `.dt_type` attribute.'''
        m = idaapi.get_member(self.__owner.ptr, self.offset - self.__owner.members.baseoffset)
        if m is None:
            return 0
        flag = m.flag & idaapi.FF_MASK

        # idaapi(swig) and python have different definitions of what constant values are
        max = (sys.maxint+1)*2
        return flag if flag < sys.maxint else flag - max
    @property
    def type(self):
        '''Return the member's type in it's pythonic form.'''
        res = interface.typemap.dissolve(self.flag,self.typeid,self.size)
        if isinstance(res, structure_t):
            res = instance(res.id, offset=self.offset)
        elif isinstance(res, tuple):
            t,sz = res
            if isinstance(t, structure_t):
                t = instance(t.id, offset=self.offset)
            elif isinstance(t, [].__class__) and isinstance(t[0], structure_t):
                t[0] = instance(t[0].id, offset=self.offset)
            res = t,sz
        return res
    @type.setter
    def type(self, type):
        '''Set the member's type.'''
        flag,typeid,size = interface.typemap.resolve(type)
        opinfo = idaapi.opinfo_t()
        opinfo.tid = typeid
        return idaapi.set_member_type(self.__owner.ptr, self.offset, flag, opinfo, size)

    #def resize(self, size):
    #    # FIXME: re-assign this method as a setter for .size
    #    res = idaapi.expand_struc(self.owner.ptr, self.offset, size, recalc=True)
    #    if not res:
    #        logging.fatal('structure_t({!r}).member_t[{:d}].resize : Issue resizing field {:s} : 0x{:x}'.format(self.owner.name, self.index, self.fullname, size))
    #    return res

    def __repr__(self):
        '''Display the specified member in a readable format.'''
        id,name,typ,comment = self.id,self.name,self.type,self.comment
        offset_repr = '-0x{:x}'.format(abs(self.offset)) if self.offset < 0 else '0x{:x}'.format(self.offset)
        return '{:s} [{:d}] {:s} {:s} {{{!r}:+0x{:x}}}{:s}'.format(self.__class__, self.index, name, typ, offset_repr, self.size, ' // {:d}'.format(comment) if comment else '')

