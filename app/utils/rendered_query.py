"""
    Utility functions for parsing rendered query parameters.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from fastapi import Request, HTTPException, Query
from app.utils.dicom_media import DicomMediaType  # noqa
from app.utils.accept_headers import parse_accept_headers, AcceptHeaders


class ThreeVec (BaseModel):
    """
        Holds a 3 vector
    """
    x : float
    y : float
    z : float

class RenderingMethod (str,Enum):
    """
        rendering methods
    """
    volume_rendered = "volume_rendered" # pylint: disable=C0103
    maximum_ip = "maximum_ip" # pylint: disable=C0103
    minimum_ip = "minimum_ip" # pylint: disable=C0103
    average_ip = "average_ip" # pylint: disable=C0103

class Orientation (str, Enum):
    """
        Orientations
    """

    a = 'a' # pylint: disable=C0103
    p = 'p' # pylint: disable=C0103
    r = 'r' # pylint: disable=C0103
    l = 'l' # pylint: disable=C0103
    h = 'h' # pylint: disable=C0103

class Window(BaseModel):
    """
    Represents a window function used for rendering grayscale medical images.

    The `Window` class defines the parameters for a window function, which is used to adjust the
    contrast and brightness of a grayscale medical image. The window function is specified by
    three attributes:

    - `center`: The center value of the window function.
    - `width`: The width of the window function.
    - `func`: The type of window function to use, such as "LINEAR", "LOG", or "SIGMOID".

    These parameters are used in the `render_grayscale` function to apply the window function to
    the pixel data of a medical image.
    """

    center: float
    width: float
    func: str

class Viewport(BaseModel):
    """
    Represents a viewport for rendering a medical image.

    The `Viewport` class defines the parameters for a viewport, which is used to specify the
    region of a medical image to be rendered. The viewport is specified by six attributes:

    - `vw`: The width of the viewport in pixels.
    - `vh`: The height of the viewport in pixels.
    - `sx`: The x-coordinate of the top-left corner of the viewport, as a fraction of the
    full image width.
    - `sy`: The y-coordinate of the top-left corner of the viewport, as a fraction of the
    full image height.
    - `sw`: The width of the viewport, as a fraction of the full image width.
    - `sh`: The height of the viewport, as a fraction of the full image height.

    These parameters are used to define the region of the medical image that should be
    rendered within the viewport.
    """

    vw:int
    vh:int
    sx:float|None
    sy:float|None
    sw:float|None
    sh:float|None



def accept_headers_rendered(request: Request) -> AcceptHeaders:
    """
    Parses the Accept headers from the incoming request and returns an AcceptHeaders object.

    If the Accept header is not present, raises a 406 Not Acceptable HTTP exception.

    If both the DICOM and DICOM_IMAGE media types are present in the Accept header,
    raises a 400 Bad Request HTTP exception, as rendered media types are not allowed together with DICOM media types.

    Returns:
        AcceptHeaders: An object representing the parsed Accept headers.

    """

    if request.headers.get("accept",None) is None:
        raise HTTPException(status_code=406,
                            detail="Accept header not present")

    accept_headers = parse_accept_headers(request.headers)
    accept_header_types = [x.type for x in accept_headers.accept_types]


    if  DicomMediaType.DICOM in accept_header_types and DicomMediaType.DICOM_IMAGE  in accept_header_types:

        raise HTTPException(status_code=400,
                            detail="Rendered media types are not allowed together with dicom media types.")
    return accept_headers



def get_query_viewport(viewport : Optional[str] = None)->Viewport | None:
    """
        TODO
    """
    if not viewport:
        return None
    ## must have vw,vx,sx,sy,sw,sh
    sp = viewport.split()
    vx: int = 0
    vy: int = 0
    sx:float = 0
    sy:float = 0
    sw:float | None = None
    sh:float | None = None

    try:
        vx = int(sp[0])
        vy = int(sp[1])
    except Exception as exc :
        raise HTTPException(status_code=400,
            detail="Missing required parameter vx or vy for Viewport") from exc

    if len(sp) >= 3 and sp[2] != "":
        try:
            sx= float(sp[2])
        except Exception as exc :
            raise HTTPException(status_code=400,
                detail="Parameter sx for Viewport is malformed") from  exc

    if len(sp) >= 4 and sp[3] != "":
        try:
            sy= float(sp[3])
        except Exception as exc:
            raise HTTPException(status_code=400,
                detail="Parameter sy for Viewport is malformed") from exc

    if len(sp) >= 5 and sp[4] != "":
        try:
            sw= float(sp[4])
        except Exception as exc:
            raise HTTPException(status_code=400,
                detail="Parameter sw for Viewport is malformed") from exc
    if len(sp) ==6 and sp[5] != "":
        try:
            sh= float(sp[5])
        except Exception as exc:
            raise HTTPException(status_code=400,
                detail="Parameter sh for Viewport is malformed") from exc

    return Viewport(vw=vx,vh=vy,sx=sx,sy=sy,sw=sw,sh=sh)

def get_query_viewport_thumb(viewport: str = Query()) -> Viewport:
    """Parse thumbnail viewport query parameter.

    Parses viewport query parameter for thumbnail requests, requiring only
    width and height values.

    Args:
        viewport (str): Viewport query string with width and height

    Returns:
        Viewport: Viewport object with width and height set

    Raises:
        HTTPException: If required viewport parameters are missing
    """


    ## must have vw,vx,sx,sy,sw,sh
    sp = viewport.split()
    vx = 0
    vy = 0

    try:
        vx = int(sp[0])
        vy = int(sp[1])
    except :
        raise HTTPException(status_code=400,
            detail="Missing required parameter vx or vy for Viewport")

    return Viewport(vw=vx,vh=vy,sx=None,sy=None,sw=None,sh=None)

def get_query_window(window: Optional[str] = None) -> Window | None:
    """Parse window query parameter into Window object.

    Parses a comma-separated window query parameter containing center, width,
    and function values.

    Args:
        window (Optional[str]): Window query string in format "center,width,function"

    Returns:
        Window | None: Parsed Window object or None if no window parameter

    Raises:
        HTTPException: If window parameter is malformed or invalid
    """

    if not window:
        return None

    sp = window.split(',')

    if len(sp) != 3:
        raise HTTPException(status_code=400,
            detail=f"Window query has three parameter, only {len(sp)} supplier")

    center = float(sp[0])
    width = float(sp[1])
    voi_func = sp[2]

    if voi_func not in ["LINEAR","LINEAR_EXACT","SIGMOID"]:
        raise HTTPException(status_code=400,
            detail="Window function '{voi_func}' is not supported")

    if voi_func == "LINEAR":
        if width < 1:
            raise HTTPException(status_code=400,
                detail="Window width must be greater than or equal to 1 for 'LINEAR' windowing operation")

    elif voi_func in  ["LINEAR_EXACT", "SIGMOID"]:
        if width <= 0:
            raise HTTPException(status_code=400,
                detail="Window width must be greater 0 for '{voi_func}' windowing operation")


    return Window(center=center,width=width,func=voi_func)

def get_query_3vec(vec: Optional[str] = None) -> ThreeVec | None:
    """
    Args:
        vec_name
    """

    if not vec:
        return None
    sp = vec.split(',')

    if len(sp) != 3:
        raise HTTPException(status_code=400,
            detail=f"query has three parameter, only {len(sp)} supplier")

    return ThreeVec(x=float(sp[0]),y=float(sp[1]),z=float(sp[2]))
