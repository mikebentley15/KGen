# kgen_search.py

from kgen_utils import Config, Logger, show_tree, KGGenType
import Fortran2003
from typedecl_statements import TypeDeclarationStatement, TypeStmt
from block_statements import Type, TypeDecl, Function, Subroutine, Interface, execution_part
from statements import External, Common, SpecificBinding
from kgen_extra import Intrinsic_Procedures
from ordereddict import OrderedDict

res_default = [ TypeDeclarationStatement ]
res_external = [ External ]
res_typedecl = [ TypeDeclarationStatement ]
res_typestmt = [ TypeStmt ]
res_derivedtype = [ Type, TypeDecl ] 
res_kind = [ TypeDeclarationStatement ] + res_derivedtype
res_typespec = [ TypeDeclarationStatement ] + res_derivedtype
res_value = [ TypeDeclarationStatement, Function, Interface ] + res_external
res_subroutine = [ Subroutine, Interface ] + res_external
res_function = [ Function, Interface ] + res_external
res_subprogram = [ Subroutine, Function, Interface ] + res_external
res_common = [ Common ]
res_ptr_object = [ SpecificBinding, TypeDeclarationStatement ]
res_target = res_subprogram + res_typedecl
res_anything = res_typespec + res_subprogram + [ SpecificBinding, Common, Type, TypeDecl ]

###############################################################################
################################### COMMON ####################################
###############################################################################

class SearchException(Exception):
    pass

def is_except(name, stmt):
    if not name or not stmt: return False

    namelist = [a.name for a in stmt.ancestors()]
    namelist.append(name.string.lower())
    exceptlist = Config.search['except']

    for elist in exceptlist:
        elist_split = elist.split(':')
        same = True
        for i in range(min(len(namelist), len(elist_split))):
            if namelist[len(namelist)-i-1]!=elist_split[len(elist_split)-i-1]:
                same = False
                break
        if same: return True

    return False

def f2003_search_unknowns(stmt, node, resolvers=None, gentype=None):
    if node is None: return

    # skip searching if specified
    if ( hasattr(node, 'skip_search') and node.skip_search ) or \
        ( hasattr(node, 'parent') and hasattr(node.parent, 'skip_search') and node.parent.skip_search ):
        return

    # save in unknowns dict in stmt
    if not hasattr(stmt, 'unknowns'):
        stmt.unknowns = OrderedDict()

    clsname = node.__class__.__name__

    if clsname=='Name':
        get_name(stmt, node, resolvers, gentype=gentype)
        return

    itemclsname = None
    try:
        if clsname.endswith('_List'):
            _clsname = clsname[:-5]
            for item in node.items:
                if item is None: continue
                itemclsname = item.__class__.__name__
                if itemclsname=='Name':
                    get_name(stmt, item, resolvers, gentype=gentype)
                else:
                    exec('search_%s(stmt, item, gentype=gentype)' % itemclsname)
        elif clsname.startswith('End_'):
            pass
        else:
            exec('search_%s(stmt, node, gentype=gentype)' % clsname)
    except Exception as e:
        errname = clsname
        if itemclsname:
            errname = itemclsname
        errmsg = "Error: Fortran specification of %s is not supported yet."%errname

        Logger.exception(errmsg, node=node)

        if Config.search['promote_exception']:
            raise
        else:
            print ''
            print errmsg
            print ''
            print "'kgen.log' in output folder contains detail information of this error."
            print "If you send the log file to 'kgen@ucar.edu', that could be very"
            print "helpful for us to support this Fortran spec. in future KGEN version."
            print ''
            import sys
            sys.exit(-1)

def get_name_or_defer(stmt, node, resolvers, defer=True, gentype=None):
    from kgen_utils import KGName, pack_innamepath, get_innamepath, match_namepath
    from kgen_state import ResState

    if node is None: return

    # uncomment below line for debug
    #print node.__class__, str(node)

    if isinstance(node, Fortran2003.Name):

        # skip if intrinsic
        if node.string.lower() in Intrinsic_Procedures:
            if  Config.search['skip_intrinsic'] and not is_except(node, stmt):
                if hasattr(node, 'parent') and not isinstance(node.parent, Fortran2003.Part_Ref) and \
                    not (isinstance(node.parent, Fortran2003.Function_Reference) and node.string.lower()=='null') and \
                    not (isinstance(node.parent, Fortran2003.Specific_Binding) and node.string.lower()=='null'):
                    Logger.info('Intrinsic procedure name of "%s" is used for name resolution'% \
                        (node.string.lower()), stdout=True)
                    Logger.info('\tnear "%s"'% stmt.item.line, stdout=True)
                    Logger.info('\tin %s'% stmt.reader.id, stdout=True)
                else:
                    #if node.string.lower()!='null':
                    #    Logger.info('Intrinsic procedure name of "%s" is skipped from name resolution'% \
                    #        (node.string.lower()), stdout=True)
                    #Logger.info('\tnear "%s"'% stmt.item.line, stdout=True)
                    #Logger.info('\tin %s'% stmt.reader.id, stdout=True)
                    return
    
            elif not Config.search['skip_intrinsic'] and is_except(node, stmt): 
                if hasattr(node, 'parent') and not isinstance(node.parent, Fortran2003.Part_Ref) and \
                    not (isinstance(node.parent, Fortran2003.Function_Reference) and node.string.lower()=='null') and \
                    not (isinstance(node.parent, Fortran2003.Specific_Binding) and node.string.lower()=='null'):
                    #Logger.info('Intrinsic procedure name of "%s" is NOT skipped from name resolution'% \
                    #    (node.string.lower()), stdout=True)
                    #Logger.info('\tnear "%s"'% stmt.item.line, stdout=True)
                    #Logger.info('\tin %s'% stmt.reader.id, stdout=True)
                    pass
                else:
                    if node.string.lower()!='null':
                        Logger.info('Intrinsic procedure name of "%s" is skipped from name resolution'% \
                            (node.string.lower()), stdout=True)
                    Logger.info('\tnear "%s"'% stmt.item.line, stdout=True)
                    Logger.info('\tin %s'% stmt.reader.id, stdout=True)
                    return

        # skip if excluded
        #if Config.exclude.has_key('namepath') and stmt.__class__ in execution_part:
        if Config.exclude.has_key('namepath'):
            for pattern, actions in Config.exclude['namepath'].iteritems():
                name = node.string.lower()
                namepath = pack_innamepath(stmt, name) 
                if match_namepath(pattern, namepath):
                    if not hasattr(stmt, 'exclude_names'): stmt.exclude_names = OrderedDict()
                    if stmt.exclude_names.has_key(name):
                        stmt.exclude_names[name].extend(actions)
                    else:
                        stmt.exclude_names[name] = actions
                    node.skip_search = True
                    if hasattr(node, 'parent'): node.parent.skip_search = True
                    return

        ukey = KGName(pack_innamepath(stmt, node.string.lower()), node=node, stmt=stmt)

        if gentype is None: gentype = KGGenType.STATE_IN

        if resolvers is None:
            stmt.unknowns[ukey] = ResState(gentype, ukey, stmt, res_default)
        else:
            stmt.unknowns[ukey] = ResState(gentype, ukey, stmt, resolvers)
        Logger.info('%s is saved as unknown' % node.string.lower(), name=ukey, stmt=stmt)

    elif defer:
        f2003_search_unknowns(stmt, node, resolvers, gentype=gentype)

def get_name(stmt, node, resolvers, gentype=None):
    get_name_or_defer(stmt, node, resolvers, defer=False, gentype=gentype)

def defer(stmt, node, gentype=None):
    if isinstance(node, Fortran2003.Name):
        raise SearchException('%s can not be Name class' % str(node))
    f2003_search_unknowns(stmt, node, gentype=gentype)


def defer_items(stmt, node, gentype=None):
    if hasattr(node, 'items'):
        for item in node.items:
            if isinstance(item, Fortran2003.Name):
                raise SearchException('%s can not be Name class' % str(item))
            f2003_search_unknowns(stmt, item, gentype=gentype)

###############################################################################
################################### SEARCH ####################################
###############################################################################

def search_Type_Declaration_Stmt(stmt, node, gentype=None):  
    from kgen_utils import pack_innamepath, match_namepath

    # collect excluded names
    if Config.exclude.has_key('namepath'):
        for pattern, actions in Config.exclude['namepath'].iteritems():
            decls = []
            if isinstance(node.items[2], Fortran2003.Entity_Decl):
                decls.append(node.items[2].items[0].string.lower())
            elif isinstance(node.items[2], Fortran2003.Entity_Decl_List):
                for item in node.items[2].items:
                    decls.append(item.items[0].string.lower())
            for decl in decls:
                namepath = pack_innamepath(stmt, decl) 
                if match_namepath(pattern, namepath):
                    if not hasattr(stmt, 'exclude_names'): stmt.exclude_names = OrderedDict()
                    if stmt.exclude_names.has_key(decl):
                        stmt.exclude_names[decl].extend(actions)
                    else:
                        stmt.exclude_names[decl] = actions

    defer_items(stmt, node)

def search_Intrinsic_Type_Spec(stmt, node, gentype=None): 
    defer(stmt, node.items[1])

def search_Kind_Selector(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[1], res_kind)

def search_Entity_Decl(stmt, node, gentype=None): 
    defer(stmt, node.items[1])
    get_name_or_defer(stmt, node.items[2], res_value)
    get_name_or_defer(stmt, node.items[3], res_value) 

def search_Explicit_Shape_Spec(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Dimension_Attr_Spec(stmt, node, gentype=None): 
    defer(stmt, node.items[1])

def search_Add_Operand(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Mult_Operand(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Attr_Spec(stmt, node, gentype=None): 
    defer_items(stmt, node)

def search_Initialization(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Part_Ref(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value, gentype=gentype) 
    get_name_or_defer(stmt, node.items[1], res_value) 

def search_Structure_Constructor_2(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Int_Literal_Constant(stmt, node, gentype=None): 
    if node.items[1]:
        get_name_or_defer(stmt, Fortran2003.Name(node.items[1]), res_typedecl)

def search_Signed_Int_Literal_Constant(stmt, node, gentype=None): 
    if node.items[1]:
        get_name_or_defer(stmt, Fortran2003.Name(node.items[1]), res_typedecl)

def search_Real_Literal_Constant(stmt, node, gentype=None): 
    if node.items[1]:
        get_name_or_defer(stmt, Fortran2003.Name(node.items[1]), res_typedecl)

def search_Signed_Real_Literal_Constant(stmt, node, gentype=None): 
    if node.items[1]:
        get_name_or_defer(stmt, Fortran2003.Name(node.items[1]), res_typedecl)

def search_Subroutine_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[2], res_typedecl) # dummy args
    get_name_or_defer(stmt, node.items[3], res_typedecl) # postfix

def search_Comment(stmt, node, gentype=None): 
    pass

def search_Nonlabel_Do_Stmt(stmt, node, gentype=None): 
    if len(node.items)==3:
        defer(stmt, node.items[2])
    elif len(node.items)==2:
        if isinstance(node.items[0], str):
            defer(stmt, node.items[1])

def search_Loop_Control(stmt, node, gentype=None): 
    if len(node.items)==1:
        get_name_or_defer(stmt, node.items[0], res_value)
    else:
        get_name_or_defer(stmt, node.items[0], res_typedecl, gentype=KGGenType.STATE_OUT)
        if isinstance(node.items[1], list):
            for item in node.items[1]:
                get_name_or_defer(stmt, item, res_value)
        else:
            get_name_or_defer(stmt, node.items[1], res_value)

def search_Assignment_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value, gentype=KGGenType.STATE_OUT)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Level_2_Expr(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Parenthesis(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[1], res_value, gentype=gentype)

def search_str(stmt, string, gentype=None):
    pass

def search_Function_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_derivedtype ) # prefix
    get_name_or_defer(stmt, node.items[2], res_typedecl) # dummy args
    get_name_or_defer(stmt, node.items[3], res_typedecl)

def search_Assumed_Shape_Spec(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Allocate_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_typespec)
    get_name_or_defer(stmt, node.items[1], res_typedecl)
    defer(stmt, node.items[2])

def search_Allocation(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_typedecl)
    get_name_or_defer(stmt, node.items[1], res_value)
    #if len(node.items)>1:
    #    defer_items(stmt, node.items[1:])

def search_Allocate_Shape_Spec(stmt, node, gentype=None): 
    if node.items:
        for item in node.items:
            get_name_or_defer(stmt, item, res_value)

def search_Use_Stmt(stmt, node, gentype=None): 
    pass

def search_If_Then_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)

def search_Level_4_Expr(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_If_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Else_If_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Else_Stmt(stmt, node, gentype=None): 
    pass

def search_Level_2_Unary_Expr(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[1], res_value)


def search_Label_Do_Stmt(stmt, node, gentype=None): 
    defer(stmt, node.items[2])

def search_Array_Constructor(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[1], res_value) 

def search_Array_Section(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    defer(stmt, node.items[1])

def search_Substring_Range(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Select_Case_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)

def search_Case_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)

def search_Case_Selector(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)

def search_Call_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_subroutine)
    if isinstance(node.items[1], Fortran2003.Name):
        get_name_or_defer(stmt, node.items[1], res_value)
    else:
        defer(stmt, node.items[1])

def search_Char_Literal_Constant(stmt, node, gentype=None): 
    if node.items[1]:
        get_name_or_defer(stmt, Fortran2003.Name(node.items[1]), res_typedecl)
    #get_name_or_defer(stmt, node.items[0], res_typedecl)

def search_Length_Selector(stmt, node, gentype=None): 
    for item in node.items:
        get_name_or_defer(stmt, item, res_value)

def search_Type_Param_Value(stmt, node, gentype=None): 
    # NOTE: need to verify its content structure
    if node.item:
        get_name_or_defer(stmt, node.item, res_value)

def search_Write_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Read_Stmt(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Io_Control_Spec(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Stop_Stmt(stmt, node, gentype=None): 
    pass

def search_Contains_Stmt(stmt, node, gentype=None): 
    pass

def search_Subscript_Triplet(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value) 
    get_name_or_defer(stmt, node.items[1], res_value) 
    get_name_or_defer(stmt, node.items[2], res_value) 

def search_Interface_Stmt(stmt, node, gentype=None):
    pass

def search_Procedure_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_subprogram)

def search_Prefix(stmt, node, gentype=None):
    for item in node.items:
        get_name_or_defer(stmt, node.items[0], res_anything)

def search_Prefix_Spec(stmt, node, gentype=None):
    if node.item or hasattr(node, 'items'):
        raise ProgramException('Unexpected item or items attr')

def search_Logical_Literal_Constant(stmt, node, gentype=None):
    if node.items[1]:
        get_name_or_defer(stmt, Fortran2003.Name(node.items[1]), res_typedecl)
    #get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Access_Spec(stmt, node, gentype=None):
    pass

def search_And_Operand(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Equiv_Operand(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Or_Operand(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Where_Construct_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)

def search_Elsewhere_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Suffix(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Declaration_Type_Spec(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_derivedtype)

def search_Data_Ref(stmt, node, gentype=None):
    from kgen_utils import KGName
    from Fortran2003 import Name, Part_Ref

    # NOTE: to limit the scope of data saving in derived type,
    #       the last part_ref would be the one that has gentype=gentype
    if isinstance(node.items[0], Name):
        get_name_or_defer(stmt, node.items[0], res_typestmt, gentype=gentype)
    elif isinstance(node.items[0], Part_Ref):
        get_name_or_defer(stmt, node.items[0].items[0], res_typestmt, gentype=gentype) 
        get_name_or_defer(stmt, node.items[0].items[1], res_value) 

    for item in node.items[1:]:
        if isinstance(item, Name): pass
        elif isinstance(item, Part_Ref):
            get_name_or_defer(stmt, item.items[1], res_value)
        elif item is None: pass
        else: raise ProgramException('Unknown type: %s'%item.__class)

def search_Structure_Constructor(stmt, node, gentype=None):
    #get_name_or_defer(stmt, node.items[0], res_derivedtype)
    # NOTE: parser found ordinary subprogram as Structure_Constructor
    get_name_or_defer(stmt, node.items[0], res_value + res_derivedtype)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Binary_Constant(stmt, node, gentype=None):
    pass

def search_Octal_Constant(stmt, node, gentype=None):
    pass

def search_Hex_Constant(stmt, node, gentype=None):
    pass

def search_Intrinsic_Stmt(stmt, node, gentype=None):
    pass
    #get_name_or_defer(stmt, node.items[1], res_subprogram)

def search_Derived_Type_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Access_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_anything)

def search_Function_Reference(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_function)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Return_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_function)

def search_Print_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Format(stmt, node, gentype=None):
    if hasattr(node, 'items') and len(node.items)>0:
        get_name_or_defer(stmt, node.items[0], res_value)

def search_Implicit_Stmt(stmt, node, gentype=None):
    if hasattr(node, 'items') and len(node.items)>0:
        get_name_or_defer(stmt, node.items[0], res_value)

def search_Exit_Stmt(stmt, node, gentype=None):
    pass

def search_Pointer_Assignment_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_ptr_object) # data pointer obj or procedure pointer obj
    get_name_or_defer(stmt, node.items[2], res_target) # data target or procedure target

def search_Proc_Component_Ref(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value, gentype=gentype)
    # Type definition may handle a procedure component name?
    #get_name_or_defer(stmt, node.items[2], res_value)

def search_Io_Unit(stmt, node, gentype=None):
    if hasattr(node, 'items') and len(node.items)>0:
        get_name_or_defer(stmt, node.items[0], res_value)

def search_Level_3_Expr(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Open_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Connect_Spec(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Endfile_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Position_Spec(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Close_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Close_Spec(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Label(stmt, node, gentype=None):
    pass

def search_Io_Implied_Do(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Io_Implied_Do_Control(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_typedecl, gentype=KGGenType.STATE_OUT)
    get_name_or_defer(stmt, node.items[1], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)
    get_name_or_defer(stmt, node.items[3], res_value)

def search_Format_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    # No need for searching format-items?
    #get_name_or_defer(stmt, node.items[1], res_value)

def search_Format_Specification(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Format_Item_C1002(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Control_Edit_Desc(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Format_Item(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Alloc_Opt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Deallocate_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Cycle_Stmt(stmt, node, gentype=None):
    pass

def search_External_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], \
        [ TypeDeclarationStatement, Function, Subroutine ])

def search_Case_Value_Range(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Forall_Construct_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Forall_Header(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Forall_Triplet_Spec(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)
    get_name_or_defer(stmt, node.items[3], res_value)

def search_Goto_Stmt(stmt, node, gentype=None):
    pass

def search_Continue_Stmt(stmt, node, gentype=None):
    pass

def search_Wait_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Wait_Spec(stmt, node, gentype=None):
    if hasattr(node, 'items') and len(node.items)>0:
        for item in node.items:
            get_name_or_defer(stmt, item, res_value)

def search_Rewind_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Flush_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Import_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_anything)

def search_Block_Data_Stmt(stmt, node, gentype=None):
    # NOTE: Temporary solution
    pass

def search_Data_Stmt(stmt, node, gentype=None):
    if hasattr(node, 'items') and len(node.items)>0:
        for item in node.items:
            get_name_or_defer(stmt, item, res_typedecl)

def search_Data_Stmt_Value(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_typedecl)
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Save_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Asynchronous_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Allocatable_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Common_Stmt(stmt, node, gentype=None):
    if hasattr(node, 'items') and len(node.items)>0:
        for itemlist in node.items:
            for name, _item in itemlist:
                get_name_or_defer(stmt, _item, res_value)

def search_Data_Stmt_Set(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Dimension_Stmt(stmt, node, gentype=None):
    if hasattr(node, 'items') and len(node.items)>0:
        for itemlist in node.items:
            for name, _item in itemlist:
                get_name_or_defer(stmt, _item, res_value)

def search_Equivalence_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Equivalence_Set(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_typedecl)
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Intent_Stmt(stmt, node, gentype=None):
    #get_name_or_defer(stmt, node.items[0], res_typedecl)
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Intent_Spec(stmt, node, gentype=None):
    pass

def search_Namelist_Stmt(stmt, node, gentype=None):
    if hasattr(node, 'items') and len(node.items)>0:
        for nlname, nlgroup in node.items:
            get_name_or_defer(stmt, nlgroup, res_typedecl)

def search_Optional_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Pointer_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_anything)

def search_Protected_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Target_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_anything)

def search_Target_Entity_Decl(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_anything)
    defer(stmt, node.items[1])
    get_name_or_defer(stmt, node.items[2], res_value)
    get_name_or_defer(stmt, node.items[3], res_value) 

def search_Volatile_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_anything)

def search_Value_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_typedecl)

def search_Backspace_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Forall_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Inquire_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Inquire_Spec(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Nullify_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Where_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Arithmetic_If_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)
    get_name_or_defer(stmt, node.items[3], res_value)

def search_Computed_Goto_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Actual_Arg_Spec(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Data_Pointer_Object(stmt, node, gentype=None):
    from Fortran2003 import Name

    get_name_or_defer(stmt, node.items[0], res_value, gentype=gentype)

    if node.items[2] and not isinstance(node.items[2], Name):
        get_name_or_defer(stmt, node.items[2], res_value)

def search_Type_Attr_Spec(stmt, node, gentype=None):
    if isinstance(node.items[0], str) and node.items[0]=='EXTENDS':
        get_name_or_defer(stmt, node.items[1], res_derivedtype)
    else:
        get_name_or_defer(stmt, node.items[0], res_value)
        get_name_or_defer(stmt, node.items[1], res_value)

def search_Level_5_Expr(stmt, node, gentype=None):
        get_name_or_defer(stmt, node.items[0], res_value)
        get_name_or_defer(stmt, node.items[2], res_value)

def search_Parameter_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)
   
def search_Named_Constant_Def(stmt, node, gentype=None): 
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Saved_Entity(stmt, node, gentype=None):
    if len(node.items)==3 and node.items[0]=='/' and node.items[2]=='/':
        get_name_or_defer(stmt, node.items[1], res_common)
    else:
        for item in node.items:
            get_name_or_defer(stmt, item, res_value)

def search_Alloc_Opt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Dealloc_Opt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Level_5_Expr(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Generic_Spec(stmt, node, gentype=None):
    pass

def search_Assumed_Size_Spec(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Common_Block_Object(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Ac_Implied_Do(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Ac_Implied_Do_Control(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value, gentype=KGGenType.STATE_OUT)
    if node.items[1]:
        for item in node.items[1]:
            get_name_or_defer(stmt, item, res_value)

def search_Specific_Binding(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_typespec + [ Interface ])
    get_name_or_defer(stmt, node.items[1], res_value)
    if node.items[3] is None:
        get_name_or_defer(stmt, node.items[2], res_subprogram)
    else:
        get_name_or_defer(stmt, node.items[3], res_subprogram)

def search_Binding_Attr(stmt, node, gentype=None):
    pass

def search_Masked_Elsewhere_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)

def search_Procedure_Designator(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)

def search_Associate_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Association(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[2], res_value)

def search_Generic_Binding(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[2], [ Fortran2003.Specific_Binding ])

def search_Complex_Literal_Constant(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Char_Length(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Data_Implied_Do(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_value)
    get_name_or_defer(stmt, node.items[1], res_value, gentype=KGGenType.STATE_OUT)
    get_name_or_defer(stmt, node.items[2], res_value)
    get_name_or_defer(stmt, node.items[3], res_value)
    get_name_or_defer(stmt, node.items[4], res_value)

def search_Ac_Spec(stmt, node, gentype=None):
    defer(stmt, node.items[0])
    get_name_or_defer(stmt, node.items[1], res_value)

def search_Sequence_Stmt(stmt, node, gentype=None):
    pass

def search_Stmt_Function_Stmt(stmt, node, gentype=None):
    get_name_or_defer(stmt, node.items[0], res_typedecl)
    #show_tree(node)
    #import pdb ;pdb.set_trace()
    pass
