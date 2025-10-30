"""
    Utility functions for parsing accept headers.
"""
from dataclasses import dataclass
from typing import List, Optional
from starlette.datastructures import Headers
from webob.acceptparse import Accept, AcceptLanguage, \
                              AcceptCharset, AcceptEncoding
from app.utils.dicom_media import DicomMediaType



@dataclass
class AcceptHeaderField:
    """
        Represents a header field with a value and optional quality factor.

        Attributes:
            value (str): The value of the header field.
            quality (float, optional): The quality factor of the header field, defaulting to 1.0.
    """
    value: str
    quality: float = 1.0


@dataclass
class AcceptType:
    """
        Represents a parsed Accept header media type with its associated metadata.

        Attributes:
            type (DicomMediaType): The parsed DICOM media type.
            media_type_str (str): The original media type string.
            is_multipart (bool, optional): Indicates if the media type is multipart. Defaults to True.
            transfer_syntax (str, optional): The transfer syntax associated with the media type, if applicable.
            charset (str, optional): The character set of the media type, if specified.
            quality (float, optional): The quality factor of the media type. Defaults to 1.0.
    """

    type: DicomMediaType
    media_type_str: str
    is_multipart: bool = True
    transfer_syntax: Optional[str] = None
    charset: Optional[str] = None
    quality: float = 1.0


@dataclass
class AcceptHeaders:

    """
        Represents the parsed Accept headers from an HTTP request.

        Attributes:
            accept_types (List[AcceptType]): List of parsed media types from the Accept header.
            charsets (List[AcceptHeaderField]): List of accepted character sets.
            encodings (Optional[List[AcceptHeaderField]]): Optional list of accepted content encodings.
            languages (Optional[List[AcceptHeaderField]]): Optional list of accepted languages.
    """

    accept_types: List[AcceptType]
    charsets: List[AcceptHeaderField]
    encodings: Optional[List[AcceptHeaderField]]
    languages: Optional[List[AcceptHeaderField]]

    #def acceptable_media_types(self) -> List[DicomMediaType]:
    #    pass

    #def acceptable_transfer_syntaxes(self) -> List[ tuple[str,float]]:
    #    pass


def parse_media_range(media_range : str) -> DicomMediaType:
    """
        Parse media type from media range string.
        Args:
            media_range (str): media range string.

        Returns:
            DicomMediaType: the parsed dicommediatype from media range.
    """

    if "application/dicom+xml" in media_range:
        return DicomMediaType.DICOM_XML

    if "application/dicom+json" in media_range:
        return DicomMediaType.DICOM_JSON

    if "application/dicom" in media_range:
        return DicomMediaType.DICOM

    if "application/octet-stream" in media_range:
        return DicomMediaType.BYTES

    if "image/" in media_range:
        return DicomMediaType.DICOM_IMAGE

    if "video/" in media_range:
        return DicomMediaType.DICOM_VIDEO
    if "application/vnd.sun.wadl+xml" in media_range:
        return DicomMediaType.WADL
    if "application/json" in media_range:
        return DicomMediaType.JSON
    if media_range == "*/*":
        return DicomMediaType.ANY
    return DicomMediaType.ANY


def parse_accept_charset_query( accept : str | None = None, charset: str | None = None) -> AcceptHeaders:
    """
        Parse accept headers from query.

        Args:
            accept (str | None): media range string.
            charset (str | None): media range string.


        Returns:
            AcceptHeaders: the parsed accept query.
    """
    accept_types = []

    if accept:
        for (media_range, qvalue, media_type_params, extension_params) \
                in Accept.parse(accept):
            ##
            is_mp = False

            if "multipart/related" in media_range:
                is_mp = True

            # parse the media range to DicomMediaType
            dcm_mt = parse_media_range(media_range)

            charset = None
            transfer_syntax = None

            # lets see is there is a charset param or transfer
            # syntax param here
            for (mtp_k, mtp_v) in media_type_params:
                if mtp_k == "charset":
                    charset = mtp_v
                if mtp_k == "transfer-syntax":
                    transfer_syntax = mtp_v

            for ext_param in extension_params:
                #(ep_k, ep_v)
                if isinstance(ext_param, tuple):
                    (ep_k, ep_v) = ext_param
                    if ep_k == "transfer-syntax":
                        transfer_syntax = ep_v

            temp = AcceptType(type=dcm_mt, media_type_str=media_range,
                            is_multipart=is_mp, transfer_syntax=transfer_syntax,
                            charset=charset, quality=qvalue)
            accept_types.append(temp)


    temp_charset = []
    if charset:
        for (cs, quality_value) in AcceptCharset.parse(charset):
            ##
            tempc = AcceptHeaderField(value=cs, quality=quality_value)
            temp_charset.append(tempc)

    return AcceptHeaders(accept_types=accept_types, charsets=temp_charset,
                         encodings=None, languages=None)


def parse_accept_headers(headers: Headers) -> AcceptHeaders:
    """
        Parse accept headers from query.

        Args:
            accept (str | None): media range string.
            charset (str | None): media range string.


        Returns:
            AcceptHeaders: the parsed accept query.
    """
    # https://docs.pylonsproject.org/projects/webob/en/stable/api/webob.html
    accept_field = headers["accept"]
    accept_lang = headers.get("accept-language",None)
    accept_enc = headers.get("accept-encoding",None)
    accept_charset = headers.get("accept-charset",None)

    accept_types = []
    for (media_range, qvalue, media_type_params, extension_params) \
            in Accept.parse(accept_field):
        ##
        is_mp = False

        if "multipart/related" in media_range:
            is_map = True

        # parse the media range to DicomMediaType
        dcm_mt = parse_media_range(media_range)

        charset = None
        transfer_syntax = None

        # lets see is there is a charset param or transfer
        # syntax param here
        for (mtp_k, mtp_v) in media_type_params:
            if mtp_k == "charset":
                charset = mtp_v
            if mtp_k == "transfer-syntax":
                transfer_syntax = mtp_v

        for ext_param in extension_params:
            #(ep_k, ep_v)
            if isinstance(ext_param, tuple):
                (ep_k, ep_v) = ext_param
                if ep_k == "transfer-syntax":
                    transfer_syntax = ep_v


        temp = AcceptType(type=dcm_mt, media_type_str=media_range,
                          is_multipart=is_mp, transfer_syntax=transfer_syntax,
                          charset=charset, quality=qvalue)
        accept_types.append(temp)


    language = []
    if accept_lang:
        for (language_range, quality_value) in AcceptLanguage.parse(accept_lang):
            ##
            templ = AcceptHeaderField(value=language_range, quality=quality_value)
            language.append(templ)

    encoding = []
    if accept_enc:
        for (coding, quality_value) in AcceptEncoding.parse(accept_enc):
            ##
            tempe = AcceptHeaderField(value=coding, quality=quality_value)
            encoding.append(tempe)

    charsets  = []
    if accept_charset:
        for (charset, quality_value) in AcceptCharset.parse(accept_charset):
            ##
            tempc = AcceptHeaderField(value=charset, quality=quality_value)
            charsets.append(tempc)

    return AcceptHeaders(accept_types=accept_types, charsets=charsets,
                         encodings=encoding, languages=language)
