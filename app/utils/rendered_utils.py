"""
Utility functions for the rendering.
"""
import json
import numpy
import numpy.typing as npt
from PIL import Image, ImageDraw, ImageFont
from app.utils.accept_headers import  AcceptHeaders
from app.utils.dicom_storage_sop_class import is_compressed_transfer_syntax, is_image_sop_class
from app.utils.dicom_media import DicomMediaType  # noqa
from app.schema.dicom_instance import DCMInstance
from app.codecs.codec_registry import CodecRegistry
from app.utils.numpy_utils import buffer_to_array
from app.utils.rendered_query import Window, Viewport

def select_media_type_rendered(sop_class_uid : str , number_of_frames : int, \
    accept_query : AcceptHeaders , accept_headers : AcceptHeaders) -> str :
    """
    Selects the appropriate media type for rendering a DICOM image or thumbnail based on the provided SOP class UID,
    number of frames, and the client's accept headers.

    The selection process follows these steps:
    1. Identify the target's Resource Category (in this case, it's always an image).
    2. Select the representation with the highest priority supported media type for the image
    category in the Accept Query Parameter.
    3. If no media type in the Accept Query Parameter is supported, select the highest priority
    supported media type for the image category in the Accept header field, if any.
    4. Otherwise, select the default media type for the image category, if the Accept header field
    contains a wildcard media range matching the category, if any.
    5. Otherwise, return a 406 (Not Acceptable).

    The function returns the selected media type as a string, which can be "image/jpeg",
    "image/gif", or other supported image formats.
    """



    sorted_accept_query = sorted(accept_query.accept_types,key=lambda x: x.quality,reverse=True) ## currently only

    for accept_type in sorted_accept_query:
        if is_image_sop_class(sop_class_uid):
            if number_of_frames > 1:
                ##
                if accept_type.type == DicomMediaType.ANY or accept_type.media_type_str == "image/gif":
                    return "image/gif"
            else:
                if accept_type.type == DicomMediaType.ANY:
                    return "image/jpeg"
                elif accept_type.media_type_str in ["image/jpeg","image/gif","image/png","image/jp2","image/jph"]:
                    return accept_type.media_type_str



    sorted_accept_params = sorted(accept_headers.accept_types,key=lambda x: x.quality,reverse=True) ## currently only

    for accept_type in sorted_accept_params:
        if is_image_sop_class(sop_class_uid):
            if number_of_frames > 1:
                ##
                if accept_type.type == DicomMediaType.ANY or accept_type.media_type_str == "image/gif":
                    return "image/gif"
            else:
                if accept_type.type == DicomMediaType.ANY:
                    return "image/jpeg"
                elif accept_type.media_type_str in ["image/jpeg","image/gif","image/png","image/jp2","image/jph"]:
                    return accept_type.media_type_str

    return "image/jpeg"



def render_grayscale(inst: DCMInstance, pixel_array: npt.NDArray, window: Window | None) -> npt.NDArray | None:
    """Render grayscale image with optional windowing.

    Applies modality LUT and windowing transformations to pixel data for grayscale rendering.
    This implementation is adapted from pydicom's apply modality_lut function.

    Args:
        inst (DCMInstance): DICOM instance containing metadata
        pixel_array (npt.NDArray): Pixel data array to process
        window (Window | None): Optional window parameters for display

    Returns:
        npt.NDArray | None: Processed pixel array or None if no pixel data

    Reference:
        https://github.com/pydicom/pydicom/blob/357233a827272a875f04b53f3cfcb2f7db9a5a1d/src/pydicom/pixel_data_handlers/util.py
    """

    if inst.pixel_data:

        inst_metadata = json.loads(inst.meta_data)
        pixel_representation = inst.pixel_data.pixel_representation
        bits_stored = inst.pixel_data.bits_stored
        bit_depth = inst.pixel_data.bits_stored
        modality_lut = inst_metadata.get("0028300",None)
        rescale_slope = inst_metadata.get("00281053",None)
        if  rescale_slope:
            rescale_slope = rescale_slope["Value"][0]

        rescale_intercept = inst_metadata.get("00281052",None)
        if  rescale_intercept:
            rescale_intercept = rescale_intercept["Value"][0]
        window_func = inst_metadata.get("00281056","LINEAR")
        window_width = inst_metadata.get("00281051",None)
        window_center = inst_metadata.get("00281050",None)

        if window_func != "LINEAR":
            window_func = window_func["Value"][0]

        if window_width:
            window_width = window_width["Value"][0]

        if window_center:
            window_center=window_center["Value"][0]


        y_min = 0
        y_max = 0

        if pixel_representation == 0:
            y_min = 0
            y_max = 2**bits_stored - 1
        else:
            y_min = -(2 ** (bits_stored - 1))
            y_max = 2 ** (bits_stored - 1) - 1

        # slope and intercept
        if modality_lut:

            #nr_entries =
            #first_map =
            #nominal_depth =
            y_min = 0
            y_max = 2**bit_depth - 1

        elif rescale_intercept and rescale_slope: # need to check
            # need to be cast correctly
            y_min = y_min * rescale_slope + rescale_intercept
            y_max = y_max * rescale_slope + rescale_intercept
            #scaled_array = pixel_array*rescale_slope + rescale_intercept


        y_range = y_max - y_min

        win_applied = None
        if window_center is not None and window_width is not None:
            local_window = Window(center=window_center,width=window_width,func=window_func)
            if window is None:
                win_applied = local_window
            else:
                win_applied = window

        if win_applied is not None:
            if win_applied.func in ["LINEAR","LINEAR_EXACT"]:
                below = pixel_array <=(win_applied.center - win_applied.width / 2)
                above = pixel_array <= (win_applied.center - win_applied.width /2)
                between = numpy.logical_and(~below,~above)
                pixel_array[below] = y_min
                pixel_array[above] = y_max

                if between.any():
                    #pixel_array = ((pixel_array[between]-window.center))
                    pixel_array[between] = ((pixel_array[between]-win_applied.center)/win_applied.width+0.5)*\
                        y_range+y_min

            elif win_applied.func == "SIGMOID":
                pixel_array = y_range / (1 + numpy.exp(-4 * (pixel_array - win_applied.center) / win_applied.width))\
                      + y_min

        return pixel_array

    return None

def extract_image(inst: DCMInstance, frame_number: int, window: Window | None, \
                  codec_registry: CodecRegistry) -> Image.Image | None:
    """Extract and process a single frame from a DICOM instance.

    Extracts pixel data for a specific frame and converts it to a PIL Image,
    applying decompression if needed and windowing for grayscale images.

    Args:
        inst (DCMInstance): DICOM instance containing pixel data
        frame_number (int): Frame number to extract (0-based)
        window (Window | None): Optional windowing parameters
        codec_registry (CodecRegistry): Registry for image decompression

    Returns:
        Image.Image: PIL Image object of the extracted frame
    """

    if not inst.pixel_data:
        return None

    if not inst.pixel_data.frames:
        return None

    if is_compressed_transfer_syntax(inst.pixel_data.transfer_syntax_uid):
        ## decompress the images
        temp = codec_registry.decode_inst(inst,0)
        if temp is None:
            return None

        dcm_pixel = temp.frames[frame_number]
    else:
        dcm_pixel = inst.pixel_data.frames[frame_number]

    temp2 = buffer_to_array(dcm_pixel,inst.pixel_data.rows,inst.pixel_data.columns,
                        inst.pixel_data.bits_allocated,inst.pixel_data.samples_per_pixel,
                        inst.pixel_data.pixel_representation,inst.pixel_data.planar_configuration)

    if inst.pixel_data.photometric_interpretation in ["MONOCHROME1","MONOCHROME2"]:
        image_pixel=render_grayscale(inst,temp2,window)
        if image_pixel is None:
            return None
        pil_image = Image.fromarray(image_pixel)
        pil_image = pil_image.convert("L")

    elif inst.pixel_data.photometric_interpretation == "PALETTE COLOR": #TODO
        pass
        #image_pixel = apply_color_lut(dcm_pixel,ds)
    else:
        if dcm_pixel is None:
            return None
        pil_image=Image.fromarray(temp2)

    return pil_image


def render_image_thumbnail(inst: DCMInstance, frame_number: int, viewport: Viewport | None,
                           codec_registry: CodecRegistry) -> Image.Image | None:
    """Render a thumbnail image from a DICOM instance frame.

    Creates a thumbnail by extracting an image and resizing it based on viewport
    parameters or default sizing.

    Args:
        inst (DCMInstance): DICOM instance containing pixel data
        frame_number (int): Frame number to render (0-based)
        viewport (Viewport | None): Optional viewport parameters for sizing
        codec_registry (CodecRegistry): Registry for image decompression

    Returns:
        Image.Image: PIL Image object of the thumbnail
    """

    pil_image = extract_image(inst,frame_number,None,codec_registry)

    if pil_image is None:
        return None

    # now we can do a viewport map
    if viewport is not None:

        pil_image = pil_image.resize((viewport.vw,viewport.vh))

    else:
        pil_image = pil_image.resize((int(pil_image.width/2.0),int(pil_image.height/2.0)))

    return pil_image

def render_image(inst: DCMInstance, frame_number: int, viewport: Viewport | None, window: Window | None,
                 annotation: str | None, codec_registry: CodecRegistry) -> Image.Image | None:
    """Render a full resolution image from a DICOM instance frame.

    Creates a rendered image by extracting pixel data, applying windowing, viewport
    transformations, and optional annotations.

    Args:
        inst (DCMInstance): DICOM instance containing pixel data
        frame_number (int): Frame number to render (0-based)
        viewport (Viewport | None): Optional viewport parameters for cropping/scaling
        window (Window | None): Optional windowing parameters
        annotation (str | None): Optional text annotation to overlay
        codec_registry (CodecRegistry): Registry for image decompression

    Returns:
        Image.Image: PIL Image object of the rendered frame
    """

    pil_image = extract_image(inst,frame_number,window, codec_registry)

    if pil_image is None:
        return None

    # now we can do a viewport map
    if viewport is not None:
        cx = 0
        cy = 0
        cw = pil_image.width
        ch = pil_image.height

        if viewport.sx is not None:
            cx = int(viewport.sx)
        if viewport.sy is not None:
            cy = int(viewport.sy)

        if viewport.sw is None:
            cw = int(pil_image.width-cx)
        else:
            cw = int(viewport.sw)

        if viewport.sh is None:
            ch = int(pil_image.height-cy)
        else:
            ch = int(viewport.sh)

        if cw < 0:
            pil_image = pil_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            cw = abs(cw)
        if ch < 0:
            pil_image = pil_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            ch = abs(ch)

        pil_image = pil_image.crop((cx,cy,cw,ch))

        pil_image = pil_image.resize((viewport.vw,viewport.vh))

    if annotation is not None:
        pil_image_draw = ImageDraw.Draw(pil_image)
        font = ImageFont.truetype("/home/ran112/Downloads/engry.regular.ttf",15)
        pil_image_draw.text((5,5),annotation,font=font,align="left")

    return pil_image
