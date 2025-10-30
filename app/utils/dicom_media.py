"""
This module contains utilities for handling DICOM media types and multipart messages.

This module provides classes and functions for parsing, creating, and managing
DICOM content in various formats including DICOM binary, JSON, XML, images,
and multipart MIME messages used in DICOMweb communications.
"""

import enum
from typing import List, Dict, Any, Tuple
import random
import string
from io import BytesIO
from abc import ABC,abstractmethod
import logging
import pydicom


logger = logging.getLogger(__name__)


class DicomMediaType(enum.Enum):
    """
        Enumeration of supported DICOM media types.

        This enum defines the various content types that can be handled
        in DICOM communications, including different serialization formats
        and encapsulated content types.

        Note:
            This is not strictly MIME types and may need naming adjustments.
    """
    ANY = 0
    DICOM = 1
    DICOM_JSON = 2
    DICOM_XML = 3
    DICOM_IMAGE = 4
    DICOM_VIDEO = 5
    DICOM_DOCUMENT = 6
    BYTES = 7
    MULTIPART = 8
    JSON=9
    WADL=10


# DicomMediaType encapsulated content types:
# PDF  application/pdf
# CDA  text/XML
# STL  model/stl
# OBJ  model/obj
# MTL  model/mtl

def transfer_syntax_to_media_type_images(transfer_syntax: str) -> str:
    """
        Convert DICOM transfer syntax UID to corresponding media type.

        Maps DICOM transfer syntax UIDs to their appropriate MIME media types
        for image content. Used for determining how to handle compressed image data.

        Args:
            transfer_syntax (str): DICOM transfer syntax UID.

        Returns:
            str: Corresponding MIME media type string.

        Raises:
            KeyError: If the transfer syntax is not supported.
    """

    ts = {}

    ts["1.2.840.10008.1.2.4.70"] = "image/jpeg"
    ts["1.2.840.10008.1.2.4.50"] = "image/jpeg"
    ts["1.2.840.10008.1.2.4.51"] = "image/jpeg"
    ts["1.2.840.10008.1.2.4.57"] = "image/jpeg"
    ts["1.2.840.10008.1.2.8.1"] = "application/x-deflate"
    ts["1.2.840.10008.1.2.5"] = "image/dicom-rle"
    ts["1.2.840.10008.1.2.4.80"] = "image/jls"
    ts["1.2.840.10008.1.2.4.81"] = "image/jls"
    ts["1.2.840.10008.1.2.4.90"] = "image/jp2"
    ts["1.2.840.10008.1.2.4.91"] = "image/jp2"
    ts["1.2.840.10008.1.2.4.92"] = "image/jpx"
    ts["1.2.840.10008.1.2.4.93"] = "image/jpx"
    ts["1.2.840.10008.1.2.4.201"] = "image/jphc"
    ts["1.2.840.10008.1.2.4.202"] = "image/jphc"
    ts["1.2.840.10008.1.2.4.203"] = "image/jphc"
    ts["1.2.840.10008.1.2.4.110"] = "image/jxl"
    ts["1.2.840.10008.1.2.4.111"] = "image/jxl"
    ts["1.2.840.10008.1.2.4.112"] = "image/jxl"

    return ts[transfer_syntax]


class DicomMediaPart(ABC):
    """
        Abstract base class for DICOM media parts.

        Represents a single part in a multipart DICOM message, containing
        data and associated headers. Subclasses implement specific content
        types like DICOM binary, JSON, XML, images, etc.
    """

    def __init__(self, data: Any, headers: Dict | None = None):
        """
            Initialize a DICOM media part.

            Args:
                data (Any): The content data for this part.
                headers (Dict, optional): HTTP headers associated with this part.
        """
        self.headers = headers if headers else {}
        self.data = data

    @abstractmethod
    def content_type(self) -> DicomMediaType:
        """
            Get the DICOM media type for this part.

            Returns:
                DicomMediaType: The media type enum value.
        """

    @abstractmethod
    def content_type_str(self) -> str:
        """
            Get the MIME content type string for this part.

            Returns:
                str: MIME content type string for HTTP headers.
        """

    @abstractmethod
    def to_bytes(self) ->bytes:
        """
            Convert this part to raw bytes.

            Returns:
                bytes: Raw binary data.
        """

class DicomMediaPartBytes(DicomMediaPart):
    """
        DICOM media part for raw byte data.

        Represents binary data content that doesn't fit into other specific
        DICOM content types. Uses application/octet-stream MIME type.
    """

    def __init__(self, data: bytes,  headers: Dict | None = None):
        """
            Initialize a bytes media part.

            Args:
                data (bytes): Raw binary data.
                headers (Dict, optional): HTTP headers for this part.
        """
        super().__init__(data,headers)

    def to_bytes(self) ->bytes:
        """Return the raw byte data."""
        return self.data

    def content_type_str(self) -> str:
        """Return the MIME content type for binary data."""
        return 'application/octet-stream; transfer-syntax=1.2.840.10008.1.2.1'

    def content_type(self) -> DicomMediaType:
        """Return the DICOM media type enum value."""
        return DicomMediaType.BYTES


class DicomMediaPartDICOMImage(DicomMediaPart):
    """
        DICOM media part for encapsulated image data.

        Represents compressed image data that is encapsulated within DICOM,
        such as JPEG, JPEG 2000, RLE, etc. Maintains the original transfer syntax
        and content type information.
    """

    def __init__(self, data: bytes, content_type: str,
                 transfer_syntax: str | None= None, headers: Dict | None = None):
        """
            Initialize an encapsulated image media part.

            Args:
                data (bytes): Compressed image data.
                content_type (str): MIME content type for the image.
                transfer_syntax (str, optional): DICOM transfer syntax UID.
                headers (Dict, optional): HTTP headers for this part.
        """
        super().__init__(data,headers)
        self.data = data
        self.ct_str = content_type
        self.transfer_syntax_str = transfer_syntax

    def to_bytes(self) -> bytes:
        """Return the compressed image data."""
        return self.data

    def content_type_str(self) -> str:
        """Return the MIME content type for the image."""
        return self.ct_str

    def transfer_syntax(self) -> str|None:
        """Return the DICOM transfer syntax UID."""
        return self.transfer_syntax_str

    def content_type(self) -> DicomMediaType:
        """Return the DICOM media type enum value."""
        return DicomMediaType.DICOM_IMAGE


class DicomMediaPartDocument(DicomMediaPart):
    """
        DICOM media part for encapsulated document data.

        Represents document content encapsulated within DICOM, such as
        PDF files, CDA documents, STL models, etc.
    """

    def __init__(self, data: bytes, content_type: str, headers: Dict | None= None):
        """
            Initialize an encapsulated document media part.

            Args:
                data (bytes): Document data.
                content_type (str): MIME content type for the document.
                headers (Dict, optional): HTTP headers for this part.
        """
        super().__init__(data,headers)
        self.data = data
        self.ct_str = content_type

    def to_bytes(self) -> bytes:
        """Return the document data."""
        return self.data

    def content_type_str(self) -> str:
        """Return the MIME content type for the document."""
        return self.ct_str

    #def transfer_syntax(self) -> str:
    #    """Return the DICOM transfer syntax UID."""
    #    return pydicom.uid.ExplicitVRLittleEndian

    def content_type(self) -> DicomMediaType:
        """Return the DICOM media type enum value."""
        return DicomMediaType.DICOM_DOCUMENT


class DicomMediaPartJSON(DicomMediaPart):
    """
        DICOM media part for JSON-formatted DICOM data.

        Represents DICOM data serialized in JSON format according to
        the DICOM JSON specification (PS3.18).
    """

    def __init__(self,  data: str, headers: Dict | None= None):
        """
            Initialize a DICOM JSON media part.

            Args:
                data (str): DICOM data in JSON format.
                headers (Dict, optional): HTTP headers for this part.
        """
        super().__init__(data,headers)
        self.data = data

    def to_bytes(self) -> bytes:
        """Return the JSON data encoded as UTF-8 bytes."""
        return self.data.encode('utf-8')

    def content_type_str(self) -> str:
        """Return the MIME content type for DICOM JSON."""
        return 'application/dicom+json'

    def content_type(self) -> DicomMediaType:
        """Return the DICOM media type enum value."""
        return DicomMediaType.DICOM_JSON


class DicomMediaPartXML(DicomMediaPart):
    """
        DICOM media part for XML-formatted DICOM data.

        Represents DICOM data serialized in XML format according to
        the DICOM XML specification (PS3.19).
    """

    def __init__(self, data: str, headers: Dict | None = None):
        """
            Initialize a DICOM XML media part.

            Args:
                data (str): DICOM data in XML format.
                headers (Dict, optional): HTTP headers for this part.
        """
        super().__init__(data,headers)
        self.data = data

    def to_bytes(self) -> bytes:
        """Return the XML data encoded as UTF-8 bytes."""
        return self.data.encode('utf-8')

    def content_type_str(self) -> str:
        """Return the MIME content type for DICOM XML."""
        return 'application/dicom+xml'

    def content_type(self) -> DicomMediaType:
        """Return the DICOM media type enum value."""
        return DicomMediaType.DICOM_XML


class DicomMediaPartDICOM(DicomMediaPart):
    """
        DICOM media part for binary DICOM data.

        Represents DICOM data in its native binary format, using pydicom
        FileDataset objects for manipulation and serialization.
    """

    def __init__(self, data: pydicom.FileDataset | None, headers: Dict | None= None):
        """
            Initialize a DICOM binary media part.

            Args:
                data (pydicom.FileDataset | None): DICOM dataset object or None if invalid.
                headers (Dict, optional): HTTP headers for this part.
        """
        super().__init__(data,headers)
        self.data = data

    def to_bytes(self) -> bytes:
        """
            Serialize the DICOM dataset to bytes.

            Uses pydicom to write the dataset to a memory buffer and return
            the binary DICOM data.

            Returns:
                bytes: DICOM data in binary format.
        """
        with BytesIO() as buffer:
            # create a DicomFileLike object that has some properties of DataSet
            memory_dataset = pydicom.filebase.DicomFileLike(buffer)
            # write the dataset to the DicomFileLike object
            # will need to write with specific charset.

            pydicom.dcmwrite(memory_dataset, self.data,  enforce_file_format=True)
            # to read from the object, you have to rewind it
            memory_dataset.seek(0)
            # read the contents as bytes
            return memory_dataset.read()

    def content_type_str(self) -> str:
        """Return the MIME content type for DICOM binary."""
        return 'application/dicom'

    def content_type(self) -> DicomMediaType:
        """Return the DICOM media type enum value."""
        return DicomMediaType.DICOM


class DicomMediaMultipartMessage:
    """
        Container for multipart DICOM messages.

        Manages multiple DICOM media parts that can be serialized into
        a multipart MIME message format for DICOMweb communications.
    """

    def __init__(self) -> None:
        """
            Initialize an empty multipart message.

            Creates an empty message with no parts and no boundary set.
        """
        self.parts : List [DicomMediaPart]= []
        self.boundary : str | None = None

    def to_bytes(self) -> bytes:
        """
            Serialize the multipart message to bytes.

            Generates a multipart MIME message with random boundary
            and serializes all parts with appropriate headers.

            Returns:
                bytes: Complete multipart MIME message as bytes.
        """

        self.boundary = ''.join(random.choices(
            string.ascii_letters + string.digits, k=40))

        buffer = b""
        for part in self.parts:

            buffer = buffer+ bytearray('--'+self.boundary + '\r\n', encoding='utf-8')
            header = "Content-Location: "  + part.headers["Content-Location"]
#            for hh in part.headers[1:]:

 #               header += "\n"+hh+": "+part.headers[hh]

            header += "\nContent-Type: "+part.content_type_str()
            #header += "\nContent-Type: "+part.content_type_str()

            header = header + "\r\n\r\n"
            buffer = buffer + header.encode('UTF-8')
            buffer = buffer+part.to_bytes()
            buffer = buffer + bytearray('\r\n', encoding='utf-8')
            # generate a 40byte
        buffer = buffer+bytearray(
            '--'+self.boundary + '--\r\n', encoding='utf-8')

        return bytes(buffer)


class DicomMediaSinglepartParser:
    """
        Parser for single-part DICOM messages.

        Parses HTTP message bodies containing single DICOM content types
        like DICOM binary, JSON, or XML and converts them to DicomMediaPart objects.
    """

    def __init__(self, content_type: DicomMediaType, transfer_syntax_uid: str):
        """
            Initialize the single-part parser.

            Args:
                content_type (DicomMediaType): Expected content type of the message.
                transfer_syntax_uid (str): DICOM transfer syntax UID.
        """
        self.content_type = content_type
        self.transfer_syntax_uid = transfer_syntax_uid

    def parse_body(self, body: bytes) -> List[DicomMediaPart]:
        """
            Parse a single-part message body.

            Converts the raw message body into appropriate DicomMediaPart objects
            based on the configured content type.

            Args:
                body (bytes): Raw message body bytes.

            Returns:
                List[DicomMediaPart]: List containing the parsed media part.
        """

        parts : List[DicomMediaPart]= []

        if self.content_type == DicomMediaType.DICOM:
            try:
                ds = pydicom.dcmread(BytesIO(body))
                parts.append(DicomMediaPartDICOM(ds, None))
            except pydicom.errors.InvalidDicomError:
                parts.append(DicomMediaPartDICOM(None, None))

        elif self.content_type == DicomMediaType.DICOM_JSON:
            parts.append(DicomMediaPartJSON(body.decode('utf-8'), None)) # need charset

        elif self.content_type == DicomMediaType.DICOM_XML:
            parts.append(DicomMediaPartXML(body.decode('utf-8'), None)) # need charset

        return parts


class DicomMediaMultipartParser:
    """
        Parser for multipart DICOM messages.

        Parses HTTP message bodies containing multipart MIME content with
        multiple DICOM parts separated by boundaries.
    """

    def __init__(self, boundary: str):
        """
            Initialize the multipart parser.

            Args:
                boundary (str): MIME boundary string used to separate parts.
        """
        self.boundary = boundary

    def parse_body(self, body: bytes) -> List[DicomMediaPart]:
        """
            Parse a multipart message body.

            Extracts individual parts from a multipart MIME message and converts
            each part to appropriate DicomMediaPart objects based on content type.

            Args:
                body (bytes): Raw multipart message body bytes.

            Returns:
                List[DicomMediaPart]: List of parsed media parts.
        """

        # find teh first boundary
        start_index = body.find(bytes('--'+self.boundary+'\r\n',
                                      encoding='UTF-8'))

        # check that the first index is zero.
        parts : List[DicomMediaPart] = []
        finished = False
        while not finished:
            end_index = body.find(bytes('--'+self.boundary, encoding='UTF-8'),
                                  start_index+5+len(self.boundary))

            if (body[end_index+len(self.boundary) + 2:end_index+len(self.boundary)+4] == bytes('--', encoding='UTF-8') \
                and (len(body)-(end_index+len(self.boundary)+4)) < 5):
                # this is the last one
                end_index = end_index - 1
                finished = True

            # extract the part
            sub_bytes = body[start_index+len(self.boundary)+4:end_index]

            # extract the headers
            (headers, header_end_index) = self.extract_headers(sub_bytes)

            # check the transfer syntax

            # need to extract transfer syntax
            # also charset

            content_type_str = headers["content-type"]
            cts_parts = content_type_str.split(';')
            content_type = cts_parts[0]  # always have content type
            temp : Dict[str,str] = {}
            for part in cts_parts[1:]:
                sp = part.split('=')
                temp[sp[0].lower().strip()] = temp[sp[1].lower().strip()]

            transfer_syntax = temp.get('transfer-syntax')
            charset = temp.get('charset')

            sub_bytes_data = sub_bytes[header_end_index:]

            if content_type == "application/dicom":
                try:
                    ds = pydicom.dcmread(BytesIO(sub_bytes_data))
                    parts.append(DicomMediaPartDICOM(ds, headers))
                except pydicom.errors.InvalidDicomError:
                    parts.append(DicomMediaPartDICOM(None, headers))

            elif content_type == "application/dicom+json":
                parts.append(DicomMediaPartJSON(sub_bytes_data.decode('utf-8'),
                                                headers))

            elif content_type == "application/dicom+xml":
                parts.append(DicomMediaPartXML(sub_bytes_data.decode('utf-8'),
                                               headers))

            elif content_type == "application/octet-stream":
                parts.append(DicomMediaPartBytes(sub_bytes_data, headers))

            # this can be problamatic as this might be an encasulated image
            elif content_type in ["image/jpeg", "image/dicom-rle", "image/jls",
                                  "image/jp2", "image/jpx",  "image/jphc",
                                  "image/gif", "image/png"]:
                parts.append(DicomMediaPartDICOMImage(sub_bytes_data, content_type, transfer_syntax, headers))


            elif content_type in ["application/pdf", "text/XML", "model/stl",
                                  "model/obj", "model/mtl"]:
                parts.append(DicomMediaPartDocument(sub_bytes_data, content_type,
                                                    headers))
            if finished:
                break

            start_index = end_index
        return parts

    def extract_headers(self, sub_bytes:bytes)-> Tuple[Dict,int]:
        """
            Extract HTTP headers from a multipart section.

            Parses the header section of a multipart part to extract
            key-value pairs for Content-Type, Content-Location, etc.

            Args:
                sub_bytes (bytes): Raw bytes containing headers and data.

            Returns:
                tuple: (headers_dict, header_end_index) where headers_dict contains
                       the parsed headers and header_end_index is the byte offset
                       where the actual content starts.
        """


        # look for CRLFCRLF
        end_header_index = sub_bytes.find(bytes('\r\n\r\n', encoding='UTF-8'))

        headers = {}

        temp = sub_bytes[:end_header_index].decode('UTF-8')
        for line in temp.split('\n'):
            if line == "\n":
                continue
            line_split = line.split(':')
            headers[line_split[0].strip().lower()] = line_split[1].strip()

        return (headers, end_header_index + 4)
