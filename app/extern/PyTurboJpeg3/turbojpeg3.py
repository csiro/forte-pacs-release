"""
This module is a wrapper on TubroJpeg v3 API. This in essence a fork of 
PyTurbpo JPEG (https://github.com/lilohuang/PyTurboJPEG) and thus credit goes
to its author. 

"""

from ctypes import *
from ctypes.util import find_library
import ctypes
import platform
import warnings
import os
from typing import Tuple, Dict, Any
import numpy as np
import numpy.typing as npt

# default libTurboJPEG library path
DEFAULT_LIB_PATHS = {
    'Darwin': [
        '/usr/local/opt/jpeg-turbo/lib/libturbojpeg.dylib',
        '/opt/libjpeg-turbo/lib64/libturbojpeg.dylib',
        '/opt/homebrew/opt/jpeg-turbo/lib/libturbojpeg.dylib'
    ],
    'Linux': [
        '/opt/libjpeg-turbo/lib64/libturbojpeg.so',
        '/usr/lib/x86_64-linux-gnu/libturbojpeg.so.0',
        '/usr/lib/aarch64-linux-gnu/libturbojpeg.so.0',
        '/usr/lib/libturbojpeg.so.0',
        '/usr/lib64/libturbojpeg.so.0'

    ],
    'FreeBSD': [
        '/usr/local/lib/libturbojpeg.so.0',
        '/usr/local/lib/libturbojpeg.so'
    ],
    'NetBSD': [
        '/usr/pkg/lib/libturbojpeg.so.0',
        '/usr/pkg/lib/libturbojpeg.so'
    ],
    'Windows': ['C:/libjpeg-turbo64/bin/turbojpeg.dll']
}

# init types
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJINIT_COMPRESS = 0
TJINIT_DECOMPRESS = 1
TJINIT_TRANSFORM = 2



# parameters
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJPARAM_STOPONWARNING = 0
TJPARAM_BOTTOMUP = 1
TJPARAM_NOREALLOC = 2
TJPARAM_QUALITY = 3
TJPARAM_SUBSAMP = 4
TJPARAM_JPEGWIDTH = 5
TJPARAM_JPEGHEIGHT = 6
TJPARAM_PRECISION = 7
TJPARAM_COLORSPACE = 8
TJPARAM_FASTUPSAMPLE = 9
TJPARAM_FASTDCT = 10
TJPARAM_OPTIMIZE = 11
TJPARAM_PROGRESSIVE = 12
TJPARAM_SCANLIMIT = 13
TJPARAM_ARITHMETIC = 14
TJPARAM_LOSSLESS = 15
TJPARAM_LOSSLESSPSV = 16
TJPARAM_LOSSLESSPT = 17
TJPARAM_RESTARTBLOCKS = 18
TJPARAM_RESTARTROWS = 19
TJPARAM_XDENSITY = 20
TJPARAM_YDENSITY = 21
TJPARAM_DENSITYUNITS = 22
TJPARAM_MAXMEMORY = 23
TJPARAM_MAXPIXELS = 24
TJPARAM_SAVEMARKERS = 25

# error codes
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJERR_WARNING = 0
TJERR_FATAL = 1

# color spaces
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJCS_RGB = 0
TJCS_YCbCr = 1
TJCS_GRAY = 2
TJCS_CMYK = 3
TJCS_YCCK = 4

# pixel formats
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJPF_RGB = 0
TJPF_BGR = 1
TJPF_RGBX = 2
TJPF_BGRX = 3
TJPF_XBGR = 4
TJPF_XRGB = 5
TJPF_GRAY = 6
TJPF_RGBA = 7
TJPF_BGRA = 8
TJPF_ABGR = 9
TJPF_ARGB = 10
TJPF_CMYK = 11

# chrominance subsampling options
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJSAMP_444 = 0
TJSAMP_422 = 1
TJSAMP_420 = 2
TJSAMP_GRAY = 3
TJSAMP_440 = 4
TJSAMP_411 = 5
TJSAMP_441 = 6

# transform operations
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJXOP_NONE = 0
TJXOP_HFLIP = 1
TJXOP_VFLIP = 2
TJXOP_TRANSPOSE = 3
TJXOP_TRANSVERSE = 4
TJXOP_ROT90 = 5
TJXOP_ROT180 = 6
TJXOP_ROT270 = 7

# transform options
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
TJXOPT_PERFECT = 1
TJXOPT_TRIM = 2
TJXOPT_CROP = 4
TJXOPT_GRAY = 8
TJXOPT_NOOUTPUT = 16
TJXOPT_PROGRESSIVE = 32
TJXOPT_COPYNONE = 64

# pixel size
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
tjPixelSize = [3, 3, 4, 4, 4, 4, 1, 4, 4, 4, 4, 4]

# MCU block width (in pixels) for a given level of chrominance subsampling.
# MCU block sizes:
#  - 8x8 for no subsampling or grayscale
#  - 16x8 for 4:2:2
#  - 8x16 for 4:4:0
#  - 16x16 for 4:2:0
#  - 32x8 for 4:1:1
tjMCUWidth = [8, 16, 16, 8, 8, 32]

# MCU block height (in pixels) for a given level of chrominance subsampling.
# MCU block sizes:
#  - 8x8 for no subsampling or grayscale
#  - 16x8 for 4:2:2
#  - 8x16 for 4:4:0
#  - 16x16 for 4:2:0
#  - 32x8 for 4:1:1
tjMCUHeight = [8, 8, 16, 8, 16, 8]

# miscellaneous flags
# see details in https://github.com/libjpeg-turbo/libjpeg-turbo/blob/master/turbojpeg.h
# note: TJFLAG_NOREALLOC cannot be supported due to reallocation is needed by PyTurboJPEG.
TJFLAG_BOTTOMUP = 2
TJFLAG_FASTUPSAMPLE = 256
TJFLAG_FASTDCT = 2048
TJFLAG_ACCURATEDCT = 4096
TJFLAG_STOPONWARNING = 8192
TJFLAG_PROGRESSIVE = 16384
TJFLAG_LIMITSCANS = 32768

class CroppingRegion(Structure):
    _fields_ = [("x", c_int), ("y", c_int), ("w", c_int), ("h", c_int)]

class ScalingFactor(Structure):
    _fields_ = ('num', c_int), ('denom', c_int)

CUSTOMFILTER = CFUNCTYPE(
    c_int,
    POINTER(c_short),
    CroppingRegion,
    CroppingRegion,
    c_int,
    c_int,
    c_void_p
)



# MCU for luminance is always 8
MCU_WIDTH = 8
MCU_HEIGHT = 8
MCU_SIZE = 64



class TurboJPEG3(object):
    """A Python wrapper of libjpeg-turbo for decoding and encoding JPEG image."""
    def __init__(self, lib_path : str | None =None) -> None:
        print (self.__find_turbojpeg())
        turbo_jpeg = cdll.LoadLibrary(
            self.__find_turbojpeg() if lib_path is None else lib_path)
        self.__init_tj = turbo_jpeg.tj3Init
        self.__init_tj.restype = c_void_p
        self.__init_tj.argtypes = [c_int]

        self.__destroy_tj = turbo_jpeg.tjDestroy
        self.__destroy_tj.argtypes = [c_void_p]
        self.__destroy_tj.restype = None

        self.__get_error_str = turbo_jpeg.tj3GetErrorStr
        self.__get_error_str.argtypes = [c_void_p]
        self.__get_error_str.restype = c_char_p

        self.__get_error_code = turbo_jpeg.tj3GetErrorCode
        self.__get_error_code.argtypes = [c_void_p]
        self.__get_error_code.restype = c_int

        ## get  and set here
        self.__get_param = turbo_jpeg.tj3Get
        self.__get_param.argtypes = [c_void_p, c_int]
        self.__get_param.restype = c_int

        self.__set_param = turbo_jpeg.tj3Set
        self.__set_param.argtypes = [c_void_p, c_int, c_int]
        self.__set_param.restype = c_int

        # buffer size
        self.__buffer_size_jpeg = turbo_jpeg.tj3JPEGBufSize
        self.__buffer_size_jpeg.argtypes = [c_int,c_int,c_int]
        self.__buffer_size_jpeg.restype = c_size_t

        self.__buffer_size_yuv = turbo_jpeg.tj3YUVBufSize
        self.__buffer_size_yuv.argtypes = [c_int,c_int,c_int,c_int]
        self.__buffer_size_yuv.restype = c_size_t

        # YUV plane
        self.__yuv_plane_size = turbo_jpeg.tj3YUVPlaneSize
        self.__yuv_plane_size.argtypes = [c_int,c_int,c_int,c_int,c_int]
        self.__yuv_plane_size.restype = c_size_t

        self.__yuv_plane_width= turbo_jpeg.tj3YUVPlaneSize
        self.__yuv_plane_width.argtypes = [c_int,c_int,c_int]
        self.__yuv_plane_width.restype = c_size_t

        self.__yuv_plane_height = turbo_jpeg.tj3YUVPlaneSize
        self.__yuv_plane_height.argtypes = [c_int,c_int,c_int]
        self.__yuv_plane_height.restype = c_size_t

        # decompress
        self.__decompress_header = turbo_jpeg.tj3DecompressHeader
        self.__decompress_header.argtypes = [c_void_p, POINTER(c_ubyte), c_size_t]
        self.__decompress_header.restype = c_int

        self.__decompress8 =  turbo_jpeg.tj3Decompress8
        self.__decompress8.argtypes =  [c_void_p, POINTER(c_ubyte),c_size_t,POINTER(c_ubyte),c_int,c_int]
        self.__decompress8.restype =  c_int

        self.__decompress12 =  turbo_jpeg.tj3Decompress12
        self.__decompress12.argtypes =  [c_void_p, POINTER(c_ubyte),c_size_t,POINTER(c_short),c_int,c_int]
        self.__decompress12.restype =  c_int

        self.__decompress16 =  turbo_jpeg.tj3Decompress16
        self.__decompress16.argtypes =  [c_void_p, POINTER(c_ubyte),c_size_t,POINTER(c_ushort),c_int,c_int]
        self.__decompress16.restype =  c_int

        self.__decompress = {8:self.__decompress8, 12:self.__decompress12,16: self.__decompress16}

        self.__decompressYUV8 = turbo_jpeg.tj3DecompressToYUV8
        self.__decompressYUV8.argtypes = [c_void_p, POINTER(c_ubyte),c_size_t,POINTER(c_ubyte),c_int]
        self.__decompressYUV8.restype = c_int

        self.__decompressYUVPlanes8 = turbo_jpeg.tj3DecompressToYUVPlanes8
        self.__decompressYUVPlanes8.argtypes = [c_void_p, POINTER(c_ubyte),\
                                                c_size_t,POINTER(POINTER(c_ubyte)),POINTER(c_int)]
        self.__decompressYUVPlanes8.restype = c_int

        ## compress
        self.__compress8 = turbo_jpeg.tj3Compress8
        self.__compress8.argtypes = [c_void_p,POINTER(c_ubyte),c_int,c_int,c_int,c_int,\
                                     POINTER(POINTER(c_ubyte)), POINTER(c_size_t)]
        self.__compress8.restype = c_int

        self.__compress12 = turbo_jpeg.tj3Compress12
        self.__compress12.argtypes = [c_void_p,POINTER(c_short),c_int,c_int,c_int,c_int,\
                                      POINTER(POINTER(c_ubyte)), POINTER(c_size_t)]
        self.__compress12.restype = c_int

        self.__compress16 = turbo_jpeg.tj3Compress16
        self.__compress16.argtypes = [c_void_p,POINTER(c_ushort),c_int,c_int,c_int,c_int,\
                                      POINTER(POINTER(c_ubyte)), POINTER(c_size_t)]
        self.__compress16.restype = c_int

        self.__compress = {8:self.__compress8, 12:self.__compress12,16: self.__compress16}

        self.__free = turbo_jpeg.tjFree
        self.__free.argtypes = [c_void_p]
        self.__free.restype = None


    def decode_header(self, jpeg_buf : bytes) -> Tuple[int,int,int,int,int]:
        """decodes JPEG header and returns image properties as a tuple.
           e.g. (width, height, jpeg_subsample, jpeg_colorspace)
        """
        handle = self.__init_tj(TJINIT_DECOMPRESS)
        try:

            jpeg_array = np.frombuffer(jpeg_buf, dtype=np.uint8)
            src_addr = self.__getaddr(jpeg_array)
            return self.__get_header_and_dimensions(handle,src_addr,jpeg_array.size)
        finally:
            self.__destroy_tj(handle)


    def __get_header_and_dimensions(self,handle:c_void_p,jpeg_buf: ctypes._Pointer, jpeg_buf_size : int) \
        -> Tuple[int,int,int,int,int]:

        status = self.__decompress_header(
            handle, jpeg_buf, jpeg_buf_size)
        width = self.__get_param(handle,TJPARAM_JPEGWIDTH)
        height = self.__get_param(handle,TJPARAM_JPEGHEIGHT)
        jpeg_subsample = self.__get_param(handle,TJPARAM_SUBSAMP)
        jpeg_colorspace = self.__get_param(handle,TJPARAM_COLORSPACE)
        precision = self.__get_param(handle,TJPARAM_PRECISION)
        if status != 0:
            self.__report_error(handle)
        return (width, height, jpeg_subsample, jpeg_colorspace, precision)


    def __set_decomp_params(self,handle:c_void_p,** kwargs : Dict[str,Any])->None:

        pass

    def __set_comp_params(self,handle:c_void_p,** kwargs : Dict[str,Any])->None:


        pass

    def decode(self, jpeg_buf: bytes, pixel_format: int =TJPF_BGR, ** kwargs : Dict[str,Any])->np.ndarray:
        """decodes JPEG memory buffer to numpy array."""
        handle = self.__init_tj(TJINIT_DECOMPRESS)
        self.__set_decomp_params(handle, **kwargs)

        try:
            jpeg_array = np.frombuffer(jpeg_buf, dtype=np.uint8)
            src_addr = self.__getaddr(jpeg_array)

            (width,height,_,_,precision) = self.__get_header_and_dimensions(handle,src_addr,jpeg_array.size)


            #if scaling_factor == None: scaling_factor = 1.0
            scaling_factor = 1  ## scaling to be added later
            scaled_height = height * scaling_factor
            scaled_width = width * scaling_factor


            img_dtype : npt.DTypeLike = np.uint8  ## default is 8 bits

            if precision in [12,16]:
                img_dtype = np.uint16


            img_array = np.empty([scaled_height, scaled_width, tjPixelSize[pixel_format]],dtype=img_dtype)
            dest_addr = self.__getaddr(img_array)

            status = self.__decompress[precision](handle,src_addr,jpeg_array.size,dest_addr,0,pixel_format)

            if status != 0:
                self.__report_error(handle)
            return img_array
        finally:
            self.__destroy_tj(handle)



    def encode(self, img_array : np.ndarray, precision:int, pixel_format : int =TJPF_BGR, ** kwargs : Dict[str,Any]) \
        -> bytes | None:
        """encodes numpy array to JPEG memory buffer."""
        handle = self.__init_tj(TJINIT_COMPRESS)
        self.__set_comp_params(handle, **kwargs)

        try:
            img_array = np.ascontiguousarray(img_array)

            jpeg_buf = c_void_p()
            jpeg_size = c_ulong()

            height, width = img_array.shape[:2]
            channel = tjPixelSize[pixel_format]
            if channel > 1 and (len(img_array.shape) < 3 or img_array.shape[2] != channel):
                raise ValueError('Invalid shape for image data')
            src_addr = self.__getaddr(img_array)

            status = self.__compress[precision](handle,src_addr,width,img_array.strides[0], height, pixel_format,
                byref(jpeg_buf), byref(jpeg_size))

            if status != 0:
                self.__report_error(handle)
                return None

            if jpeg_buf.value is not None:
                result = self.__copy_from_buffer(jpeg_buf.value, jpeg_size.value)
                self.__free(jpeg_buf)

                return result
            return None
        finally:
            self.__destroy_tj(handle)

    def encode_bytes(self, img_array : bytes, width : int, height : int,  \
                     num_channels: int,precision:int, pixel_format : int =TJPF_BGR, ** kwargs : Dict[str,Any]) \
                                                                                            -> bytes | None:
        """encodes numpy array to JPEG memory buffer."""
        handle = self.__init_tj(TJINIT_COMPRESS)

        self.__set_comp_params(handle, **kwargs)

        try:
            jpeg_buf = c_void_p()
            jpeg_size = c_ulong()

            channel = tjPixelSize[pixel_format]
            if channel > 1 and (num_channels < 3 or num_channels != channel):
                raise ValueError('Invalid shape for image data')

            status = self.__compress[precision](handle,img_array,width,0, height, pixel_format,
                byref(jpeg_buf), byref(jpeg_size))

            if status != 0:
                self.__report_error(handle)
                return None

            if jpeg_buf.value is not None:
                result = self.__copy_from_buffer(jpeg_buf.value, jpeg_size.value)
                self.__free(jpeg_buf)

                return result
            return None
        finally:
            self.__destroy_tj(handle)

    def __report_error(self, handle: c_void_p) -> None:
        """reports error while error occurred"""
        if self.__get_error_code is not None:
            # using new error handling logic if possible
            if self.__get_error_code(handle) == TJERR_WARNING:
                warnings.warn(self.__get_error_string(handle))
                return
        # fatal error occurred
        raise IOError(self.__get_error_string(handle))

    def __get_error_string(self, handle: c_void_p)-> str:
        """returns error string"""
        # fallback to old interface
        return self.__get_error_str(handle).decode()

    def __find_turbojpeg(self)-> str:
        """returns default turbojpeg library path if possible"""
        lib_path = find_library('turbojpeg')
        if lib_path is not None:
            return lib_path
        for lib_path in DEFAULT_LIB_PATHS[platform.system()]:
            if os.path.exists(lib_path):
                return lib_path
        if platform.system() == 'Linux' and 'LD_LIBRARY_PATH' in os.environ:
            ld_library_path = os.environ['LD_LIBRARY_PATH']
            for path in ld_library_path.split(':'):
                lib_path = os.path.join(path, 'libturbojpeg.so.0')
                if os.path.exists(lib_path):
                    return lib_path
        raise RuntimeError(
            'Unable to locate turbojpeg library automatically. '
            'You may specify the turbojpeg library path manually.\n'
            'e.g. jpeg = TurboJPEG(lib_path)')

    def __getaddr(self, nda: np.ndarray)-> ctypes._Pointer :
        """returns the memory address for a given ndarray"""
        if nda.dtype == np.uint16:
            return cast(nda.__array_interface__['data'][0], POINTER(c_ushort))

        return cast(nda.__array_interface__['data'][0], POINTER(c_ubyte))

    @staticmethod
    def __copy_from_buffer(buffer: int, size :int ) -> bytes:
        """Copy bytes from buffer to python bytes."""
        dest_buf = create_string_buffer(size)
        memmove(dest_buf, buffer, size)
        return dest_buf.raw
