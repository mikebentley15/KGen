# kgen_state.py
# data structure

from kgen_utils import Logger, Config, singleton, UserException
from api import parse, walk
from ordereddict import OrderedDict

@singleton
class State(object):
    # KGEN states
    CREATED, CALLSITE_LOCATED, KERNELINFO_COLLECTED, GENINFO_MARKED, \
        STATE_GENERATED, KERNEL_GENERATED, MAKEFILES_GENERATED = range(7)

    # TKDPAT types
    TB_EXTERN, PB_INPUT, PB_OUTPUT, KD_INPUT, DT_MODULE, DT_CALLMODULE, DT_CALLPARENT, MOD_EXTERN = range(8)

    # module number
    mod_num = 1

    def __init__(self):

        # attributes holder
        self._attrs = OrderedDict()

        # KGEN state
        self._attrs['state'] = self.CREATED

        # callsite attributes
        self._attrs['callsite'] = OrderedDict()
        self._attrs['callsite']['stmts'] = []
#        self._attrs['callsite']['expr'] = None
#        self._attrs['callsite']['actual_arg'] = OrderedDict()
#        self._attrs['callsite']['actual_arg']['names'] = None # ActualArgList object
#        self._attrs['callsite']['actual_arg']['in_names'] = []
#        self._attrs['callsite']['actual_arg']['out_names'] = []
#        self._attrs['callsite']['actual_arg']['inout_names'] = []
#        self._attrs['callsite']['actual_arg']['typedecl_stmt'] = OrderedDict()

        # parent subprogram of callsite stmt attributes
        self._attrs['parentblock'] = OrderedDict()
        self._attrs['parentblock']['stmt'] = None
#        self._attrs['parentblock']['expr'] = None
#        self._attrs['parentblock']['dummy_arg'] = OrderedDict()
#        self._attrs['parentblock']['dummy_arg']['names'] = []
#        self._attrs['parentblock']['dummy_arg']['in_names'] = []
#        self._attrs['parentblock']['dummy_arg']['out_names'] = []
#        self._attrs['parentblock']['dummy_arg']['inout_names'] = []
#        self._attrs['parentblock']['dummy_arg']['typedecl_stmt'] = OrderedDict()
#        self._attrs['parentblock']['input'] =  OrderedDict()# variables for callsite actual args and kernel externs
#        self._attrs['parentblock']['input']['names'] = []
#        self._attrs['parentblock']['input']['typedecl_stmt'] = OrderedDict()
#        self._attrs['parentblock']['output'] = OrderedDict() # variables for callsite outputs
#        self._attrs['parentblock']['output']['names'] = []
#        self._attrs['parentblock']['output']['typedecl_stmt'] = OrderedDict()
#        self._attrs['parentblock']['output']['tkdpat'] = []
#        self._attrs['parentblock']['inout'] = OrderedDict()
#        self._attrs['parentblock']['inout']['tkdpat'] = []
#        self._attrs['parentblock']['writesubr'] = OrderedDict()
#        self._attrs['parentblock']['writesubr']['tkdpat'] = []
#        self._attrs['parentblock']['mod_rw_var_depends'] = [] # dependency for call kgen_write_var
#        self._attrs['parentblock']['dtype'] = [] # derived types

        # callsite topblock attributes
        self._attrs['topblock'] = OrderedDict()
#        self._attrs['topblock']['file'] = None # SrcFile object
#        self._attrs['topblock']['path'] = '' # absolute path
        self._attrs['topblock']['stmt'] = None
#        self._attrs['topblock']['expr'] = None
#        self._attrs['topblock']['extern'] = OrderedDict()
#        self._attrs['topblock']['extern']['names'] = []
#        self._attrs['topblock']['extern']['typedecl_stmt'] = OrderedDict()
#        self._attrs['topblock']['extern']['tkdpat'] = []
#        #self._attrs['topblock']['mod_depends'] = [] # dependency for compile
#        self._attrs['topblock']['mod_rw_var_depends'] = [] # dependency for call kgen_write_var
#        self._attrs['topblock']['dtype'] = [] # derived types

        # kernel attributes
        self._attrs['kernel'] = OrderedDict()
        self._attrs['kernel']['name'] = None
#        self._attrs['kernel']['stmt'] = None
#        self._attrs['kernel']['expr'] = None
#        self._attrs['kernel']['parent'] = None
#        self._attrs['kernel']['top'] = None
#        self._attrs['kernel']['dummy_arg'] = OrderedDict()
#        self._attrs['kernel']['dummy_arg']['names'] = []
#        self._attrs['kernel']['dummy_arg']['in_names'] = []
#        self._attrs['kernel']['dummy_arg']['out_names'] = []
#        self._attrs['kernel']['dummy_arg']['inout_names'] = []
#        self._attrs['kernel']['dummy_arg']['typedecl_stmt'] = OrderedDict()
#
        # modules
        self._attrs['modules'] = OrderedDict()

        # src files
        self._attrs['srcfiles'] = OrderedDict()

        # used src files
        self._attrs['used_srcfiles'] = OrderedDict()

        # imported files
        self._attrs['imported'] = OrderedDict()
        self._attrs['imported']['source'] = []


        # kernel_driver attributes
        self._attrs['kernel_driver'] = OrderedDict()
#        self._attrs['kernel_driver']['input'] = OrderedDict()
#        self._attrs['kernel_driver']['input']['names'] = []
#        self._attrs['kernel_driver']['input']['typedecl_stmt'] = OrderedDict()
#        self._attrs['kernel_driver']['input']['tkdpat'] = []
#        self._attrs['kernel_driver']['mod_rw_var_depends'] = []
#        # new kernel_driver attributes
        self._attrs['kernel_driver']['name'] = 'kernel_driver'
#        self._attrs['kernel_driver']['program'] = None
        self._attrs['kernel_driver']['callsite_args'] = ['kgen_unit', 'kgen_elapsed_time', 'kgen_isverified']

        # program units
        self._attrs['program_units'] = OrderedDict()
#
#        # new attribute holder for multiple kernels
#        self._attrs['kernels'] = OrderedDict()
#        self._attrs['kernels'][0] = OrderedDict()
#        self._attrs['kernels'][0]['name'] = 'dummy_name_test'

    def __getattr__(self, name):
        return self._attrs[name]

class ResState(object):
    ( NOT_STARTED, RESOLVED ) = range(2)

    def __init__(self, gentype, uname, org, resolvers):
        self.state = self.NOT_STARTED
        self.gentype = gentype
        self.uname = uname
        self.originator = org
        self.resolvers = resolvers
        #self.temp_uname = None
        #self.res_stmt = None
        self.res_stmts = []
        self.unamelist = [uname]

    def push_uname(self, uname):
        self.unamelist.append(uname)
        self.uname = uname

    def pop_uname(self, reset_uname=False):
        newname = self.unamelist.pop()
        self.uname = self.unamelist[-1]
        if len(self.res_stmts)>0 and reset_uname:
            newlist = []
            for (resuname, req) in self.res_stmts[-1].geninfo.values()[0]:
                if resuname==newname:
                    newlist.append((self.uname, req))
                else:
                    newlist.append((resuname, req))
                    pass
            self.res_stmts[-1].geninfo.values()[0] = newlist
            

class SrcFile(object):
    def handle_include(self, lines):
        import re
        import os

        insert_lines = []
        for i, line in enumerate(lines):
            match = re.match(r'^\s*include\s*("[^"]+"|\'[^\']+\')\s*\Z', line, re.I)
            #if not match:
            #    match = re.match(r'\s*#include\s*("[^"]+"|\<[^\']+\>)\s*\Z', line, re.I)
            if match:
                if Config.include['file'].has_key(self.abspath):
                    include_dirs = Config.include['file'][self.abspath]['path']+Config.include['path']
                else:
                    include_dirs = Config.include['path']
                filename = match.group(1)[1:-1].strip()
                path = filename
                for incl_dir in include_dirs+[os.path.dirname(self.abspath)]:
                    path = os.path.join(incl_dir, filename)
                    if os.path.exists(path):
                        break
                if os.path.isfile(path):
                    with open(path, 'r') as f:
                        included_lines = f.read()
                        insert_lines.extend(self.handle_include(included_lines.split('\n')))
                else:
                    raise UserException('Can not find %s in include paths of %s.'%(filename, self.abspath))
            else:
                insert_lines.append(line)

        return insert_lines

    def __init__(self, srcpath):
        import os.path
        from kgen_utils import exec_cmd
        from statements import Comment
        from block_statements import Module, Program

        # set default values
        self.tree = None
        self.srcpath = srcpath
        self.abspath = os.path.abspath(self.srcpath)

        
        # set source file format
        isfree = True
        isstrict = False
        if self.abspath in Config.source['file'].keys():
            if Config.source['file'][self.abspath].has_key('isfree'):
                isfree = Config.source['file'][self.abspath]['isfree']
            if Config.source['file'][self.abspath].has_key('isstrict'):
                isstrict = Config.source['file'][self.abspath]['isstrict']
        else:
            if Config.source['isstrict']: isstrict = Config.source['isstrict']
            if Config.source['isfree']: isfree = Config.source['isfree']

        # prepare include paths and macro definitions
        path_src = []
        macros_src = []
        if Config.include['file'].has_key(self.abspath):
            path_src = Config.include['file'][self.abspath]['path']+[os.path.dirname(self.abspath)]
            for k, v in Config.include['file'][self.abspath]['macro'].iteritems():
                if v:
                    macros_src.append('-D%s=%s'%(k,v))
                else:
                    macros_src.append('-D%s'%k)
        includes = '-I'+' -I'.join(Config.include['path']+path_src)
        macros_common = []
        for k, v in Config.include['macro'].iteritems():
            if v:
                macros_common.append('-D%s=%s'%(k,v))
            else:
                macros_common.append('-D%s'%k)
        macros = ' '.join(macros_common + macros_src)

        # execute preprocessing
        Logger.info('Reading %s'%self.srcpath, stdout=True)
        pp = Config.bin['pp']
        if pp.endswith('fpp'):
            if isfree: srcfmt = ' -free'
            else: srcfmt = ' -fixed'
            flags = Config.bin['fpp_flags'] + srcfmt
        elif pp.endswith('cpp'):
            flags = Config.bin['cpp_flags']
        else: raise UserException('Preprocessor is not either fpp or cpp')

        new_lines = []
        with open(self.abspath, 'r') as f:
            output = exec_cmd('%s %s %s %s' % (pp, flags, includes, macros), input=f.read())
            prep = map(lambda l: '!KGEN'+l if l.startswith('#') else l, output.split('\n'))
            new_lines = self.handle_include(prep)

        # add include paths
        if Config.include['file'].has_key(self.abspath) and Config.include['file'][self.abspath].has_key('path'):
            include_dirs = Config.include['file'][self.abspath]['path'] + [os.path.dirname(self.abspath)]
        else: include_dirs = None

        #if self.abspath=='/glade/scratch/youngsun/kgen_system_test/branches/initial/MPAS-Release/src/framework/mpas_derived_types.F':
        #    print '\n'.join(new_lines)
        #    sys.exit()
        #    import pdb ; pdb.set_trace()

        # fparse
        self.tree = parse('\n'.join(new_lines), ignore_comments=False, analyze=True, isfree=isfree, \
            isstrict=isstrict, include_dirs=include_dirs, source_only=None )
        self.tree.prep = new_lines
        self.tree.used4genstate = False

        #if self.abspath=='/glade/scratch/youngsun/kgen_system_test/branches/initial/MPAS-Release/src/framework/mpas_derived_types.F':
        #    print self.tree
        #    sys.exit()

        # parse f2003
        lineno = 0
        linediff = 0
        for stmt, depth in walk(self.tree, -1):
            stmt.parse_f2003()

        # rename reader.id
        self.tree.reader.id = self.abspath

        # collect module information
        for mod_name, mod_stmt in self.tree.a.module.iteritems(): 
            if not State.modules.has_key(mod_name):
                State.modules[mod_name] = OrderedDict()
                #State.modules[mod_name]['num'] = State.mod_num
                #State.mod_num += 1
                State.modules[mod_name]['stmt'] = mod_stmt
                State.modules[mod_name]['file'] = self
                State.modules[mod_name]['path'] = self.abspath
                #State.modules[mod_name]['extern'] = OrderedDict()
                #State.modules[mod_name]['extern']['names'] = []
                #State.modules[mod_name]['extern']['typedecl_stmt'] = OrderedDict()
                #State.modules[mod_name]['extern']['tkdpat'] = []
                #State.modules[mod_name]['mod_rw_var_depends'] = []
                #State.modules[mod_name]['dtype'] = []
        
        # collect program unit information
        for item in self.tree.content:
            if item.__class__ not in [ Module, Comment, Program ]:
                if item.reader.id not in State.program_units.keys():
                    State.program_units[item.reader.id] = []
                State.program_units[item.reader.id].append(item)

        # create a tuple for file dependency
        State.srcfiles[self.abspath] = ( self, [], [] )

    def stmt_by_name(self, name, cls=None, lineafter=-1):
        from statements import Comment

        for stmt, depth in walk(self.tree, -1):
            if isinstance(cls, list):
                if not stmt.__class__ in cls: continue 

            if lineafter>0:
                if stmt.item.span[1]<=lineafter: continue
                if isinstance(stmt, Comment): continue
 
            expr = stmt.expr_by_name(name, stmt.f2003)
            if expr: return stmt, expr

        return None, None

import unittest
class Test_kgen_state(unittest.TestCase):

    def setUp(self):
        pass

    def test_true(self):
        pass

if __name__ == "__main__":
    import sys
    #unittest.main(argv=[sys.argv[0]], verbosity=2) # verbosity is available from Python 2.7
    unittest.main(argv=[sys.argv[0]])
