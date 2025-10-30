"""
JPEG Metadata Extractor Module

Extracts metadata from JPEG, JPEG2000, and JPEG-LS image streams.
Provides information about bits per pixel, lossless compression, and baseline/extended specifications.

This is extremely experimental at this stage and will be updated/restructured.

"""
from typing import Tuple, List, Dict, Optional, Union
import struct
import io
from pathlib import Path
#from dcm_meta import get_tsu_from_image_jpeg
import traceback

class JPEGMarker:
    """Represents a JPEG marker with value and name."""

    def __init__(self, val:int, name:str)->None:
        """Initialize JPEG marker.

        Args:
            val (int): Marker value
            name (str): Marker name
        """
        self.val = val
        self.name = name

    def __repr__(self) ->str:
        """Return string representation of marker."""
        return f"{hex(self.val)} {self.name}"

class JPEGMarkerWO(JPEGMarker):
    """JPEG marker without additional data."""
    def __init__(self, val:int , name:str)->None:
        """Initialize JPEG marker without data.

        Args:
            val (int): Marker value
            name (str): Marker name
        """
        super(JPEGMarkerWO, self).__init__(val, name)



markers = {}

markers[0xFFD0] = JPEGMarker(0xFFD0,"RSTm 0")
markers[0xFFD1] = JPEGMarker(0xFFD1,"RSTm 1")
markers[0xFFD2] = JPEGMarker(0xFFD2,"RSTm 2")
markers[0xFFD3] = JPEGMarker(0xFFD3,"RSTm 3")
markers[0xFFD4] = JPEGMarker(0xFFD4,"RSTm 4")
markers[0xFFD5] = JPEGMarker(0xFFD5,"RSTm 5")
markers[0xFFD6] = JPEGMarker(0xFFD6,"RSTm 6")
markers[0xFFD7] = JPEGMarker(0xFFD7,"RSTm 7")



markers[0xFFD8] = JPEGMarker(0xFFD8,"Start of Image")
markers[0xFFD9] = JPEGMarker(0xFFD9,"End of Image")

markers[0xFFC0] = JPEGMarkerWO(0xFFC0,"Start of Frame (Baseline DCT)")
markers[0xFFC1] = JPEGMarkerWO(0xFFC1,"Start of Frame (Extended Sequential DCT)")
markers[0xFFC2] = JPEGMarkerWO(0xFFC2,"Start of Frame (Progressive DCT)")
markers[0xFFC3] = JPEGMarkerWO(0xFFC3,"Start of Frame (Lossless Sequential DCT)")
markers[0xFFC4] = JPEGMarkerWO(0xFFC4,"Define Huffman Tables")
markers[0xFFC5] = JPEGMarkerWO(0xFFC5,"Start of Frame (Differential Sequential DCT)")
markers[0xFFC6] = JPEGMarkerWO(0xFFC6,"Start of Frame (Differential Progressive DCT)")
markers[0xFFC7] = JPEGMarkerWO(0xFFC7,"Start of Frame (Differential Lossless DCT)")
markers[0xFFC9] = JPEGMarkerWO(0xFFC9,"Start of Frame (Extended Sequential DCT, Arithmetic)")
markers[0xFFCA] = JPEGMarkerWO(0xFFCA,"Start of Frame (Progressive DCT, Arithmetic)")
markers[0xFFCB] = JPEGMarkerWO(0xFFCB,"Start of Frame (Lossless Sequential, Arithmetic)")
markers[0xFFCC] = JPEGMarkerWO(0xFFCC,"Define Arithmetic Coding conditionings")
markers[0xFFCD] = JPEGMarkerWO(0xFFCD,"Start of Frame (Differential Sequential DCT, Arithmetic)")
markers[0xFFCE] = JPEGMarkerWO(0xFFCE,"Start of Frame (Differential Progressive DCT, Arithmetic)")
markers[0xFFCF] = JPEGMarkerWO(0xFFCF,"Start of Frame (Differential Lossless, Arithmetic)")
markers[0xFFF7] = JPEGMarkerWO(0xFFF7,"Start of Frame JPEG-LS")
markers[0xFFF8] = JPEGMarkerWO(0xFFF8,"JPEG-LS Params")


markers[0xFFDA] = JPEGMarkerWO(0xFFDA,"Start of Scan (image data)")
markers[0xFFDB] = JPEGMarkerWO(0xFFDB,"Define Quantization Tables")
markers[0xFFDC] = JPEGMarkerWO(0xFFDC,"Define Number of Lines")
markers[0xFFDD] = JPEGMarkerWO(0xFFDD,"Define Restart Interval")
markers[0xFFDE] = JPEGMarkerWO(0xFFDE,"Define Hierarchical Progression")
markers[0xFFDF] = JPEGMarkerWO(0xFFDF,"EXPand reference components")

markers[0xFFE0] = JPEGMarkerWO(0xFFE0,"Application segment 0")
markers[0xFFE1] = JPEGMarkerWO(0xFFE1,"Application segment 1")
markers[0xFFE2] = JPEGMarkerWO(0xFFE2,"Application segment 2")
markers[0xFFE3] = JPEGMarkerWO(0xFFE3,"Application segment 3")
markers[0xFFE4] = JPEGMarkerWO(0xFFE4,"Application segment 4")
markers[0xFFE5] = JPEGMarkerWO(0xFFE5,"Application segment 5")


markers[0xFFF0] = JPEGMarkerWO(0xFFF0,"Version")
markers[0xFFF1] = JPEGMarkerWO(0xFFF0,"Define Tiled Image")
markers[0xFFF2] = JPEGMarkerWO(0xFFF0,"Define Tile")
markers[0xFFF3] = JPEGMarkerWO(0xFFF0,"Selectively Refined Frame")
markers[0xFFF4] = JPEGMarkerWO(0xFFF0,"Selectively Refined Scan")
markers[0xFFF5] = JPEGMarkerWO(0xFFF0,"Define Component Registration")
markers[0xFFF6] = JPEGMarkerWO(0xFFF0,"Define Quantizer Scale selection")
markers[0xFFFE] = JPEGMarkerWO(0xFFF0,"Comment")



class JPEGMetadata:
    """Container for JPEG metadata information."""

    def __init__(self) -> None:
        self.format_type : str| None = None
        self.bits_per_sample: int  = 0
        self.is_lossless : bool | None= None
        self.is_baseline : bool | None= None
        self.width : int = 0
        self.height : int =0
        self.components : int = 0
        self.compression_type : str | None= None
        self.colorspace : str | None = None
        self.color_transform = None
        self.component_info : List[Dict] = []
        self.error : str| None  = None
        self.psv = None
        self.progression_order : str|  None= None


class JPEGMetadataExtractor:
    """Extracts metadata from various JPEG format streams."""

    # JPEG markers
    SOI = 0xFFD8  # Start of Image
    SOF0 = 0xFFC0  # Start of Frame (Baseline DCT)
    SOF1 = 0xFFC1  # Start of Frame (Extended Sequential DCT)
    SOF2 = 0xFFC2  # Start of Frame (Progressive DCT)
    SOF3 = 0xFFC3  # Start of Frame (Lossless Sequential)
    SOF5 = 0xFFC5  # Start of Frame (Differential Sequential DCT)
    SOF6 = 0xFFC6  # Start of Frame (Differential Progressive DCT)
    SOF7 = 0xFFC7  # Start of Frame (Differential Lossless)
    SOF9 = 0xFFC9  # Start of Frame (Extended Sequential DCT, Arithmetic)
    SOF10 = 0xFFCA # Start of Frame (Progressive DCT, Arithmetic)
    SOF11 = 0xFFCB # Start of Frame (Lossless Sequential, Arithmetic)
    SOF13 = 0xFFCD # Start of Frame (Differential Sequential DCT, Arithmetic)
    SOF14 = 0xFFCE # Start of Frame (Differential Progressive DCT, Arithmetic)
    SOF15 = 0xFFCF # Start of Frame (Differential Lossless, Arithmetic)
    SOS = 0xFFDA   # Start of Scan
    EOI = 0xFFD9   # End of Image
    APP0 = 0xFFE0  # Application segment 0 (JFIF)
    APP1 = 0xFFE1  # Application segment 1 (EXIF)
    APP2 = 0xFFE2  # Application segment 2 (ICC Profile/FlashPix)
    APP14 = 0xFFEE # Application segment 14 (Adobe)

    MCT = 0xFF74
    MCC = 0xFF75
    MCO = 0xFF77
    CBD = 0xFF78


    # JPEG-LS markers
    SOF55 = 0xFFF7  # JPEG-LS Start of Frame
    LSE = 0xFFF8    # JPEG-LS Extension

    def __init__(self) -> None:
        self._stream = io.BytesIO()
        self._position = 0
        self.reset()

    def reset(self) -> None:
        """Reset internal state for processing a new image."""
        self._stream  = io.BytesIO()
        self._position = 0

    def extract_metadata(self, source: Union[str, Path, bytes, io.IOBase]) -> JPEGMetadata:
        """
        Extract metadata from a JPEG image source.

        Args:
            source: File path, bytes, or file-like object containing JPEG data

        Returns:
            JPEGMetadata object containing extracted information
        """
        metadata = JPEGMetadata()

        try:
            # Handle different input types
            if isinstance(source, (str, Path)):
                with open(source, 'rb') as f:
                    data = f.read()
                self._stream = io.BytesIO(data)
            elif isinstance(source, bytes):
                self._stream = io.BytesIO(source)
            elif hasattr(source, 'read'):
                if hasattr(source, 'seek'):
                    source.seek(0)
                data = source.read()
                self._stream = io.BytesIO(data)
            else:
                raise ValueError("Unsupported source type")

            # Determine format type
            format_type = self._detect_format()
            metadata.format_type = format_type

            if format_type == "JPEG2000":
                self._extract_jpeg2000_metadata(metadata)
            elif format_type == "JPEG-LS":
                self._extract_jpeg_ls_metadata(metadata)
            elif format_type == "JPEG":
                self._extract_jpeg_metadata(metadata)
            else:
                metadata.error = f"Unsupported format: {format_type}"

        except Exception as e:
            traceback.print_exc()
            metadata.error = str(e)

        return metadata

    def _detect_format(self) -> str:
        """Detect the JPEG format type from file header.

        Returns:
            str: Format type ('JPEG', 'JPEG2000', 'JPEG-LS', 'JPEG-XL', or 'Unknown')
        """
        self._stream.seek(0)
        header = self._stream.read(12)

        if len(header) < 4:
            return "Unknown"

        # JPEG2000 detection
        if header[:4] == b'\x00\x00\x00\x0C':  # JP2 signature box
            return "JPEG2000"
        elif header[:4] == b'\xFF\x4F\xFF\x51':  # JPEG2000 codestream
            return "JPEG2000"
        elif header == b'\x00\x00\x00\x0c\x4a\x58\x4c\x20\x0d\x0a\x87\x0a': #JPEG-XL
            return "JPEG-XL"

        # Standard JPEG detection
        if header[:2] == b'\xFF\xD8':
            # Check for JPEG-LS marker
            self._stream.seek(0)
            while True:
                marker = self._read_marker()
                if marker is None:
                    break
                if marker == self.SOF55:
                    return "JPEG-LS"
                elif marker in [self.SOF0, self.SOF1, self.SOF2, self.SOF3]:
                    return "JPEG"
            return "JPEG"
        elif header[:2] == b"\xFF\x0A":
            return "JPEG-XL"

        return "Unknown"

    def _read_marker(self) -> Optional[int]:
        """Read next JPEG marker from stream.

        Returns:
            Optional[int]: JPEG marker value or None if end of stream
        """
        while True:
            byte = self._stream.read(1)
            if not byte:
                return None


            if byte[0] == 0xFF:

                marker_byte = self._stream.read(1)

                if not marker_byte:
                    return None

                marker = 0xFF00 | marker_byte[0]

                if marker != 0xFF00:  # Skip padding
                    return marker

    def _read_uint16(self) -> int:
        """Read 16-bit big-endian unsigned integer.

        Returns:
            int: Unsigned 16-bit integer value

        Raises:
            ValueError: If unexpected end of stream
        """
        data = self._stream.read(2)
        if len(data) != 2:
            raise ValueError("Unexpected end of stream")
        return struct.unpack('>H', data)[0]

    def _read_uint32(self) -> int:
        """Read 32-bit big-endian unsigned integer.

        Returns:
            int: Unsigned 32-bit integer value

        Raises:
            ValueError: If unexpected end of stream
        """
        data = self._stream.read(4)
        if len(data) != 4:
            raise ValueError("Unexpected end of stream")
        return struct.unpack('>I', data)[0]

    def _extract_jpeg_metadata(self, metadata: JPEGMetadata)->None:
        """Extract metadata from standard JPEG stream.

        Args:
            metadata (JPEGMetadata): Metadata object to populate
        """
        self._stream.seek(0)

        while True:
            marker = self._read_marker()
            if marker is None:
                break
            print (markers[marker])
            if marker == self.SOI:
                continue
            if marker == self.EOI:
                break

            elif marker in [self.SOF0, self.SOF1, self.SOF2, self.SOF3,
                           self.SOF5, self.SOF6, self.SOF7, self.SOF9,
                           self.SOF10, self.SOF11, self.SOF13, self.SOF14, self.SOF15]:
                self._parse_sof_marker(marker, metadata)
            elif marker == self.APP0:
                print ("parse jfif")
                self._parse_app0_jfif(metadata)
            elif marker == self.APP14:
                self._parse_app14_adobe(metadata)
            elif marker == self.APP2:
                self._parse_app2_icc(metadata)
            elif marker == self.SOS:

                self._parse_jpeg_sos(metadata)
                break
            else:
                # Skip other markers
                try:
                    length = self._read_uint16()
                    print ("Length - %d"%length)
                    if length >= 2:
                        self._stream.seek(self._stream.tell() + length - 2)
                except:
                    break

        # Infer colorspace from components if not explicitly set
        if metadata.colorspace is None:
            metadata.colorspace = self._infer_colorspace_from_components(metadata)

    def _parse_sof_marker(self, marker: int, metadata: JPEGMetadata)-> None:
        """Parse Start of Frame marker for JPEG."""
        length = self._read_uint16()
        precision = struct.unpack('B', self._stream.read(1))[0]
        height = self._read_uint16()
        width = self._read_uint16()
        components = struct.unpack('B', self._stream.read(1))[0]

        metadata.bits_per_sample = precision
        metadata.width = width
        metadata.height = height
        metadata.components = components

        # Parse component information
        for i in range(components):
            if self._stream.tell() < len(self._stream.getvalue()) - 2:
                comp_id = struct.unpack('B', self._stream.read(1))[0]
                sampling = struct.unpack('B', self._stream.read(1))[0]
                quant_table = struct.unpack('B', self._stream.read(1))[0]

                h_sampling = (sampling >> 4) & 0x0F
                v_sampling = sampling & 0x0F

                metadata.component_info.append({
                    'id': comp_id,
                    'h_sampling': h_sampling,
                    'v_sampling': v_sampling,
                    'quant_table': quant_table
                })

        # Determine if lossless and baseline/extended
        if marker == self.SOF0:
            metadata.is_lossless = False
            metadata.is_baseline = True
            metadata.compression_type = "Baseline DCT"
        elif marker == self.SOF1:
            metadata.is_lossless = False
            metadata.is_baseline = False
            metadata.compression_type = "Extended Sequential DCT"
        elif marker == self.SOF2:
            metadata.is_lossless = False
            metadata.is_baseline = False
            metadata.compression_type = "Progressive DCT"
        elif marker in [self.SOF3, self.SOF11]:
            metadata.is_lossless = True
            metadata.is_baseline = False
            metadata.compression_type = "Lossless Sequential"
        elif marker == self.SOF7:
            metadata.is_lossless = True
            metadata.is_baseline = False
            metadata.compression_type = "Differential Lossless"
        else:
            metadata.is_lossless = False
            metadata.is_baseline = False
            metadata.compression_type = "Extended/Arithmetic"

    def _extract_jpeg_ls_metadata(self, metadata: JPEGMetadata)-> None:
        """Extract metadata from JPEG-LS stream."""
        self._stream.seek(0)
        metadata.is_lossless = True  # JPEG-LS is inherently lossless (or near-lossless)
        metadata.is_baseline = False  # JPEG-LS is not baseline JPEG
        metadata.compression_type = "JPEG-LS"

        while True:
            marker = self._read_marker()
            if marker is None:
                break
            print (markers[marker])

            if marker == self.SOI:
                continue

            if marker == self.EOI:
                break
            elif marker == self.SOF55:
                self._parse_jpeg_ls_sof(metadata)
                #break
            elif marker == self.SOS:

                self._parse_jpeg_ls_sos(metadata)
                break
            else:
                # Skip other markers
                try:
                    length = self._read_uint16()
                    if length >= 2:
                        self._stream.seek(self._stream.tell() + length - 2)
                except:
                    break

    def parse_jpeg2000_cod_segment(self, metadata: JPEGMetadata) -> None:

        """
        Parse the COD segment data from file object positioned after COD marker.

        Args:
            file_obj: File object positioned after COD marker

        Returns:
            dict: Parsed COD segment information
        """
        # pylint: disable=unused-variable

        # Read segment length

        length = self._read_uint16()



        # Parse COD segment fields

        # Scod (coding style)
        scod = struct.unpack('B', self._stream.read(1))[0]
        progression_order = struct.unpack('B', self._stream.read(1))[0]
        num_layers = struct.unpack('>H', self._stream.read(2))[0]
        mct_used = struct.unpack('B', self._stream.read(1))[0]

        progression_orders = {0: 'LRCP', 1: 'RLCP', 2: 'RPCL', 3: 'PCRL', 4: 'CPRL'}

        metadata.progression_order = progression_orders[progression_order]
        decomposition_levels = struct.unpack('B', self._stream.read(1))[0]

        code_block_width = struct.unpack('B', self._stream.read(1))[0]
        code_block_height = struct.unpack('B', self._stream.read(1))[0]
        code_block_style = struct.unpack('B', self._stream.read(1))[0]
        wavelet_transform = struct.unpack('B', self._stream.read(1))[0]

        self._stream.seek(self._stream.tell() + length - 12)

        if wavelet_transform & 0x01:
            print( "5/3 reversible (lossless)")
            metadata.is_lossless = True

        else:
            print ( "9/7 irreversible (lossy)")
            metadata.is_lossless = False


    def _parse_jpeg_sos(self, metadata: JPEGMetadata) -> None:
        # pylint: disable=unused-variable

        """Parse JPEG Start of Scan marker."""
        length = self._read_uint16()
        components = struct.unpack('B', self._stream.read(1))[0]


        for i in range(components):
            selector = struct.unpack('B', self._stream.read(1))[0]
            temp = struct.unpack('B', self._stream.read(1))[0]

        psv_sss = struct.unpack('B', self._stream.read(1))[0]

        sse = struct.unpack('B', self._stream.read(1))[0]
        successive_approximation = struct.unpack('B', self._stream.read(1))[0]

        metadata.psv = psv_sss
        #print (f"Components {components}")
        #print (f"Length {length}")
        #print (f"Near lossless {near_lossless}")


    def _parse_jpeg_ls_sos(self, metadata: JPEGMetadata) -> None:
        """Parse JPEG-LS Start of Scan marker."""
        # pylint: disable=unused-variable

        length = self._read_uint16()
        components = struct.unpack('B', self._stream.read(1))[0]


        for i in range(components):
            comp_id = struct.unpack('B', self._stream.read(1))[0]
            map_table_id = struct.unpack('B', self._stream.read(1))[0]

        near_lossless = struct.unpack('B', self._stream.read(1))[0]
        scan_interleave = struct.unpack('B', self._stream.read(1))[0]
        extra = struct.unpack('B', self._stream.read(1))[0]

        if near_lossless != 0:
            metadata.is_lossless = False
        else:
            metadata.is_lossless = True

        #print (f"Components {components}")
        #print (f"Length {length}")
        #print (f"Near lossless {near_lossless}")

    def _parse_jpeg_ls_sof(self, metadata: JPEGMetadata) -> None:
        """Parse JPEG-LS Start of Frame marker."""
        # pylint: disable=unused-variable

        length = self._read_uint16()
        precision = struct.unpack('B', self._stream.read(1))[0]
        height = self._read_uint16()
        width = self._read_uint16()
        components = struct.unpack('B', self._stream.read(1))[0]

        metadata.bits_per_sample = precision
        metadata.width = width
        metadata.height = height
        metadata.components = components

        # Parse component information for JPEG-LS
        for i in range(components):
            if self._stream.tell() < len(self._stream.getvalue()) - 2:
                comp_id = struct.unpack('B', self._stream.read(1))[0]
                sampling = struct.unpack('B', self._stream.read(1))[0]
                quant_table = struct.unpack('B', self._stream.read(1))[0]

                h_sampling = (sampling >> 4) & 0x0F
                v_sampling = sampling & 0x0F

                metadata.component_info.append({
                    'id': comp_id,
                    'h_sampling': h_sampling,
                    'v_sampling': v_sampling,
                    'quant_table': quant_table
                })

        # Infer colorspace for JPEG-LS
        metadata.colorspace = self._infer_colorspace_from_components(metadata)

    def _extract_jpeg2000_metadata(self, metadata: JPEGMetadata)->None:
        """Extract metadata from JPEG2000 stream."""
        self._stream.seek(0)
        metadata.is_baseline = False  # JPEG2000 is not baseline JPEG
        metadata.compression_type = "JPEG2000"

        # Look for image header box or main header in codestream
        if self._is_jp2_format():
            print ("boxes")
            self._parse_jp2_boxes(metadata)
        else:
            print ("codestream")
            self._parse_j2k_codestream(metadata)

    def _is_jp2_format(self) -> bool:
        """Check if this is JP2 format (boxed) vs raw codestream."""
        self._stream.seek(0)
        header = self._stream.read(4)
        return header == b'\x00\x00\x00\x0C'

    def _parse_jp2_boxes(self, metadata: JPEGMetadata)->None:
        """Parse JP2 format boxes."""
        self._stream.seek(0)

        while True:
            pos = self._stream.tell()
            length_data = self._stream.read(4)
            if len(length_data) != 4:
                break

            length = struct.unpack('>I', length_data)[0]
            type_data = self._stream.read(4)
            if len(type_data) != 4:
                break

            box_type = type_data.decode('ascii', errors='ignore')

            if box_type == 'ihdr':  # Image Header box
                self._parse_jp2_image_header(metadata)
                break
            elif length > 8:
                self._stream.seek(pos + length)
            else:
                break

    def _parse_jp2_image_header(self, metadata: JPEGMetadata)->None:
        """Parse JP2 image header box."""
        height = self._read_uint32()
        width = self._read_uint32()
        components = self._read_uint16()
        bpc = struct.unpack('B', self._stream.read(1))[0]
        compression = struct.unpack('B', self._stream.read(1))[0]
        unkc = struct.unpack('B', self._stream.read(1))[0]  # Unknown colorspace
        ipr = struct.unpack('B', self._stream.read(1))[0]   # Intellectual Property Rights

        print (compression)
        print (unkc)
        print (ipr)

        metadata.width = width
        metadata.height = height
        metadata.components = components
        metadata.bits_per_sample = (bpc & 0x7F) + 1

        # JPEG2000 can be lossless or lossy
       # metadata.is_lossless = None  # Cannot determine from header alone

        # Look for colorspace specification box
        metadata.colorspace = self._infer_colorspace_from_components(metadata)

    def _parse_j2k_codestream(self, metadata: JPEGMetadata)->None:
        """Parse raw JPEG2000 codestream."""
        self._stream.seek(0)

        # Look for SOC (Start of Codestream) marker
        marker = self._read_uint16()
        if marker != 0xFF4F:
            raise ValueError("Invalid JPEG2000 codestream")

        # Look for SIZ (Image and tile size) marker
        while True:
            marker = self._read_uint16()
            print (hex(marker))
            if marker == 0xFF51:  # SIZ marker
                self._parse_j2k_siz_segment(metadata)
                #break
            #if marker == 0xFF50: # CAP maker
            elif marker == 0xFF52: # COD marker
                print ("parse cod")
                self.parse_jpeg2000_cod_segment(metadata)
            elif marker == 0xFF93:  # SOD marker
                break

            else:
                if marker in [self.MCC,self.MCO, self.MCT, self.CBD]:
                    print ("Part 2")
                    metadata.compression_type = "JPEG2000 Part 2"
                # Skip segment
                length = self._read_uint16()
                if length >= 2:
                    self._stream.seek(self._stream.tell() + length - 2)

    def _parse_j2k_siz_segment(self, metadata: JPEGMetadata)->None:
        """Parse JPEG2000 SIZ segment."""
        # pylint: disable=unused-variable

        length = self._read_uint16()
        capability = self._read_uint16()
        if (capability & 0x4000) != 0:
            metadata.compression_type = "HT JPEG2000"
        width = self._read_uint32()
        height = self._read_uint32()
        x_offset = self._read_uint32()
        y_offset = self._read_uint32()
        tile_width = self._read_uint32()
        tile_height = self._read_uint32()
        tile_x_offset = self._read_uint32()
        tile_y_offset = self._read_uint32()
        components = self._read_uint16()

        metadata.width = width
        metadata.height = height
        metadata.components = components

        # Read component information
        for i in range(components):
            component_info = struct.unpack('B', self._stream.read(1))[0]
            xcomp = struct.unpack('B', self._stream.read(1))[0]
            ycomp = struct.unpack('B', self._stream.read(1))[0]
            metadata.bits_per_sample = (component_info & 0x7F) + 1

        # JPEG2000 lossless determination requires analyzing the wavelet transform
        # For simplicity, we'll mark it as potentially lossless
       # metadata.is_lossless = None

        # Infer colorspace from component count
        metadata.colorspace = self._infer_colorspace_from_components(metadata)

    def _parse_app0_jfif(self, metadata: JPEGMetadata)->None:
        """Parse APP0 JFIF marker for colorspace information."""
        length = self._read_uint16()
        if length < 14:
            return

        # Read JFIF identifier
        jfif_id = self._stream.read(5)
        if jfif_id != b'JFIF\x00':
            self._stream.seek(self._stream.tell() + length - 7)
            return

        # JFIF implies YCbCr colorspace (or grayscale for 1 component)
        if metadata.components == 1:
            metadata.colorspace = "Grayscale"
        else:
            metadata.colorspace = "YCbCr"

        # Skip rest of JFIF data
        self._stream.seek(self._stream.tell() + length - 7)

    def _parse_app14_adobe(self, metadata: JPEGMetadata)->None:
        """Parse APP14 Adobe marker for colorspace information."""
        length = self._read_uint16()
        if length < 12:
            return

        # Read Adobe identifier
        adobe_id = self._stream.read(5)
        if adobe_id != b'Adobe':
            self._stream.seek(self._stream.tell() + length - 7)
            return

        # Skip version, flags
        self._stream.seek(self._stream.tell() + 7)

        # Read color transform flag
        if self._stream.tell() < len(self._stream.getvalue()):
            color_transform = struct.unpack('B', self._stream.read(1))[0]
            metadata.color_transform = color_transform

            # Interpret color transform
            if metadata.components == 3:
                if color_transform == 1:
                    metadata.colorspace = "YCbCr"
                elif color_transform == 0:
                    metadata.colorspace = "RGB"
                else:
                    metadata.colorspace = "Unknown"
            elif metadata.components == 4:
                if color_transform == 1:
                    metadata.colorspace = "YCCK"
                elif color_transform == 0:
                    metadata.colorspace = "CMYK"
                else:
                    metadata.colorspace = "Unknown"

        # Skip rest of Adobe data
        remaining = length - (self._stream.tell() - (self._stream.tell() - length + 2))
        if remaining > 0:
            self._stream.seek(self._stream.tell() + remaining)

    def _parse_app2_icc(self, metadata: JPEGMetadata)->None:
        """Parse APP2 ICC Profile marker for colorspace information."""
        length = self._read_uint16()
        if length < 14:
            return

        # Read ICC profile identifier
        icc_id = self._stream.read(12)
        if icc_id[:11] != b'ICC_PROFILE':
            self._stream.seek(self._stream.tell() + length - 14)
            return

        # ICC profile present - indicates color managed
        metadata.colorspace = "ICC Profile"

        # Skip rest of ICC data
        self._stream.seek(self._stream.tell() + length - 14)

    def _infer_colorspace_from_components(self, metadata: JPEGMetadata) -> str:
        """Infer colorspace from component count and IDs.

        Args:
            metadata (JPEGMetadata): Metadata object containing component information

        Returns:
            str: Inferred colorspace name
        """
        if metadata.components is None:
            return "Unknown"

        # Check component IDs if available
        if metadata.component_info:
            comp_ids = [comp['id'] for comp in metadata.component_info]

            if len(comp_ids) == 1:
                return "Grayscale"
            elif len(comp_ids) == 3:
                if comp_ids == [1, 2, 3]:
                    return "YCbCr"
                elif comp_ids == [82, 71, 66]:  # 'R', 'G', 'B'
                    return "RGB"
                else:
                    return "YCbCr"  # Default for 3 components
            elif len(comp_ids) == 4:
                if comp_ids == [1, 2, 3, 4]:
                    return "YCCK"
                else:
                    return "CMYK"  # Default for 4 components

        # Fallback to component count
        if metadata.components == 1:
            return "Grayscale"
        elif metadata.components == 3:
            return "YCbCr"
        elif metadata.components == 4:
            return "CMYK"
        else:
            return "Unknown"


def extract_jpeg_metadata(source: Union[str, Path, bytes, io.IOBase]) -> JPEGMetadata :
    """
    Convenience function to extract JPEG metadata and return as dictionary.

    Args:
        source: File path, bytes, or file-like object containing JPEG data

    Returns:
        Dictionary containing metadata information
    """
    extractor = JPEGMetadataExtractor()
    metadata = extractor.extract_metadata(source)

    return metadata

def get_photometric_interpretation(md : JPEGMetadata)->str:
    ## we won't be dealing with palette color

    if md.components == 1:
        return "MONOCHROME2" ## always assume MONOCHROME2
    elif md.components == 3:
        if md.format_type == "JPEG":
            if md.colorspace == "RGB":
                return "RGB"
            elif md.colorspace == "YCbCr":
                if md.is_lossless:
                    return "YBR_FULL"
                else:
                    return "YBR_FULL_422"
            else:
                return "UNKNOWN"
        elif md.format_type == "JPEG-LS":
            if md.colorspace == "RGB":
                return "RGB"
            elif md.colorspace == "YCbCr":
                if md.is_lossless:
                    return "YBR_FULL"
        elif md.format_type == "JPEG-2000":
            if md.colorspace == "RGB":
                return "RGB"
            elif md.colorspace == "YCbCr":
                ### blah blah
                pass
            else:
                return "UNKNOWN"
        else:
            return "UNKNOWN"
        return "RGB"
    else:
        return "UNKNOWN"



## https://dicom.nema.org/medical/dicom/current/output/chtml/part18/sect_8.7.3.3.2.html
def get_media_type_ts(metadata:JPEGMetadata)->Tuple[str,str]:
    """Get media type and transfer syntax from JPEG metadata.

    Determines the appropriate DICOM media type and transfer syntax UID
    based on the JPEG format and compression characteristics.

    Args:
        metadata (JPEGMetadata): JPEG metadata object

    Returns:
        tuple: (media_type, transfer_syntax_uid) pair
    """

    media_type = ""
    ts = ""
    if metadata.format_type == "JPEG":
        media_type = "image/jpeg"

        if metadata.is_lossless:
            ## can only be .57 or .70
            if metadata.psv is not None and int(metadata.psv) == 1:
                ts =  "1.2.840.10008.1.2.4.70"
            else:
                ts = "1.2.840.10008.1.2.4.57"
        else:
            if metadata.is_baseline:
                ts = "1.2.840.10008.1.2.4.50"
            else:
                ts = "1.2.840.10008.1.2.4.51"

    elif metadata.format_type == "JPEG-LS":
        media_type = "image/jls"
        if metadata.is_lossless:
            ts="1.2.840.10008.1.2.4.80"
        else:
            ts="1.2.840.10008.1.2.4.81"

    elif  metadata.format_type == "JPEG2000":
        if metadata.compression_type == "HT JPEG2000":
            media_type="image/jphc"

            if metadata.is_lossless:
                if metadata.progression_order == "RPCL":

                    ts = "1.2.840.10008.1.2.4.202"
                else:
                    ts = "1.2.840.10008.1.2.4.201"
            else:
                ts="1.2.840.10008.1.2.4.203"
        elif metadata.compression_type == "JPEG2000":
            media_type = "image/jp2"
            if metadata.is_lossless:
                ts = "1.2.840.10008.1.2.4.90"
            else:
                ts = "1.2.840.10008.1.2.4.91"
        elif metadata.compression_type == "JPEG2000 Part 2":
            media_type = "image/jpx"

            if metadata.is_lossless:
                ts = "1.2.840.10008.1.2.4.92"
            else:
                ts = "1.2.840.10008.1.2.4.93"


    return (media_type,ts)

# Example usage
if __name__ == "__main__":
    import sys
    import pydicom
    from pydicom.encaps import get_frame

    if len(sys.argv) != 2:
        print("Usage: python jpeg_metadata.py <image_file>")
        sys.exit(1)

    dcm = pydicom.dcmread(sys.argv[1])
    md = extract_jpeg_metadata(get_frame(dcm.PixelData,0,number_of_frames=1))

    print(f"File: {sys.argv[1]}")
    print("-" * 40)
    print (dcm.file_meta.TransferSyntaxUID)
    print (get_media_type_ts(md))
    print (md.is_lossless)
    print (md.is_baseline)
    #for key, value in metadata.items():
    #    if value is not None:
     #       print(f"{key:15}: {value}")
