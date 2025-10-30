"""
This module contains utilities for converting between XML and JSON representations of DICOM data.

This module provides functions for converting DICOM data between XML and JSON formats
according to the DICOM Part 18 specification. It handles standard DICOM data elements,
sequences, person names, and bulk data references.

Reference: https://dicom.nema.org/medical/dicom/current/output/chtml/part18/sect_F.3.html#table_F.3.1-1
"""
from typing import Dict, List, Optional, Union, Any
from xml.etree.ElementTree import Element
from pydicom._dicom_dict import DicomDictionary


def xml_to_json_pn(name: Element) -> Dict[str, str]:
    """
        Convert XML Person Name element to JSON format.
        
        Converts a DICOM Person Name (PN) element from XML representation
        to JSON format, handling Alphabetic, Ideographic, and Phonetic
        name components.
        
        Args:
            name (Element): XML Element containing Person Name data.
            
        Returns:
            Dict[str, str]: Dictionary with name types as keys and
                           formatted name strings as values.
                           
        Note:
            Name components are joined with '^' separators according
            to DICOM PN formatting rules.
    """
    temp = {}
    name_types = ["Alphabetic", "Ideographic", "Phonetic"]

    name_components = ["FamilyName", "GivenName", "MiddleName", "NamePrefix", "NameSuffix"]  # noqa

    for name_type in name_types:
        name_str = ""
        name_type_comp = name.find(name_type)
        if name_type_comp is None:
            continue

        for name_component in name_components:
            elem = name_type_comp.find(name_component)
            if elem and elem.text:
                name_str = name_str + elem.text
            name_str = name_str + "^"
        # subelement

        temp[name_type] = name_str

    return temp


def json_to_xml_pn(name: Dict[str, str], item_number: int) -> Element:
    """
        Convert JSON Person Name data to XML Element format.
        
        Converts a DICOM Person Name from JSON representation to XML format,
        creating proper XML structure with name type elements and components.
        
        Args:
            name (Dict[str, str]): Dictionary containing name data with
                                  name types as keys.
            item_number (int): Item number for the XML element attribute.
            
        Returns:
            Element: XML Element representing the Person Name with proper
                    structure and attributes.
    """

    name_types = ["Alphabetic", "Ideographic", "Phonetic"]

    name_components = ["FamilyName", "GivenName", "MiddleName", "NamePrefix", "NameSuffix"]  # noqa

    name_element = Element("PersonName", attrib={'number': str(item_number)})

    for name_type in name_types:

        name_str = ""
        try:
            name_str = name[name_type]
        except KeyError:
            continue

        name_type_element = Element(name_type)

        name_split = name_str.split("^")
        name_split.extend([""]*(5-len(name_split)))

        for name_comp, name_comp_type in zip(name_split, name_components):
            if name_comp != "":
                name_comp_element = Element(name_comp_type)
                name_comp_element.text = name_comp
                name_type_element.append(name_comp_element)

        name_element.append(name_type_element)
    return name_element


def xml_to_json(dataset: Element) -> Dict[str, Dict]:
    """
        Convert XML DICOM dataset to JSON format.
        
        Converts a DICOM dataset from XML representation to JSON format
        according to DICOM Part 18 specification. Handles all standard
        DICOM data types including sequences, person names, and bulk data.
        
        Args:
            dataset (Element): XML Element containing DICOM dataset.
            
        Returns:
            Dict[str, Dict]: Dictionary representation of the DICOM dataset
                           with tags as keys and value/VR dictionaries as values.
    """

    ds : Dict[str,Dict] = {}
    for element in dataset:
        tag = element.attrib['tag']
        vr = element.attrib['vr']
        value: Optional[Union[List[Any], str]]

        if vr == 'SQ':
            value = [
                xml_to_json(item)
                for item in element
            ]

        else:

            children = list(element)

            if len(children) == 1:
                child = children[0]
                if child.tag == "BulkDataURI":
                    #
                    ds[tag] = {'vr': vr, 'BulkDataURI': child.attrib["uri"]}
                    continue

                elif child.tag == "InlineBinary" and child.text:
                    #
                    ds[tag] = {'vr': vr, 'InlineBinary': child.text}
                    continue

            if len(children) >= 1:
                if vr == "PN":
                    value = [xml_to_json_pn(v) for v in children]
                else:
                    value =[]
                    for v in children:
                        if v and v.text:
                            value.append(v.text.strip())

            else:
                value = None

        ds[tag] = {'vr': vr, 'Value': value}

    return ds

def wadl_xml_to_json(dataset: Element) -> Dict[str, Dict]:
    """
        Convert WADL XML DICOM dataset to JSON format.
        
        Similar to xml_to_json but specifically designed for WADL (Web Application
        Description Language) formatted XML. Currently implements the same logic
        as the standard XML to JSON converter.
        
        Args:
            dataset (Element): XML Element containing DICOM dataset in WADL format.
            
        Returns:
            Dict[str, Dict]: Dictionary representation of the DICOM dataset
                           with tags as keys and value/VR dictionaries as values.
    """

    ds : Dict[str,Dict] = {}
    for element in dataset:
        tag = element.attrib['tag']
        vr = element.attrib['vr']
        value: Optional[Union[List[Any], str]]

        if vr == 'SQ':
            value = [
                xml_to_json(item)
                for item in element
            ]

        else:

            children = list(element)

            if len(children) == 1:
                child = children[0]
                if child.tag == "BulkDataURI":
                    #
                    ds[tag] = {'vr': vr, 'BulkDataURI': child.attrib["uri"]}
                    continue

                elif child.tag == "InlineBinary" and child.text:
                    #
                    ds[tag] = {'vr': vr, 'InlineBinary': child.text}
                    continue

            if len(children) >= 1:
                if vr == "PN":
                    value = [xml_to_json_pn(v) for v in children]
                else:
                    value =[]
                    for v in children:
                        if v and v.text:
                            value.append(v.text.strip())

            else:
                value = None

        ds[tag] = {'vr': vr, 'Value': value}

    return ds


def json_to_xml(dataset: Dict[str, Dict], item_level : bool = False) -> Element:
    """
        Convert JSON DICOM dataset to XML format.
        
        Converts a DICOM dataset from JSON representation to XML format
        according to DICOM Part 18 specification. Creates proper XML
        structure with DicomAttribute elements and handles all DICOM data types.
        
        Args:
            dataset (Dict[str, Dict]): Dictionary containing DICOM dataset
                                     with tags as keys.
            item_level (bool, optional): If True, creates an Item element
                                        instead of NativeDicomModel. Defaults to False.
                                        
        Returns:
            Element: XML Element representing the DICOM dataset with proper
                    structure and attributes.
    """

    ds = None
    if item_level:
        ds = Element("Item")
    else:
        ds = Element("NativeDicomModel")

    for tag in dataset:


        elem = dataset[tag]
        vr = elem['vr']


        keyword = None
        attribs = {}
        try:
            keyword = DicomDictionary[int(tag, 16)]
            attribs = {"tag": tag, "vr": vr, "keyword": keyword[-1]}

        except KeyError:
            attribs = {"tag": tag, "vr": vr}

        dcm_attrib = Element("DicomAttribute", attrib=attribs)

        if "BulkDataURI" in elem.keys():
            item_elem = Element("BulkdataURI", uri=elem["BulkdataURI"])
            item_elem = Element("BulkdataURI", uri=elem["BulkdataURI"])
            dcm_attrib.append(item_elem)
            continue

        elif "InlineBinary" in elem.keys():
            item_elem = Element("InlineBinary")
            item_elem.text = elem["InlineBinary"]
            dcm_attrib.append(item_elem)
            continue

        values = elem['Value']

        for (cc, value) in enumerate(values):

            if vr == 'SQ':

                item_elem = json_to_xml(value, True)
                item_elem.set('number', str(cc))

            elif vr == 'PN':
                item_elem = json_to_xml_pn(value, cc)
                #ds.append(item_elem)
            else:
                item_elem = Element("Value", number=str(cc))
                item_elem.text = str(value)
                #ds.append(item_elem)

            dcm_attrib.append(item_elem)

        ds.append(dcm_attrib)

    return ds
