"""
Generate capabilitiues statement from OpenAPI docs.
This is has been hastedly put together and will be cleanup in the future.
"""

from xml.etree.ElementTree import Element
import xml.etree.ElementTree
from typing import List, Dict, Any
import json
import prance

class treeNode(object):
    """
        Class to build/hold a tree representation of all the path objects
        before building the xml or json document.
    """

    def __init__(self,path : str) -> None:
        """
            Constructor
        Args:
            path (str): Part of path
        """
        self.path = path
        self.leaf_data : Dict [Any, Any] | None = None
        self.children : Dict[str, treeNode] = {}

    def set_leaf_data(self,data: Dict[Any,Any])->None:
        """ Add JSON data for leaf node.

        Args:
            data (Dict[Any,Any]): Json data for leaf node
        """
        self.leaf_data = data

    def propogate_path(self,path_list : List[str], open_api_json : Dict[Any, Any]) -> None:
        """ Recursively generate the tree datastructure for path.

        Args:
            path_list (List[str]): List of path components
            open_api_json (Dict[Any, Any]): open api path component
        """
        child_path = path_list.pop(0)

        cn = None
        if child_path not in self.children:
            cn = treeNode(child_path)
            self.children[child_path] = cn
        else:
            cn = self.children[child_path]

        if len(path_list) != 0:
            cn.propogate_path(path_list,open_api_json)
        else:
            cn.set_leaf_data(open_api_json)

    def is_leaf(self) -> bool:
        """ Returns whether this is a leaf node or not

        Returns:
            bool: True if this is a leaf node
        """
        return len(self.children.keys()) == 0

def _build_path_xml(path: Dict[Any,Any]) -> Element:
    """
        Generate WADL XML component for openapi path.
    Args:
        path (Dict[Any,Any]): openapi JSON for this path component.

    Returns:
        Element: WADL XML component for path
    """

    http_method = list(path.keys())[0]
    ## method
    method = Element("method",{"name":http_method.upper(),"id":""})

    ## request
    request = Element("request")
    method.append(request)

    ## reps

    if "requestBody" in path[http_method]:

        for rep_type in path[http_method]["requestBody"]["content"]:
            rt = Element("representation",{"mediaType":rep_type})
            request.append(rt)
    ##params


    try:
        for param in path[http_method]["parameters"]:
    ##
            if param["in"] == "path":
                continue
            pp = Element("param",{"name":param["name"],"style":param["in"]})
            request.append(pp)
    except KeyError:
        pass

    if "501" in path[http_method]["responses"].keys():
        re = Element("response",{"status":"501"})
        method.append(re)
    else:
        ## responses
        for rr, resp in path[http_method]["responses"].items():
            # resp param
            #
            re = Element("response",{"status":rr})


            for cc in resp["content"]:
                ce = Element("representation",{"mediaType":cc})
                re.append(ce)

            method.append(re)

    return method

def _build_path_json(path: Dict[Any,Any]) -> Dict[Any,Any]:
    """
        Generate JSON component for openapi path.

    Args:
        path (Dict[Any,Any]): Openapi path

    Returns:

        Dict[Any,Any]: Json component of path
    """

    http_method = list(path.keys())[0]
    ## method
    method = {"@name":http_method.upper(),"@id":""}

    ## request
    request : Dict[Any, Any] = {}
    method["request"] = request
    method["response"] = []
    ## reps

    if "requestBody" in path[http_method]:

        for rep_type in path[http_method]["requestBody"]["content"]:
            rt = {"@mediaType":rep_type}
            if "representation" not in method["request"].keys():
                request["representation"] = []
            request["representation"].append(rt)
    ##params


    try:
        for param in path[http_method]["parameters"]:
    ##
            if param["in"] == "path":
                continue
            if "param" not in method["request"].keys():
                request["param"] = []
            pp = {"@name":param["name"],"@style":param["in"]}
            request["param"].append(pp)
    except KeyError:
        pass

    if "501" in path[http_method]["responses"].keys():
        re : Dict[Any, Any]= {"@status":"501"}
        method["response"].append(re)
    else:
        ## responses
        for rr, resp in path[http_method]["responses"].items():
            # resp param
            #
            re = {"@status":rr}

            for cc in resp["content"]:
                ce = {"@mediaType":cc}
                if "representation" not in re:
                    re["representation"] = []
                re["representation"].append(ce)
            method["response"].append(re)

    return method

def build_capabilities_xml(openapi_json : str, base_url : str) -> str:
    """_summary_

    Args:
        openapi_json (Dict[Any,Any]): _description_
        base_url (str): _description_

    Returns:
        str: _description_
    """
    parser = prance.ResolvingParser(spec_string=openapi_json)

    root_attrs= {}
    root_attrs["xsi:schemaLocation"]="http://wadl.dev.java.net/2009/02 wadl.xsd"
    root_attrs["xmlns:xsd"]="http://www.w3.org/2001/XMLSchema"
    root_attrs["xmlns"]="http://wadl.dev.java.net/2009/02"

    root = Element("application",root_attrs)
    resources = Element("resources",{"base":base_url})
    root.append(resources)

    root_node = treeNode('root')

    ## build a tree out of the paths
    for pk, path in parser.specification['paths'].items():

        if pk == '/':
            continue

        path_list = pk.split('/')
        #print (path_list)

        root_node.propogate_path(path_list[1:],path)


    def generate_spec(root_node : treeNode) -> Element:
        resource = Element("resource",{"path":root_node.path})

        for cp,cn in root_node.children.items():
        ##


            if cn.is_leaf() and cn.leaf_data:
                xml_resource = _build_path_xml(cn.leaf_data)
                resource.append(xml_resource)
            else:
                resource.append(generate_spec(cn))
        return resource

    for cp,cn in root_node.children.items():

        resources.append(generate_spec(cn))

    xml.etree.ElementTree.indent(root)
    temp =  xml.etree.ElementTree.tostring(root, encoding='unicode')
    return temp

def build_capabilities_json(openapi_json : str, base_url : str) -> str:
    """_summary_

    Args:
        openapi_json (Dict[Any, Any]): _description_
        base_url (str): _description_

    Returns:
        str: _description_
    """
    parser = prance.ResolvingParser(spec_string=openapi_json)



    #root = Element("application",root_attrs)

    resources : Dict[Any,Any]= {}
    root = {"@application":resources}
    resources["@base"] = base_url
    resource_ :List[Any]= []
    resources["resource"] = resource_
    root["resources"]= resources

    root_node = treeNode('root')

    ## build a tree out of the paths
    for pk, path in parser.specification['paths'].items():

        if pk == '/':
            continue

        path_list = pk.split('/')
        #print (path_list)

        root_node.propogate_path(path_list[1:],path)

    def generate_spec(root_node : treeNode) -> Dict[Any,Any]:
        resource : Dict [Any, Any]= {"@path":root_node.path}

        for cp,cn in root_node.children.items():
        ##


            if cn.is_leaf() and cn.leaf_data:
                json_resource = _build_path_json(cn.leaf_data)
                if "method" not in resource:
                    resource["method"] = []

                resource["method"].append(json_resource)
            else:
                if "resource" not in resource:
                    resource["resource"] = []

                resource["resource"].append(generate_spec(cn))
        return resource

    for cp,cn in root_node.children.items():

        resource_.append(generate_spec(cn))

    return json.dumps(root)
