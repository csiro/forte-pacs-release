"""
    Main module
"""
import logging
import logging.config
import random
import string
import time
from collections.abc import AsyncIterator
from typing import Callable
import os
import json

from fastapi import FastAPI,Request

from fastapi_lifespan_manager import LifespanManager


from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response as StarletteResponse

from app.api.dcmweb.capabilities.capabilities import capabilities_router

from app.api.dcmweb.wado.wado_api_instance import wado_instance_router
from app.api.dcmweb.wado.wado_api_metadata import wado_metadata_router
from app.api.dcmweb.wado.wado_api_bulkdata import wado_bulkdata_router
from app.api.dcmweb.wado.wado_api_rendered import wado_rendered_router
from app.api.dcmweb.wado.wado_api_renderedmpr import wado_renderedmpr_router
from app.api.dcmweb.wado.wado_api_rendered3d import wado_rendered3d_router
from app.api.dcmweb.wado.wado_api_thumbnail import wado_thumbnail_router


from app.api.dcmweb.stow.stow_api import stow_router

from app.api.dcmweb.qido.qido_api import qido_router
from app.api.dcmweb.qido.qido_api_ni import qido_router_ni

from app.services.api.data_service import DataService
from app.services.data_services.fs_data_service import FSDataService
from app.services.query_services.sql_query_service import SQLQueryService
from app.services.query_services.fhir_query_service import FHIRQueryService

from app.services.task_queue_services.rq_task_queue_service import RQTaskQueueService

from app.codecs.codec_registry import CodecRegistry

from app.callbacks.dcm_qido_meta_data import update_meta_data_qido
from app.callbacks.dcm_qido_meta_data_fhir import update_meta_data_qido_fhir

from app.config import settings
from app.utils.gen_capabilities_openapi import build_capabilities_xml, build_capabilities_json
from app.codecs.import_utils import import_decoder,import_encoder
from pathlib import Path

logger = logging.getLogger(__name__)

#sys.stdout = None
middleware = [Middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_SETTINGS.allow_origins,
    allow_methods=settings.CORS_SETTINGS.allow_methods,
	allow_headers=settings.CORS_SETTINGS.allow_headers)
]

manager = LifespanManager()
app = FastAPI(middleware=middleware, lifespan=manager, debug=True)


@manager.add
async def setup_logging()->AsyncIterator:
    """
        Setup logging
    """
    config_file_path = os.path.join(os.path.dirname(__file__),'../config/logging.conf')
    logging.config.fileConfig(config_file_path, disable_existing_loggers=False)
    yield


@manager.add
async def setup_data_service()->AsyncIterator:
    """
        Setup dataservices
    """
    data_service : DataService
    if settings.data_service.upper() == "FS_DATA_SERVICE":

        root_directory = None

        try:
            root_directory = settings.FS_DATA_SERVICE["ROOT_DIR"]
        except KeyError as e:
            ## log it.
            logger.error("Root directory required for fs data service is missing. The system requires this to function")
            raise Exception("Root directory required for fs data service is missing. The system requires this to function")

        data_service = FSDataService(root_directory)

    await data_service.init_service()
    yield {"data_service":data_service}

    await data_service.dispose()

@manager.add
async def setup_query_service()->AsyncIterator:
    """
        Setup query service
    """

    if settings.QUERY_SERVICE.upper() == "SQL_QUERY_SERVICE":
        sql_url = None
        username = None
        password =  None
        sql_dialect = None

        try:
            sql_dialect=settings.SQL_QUERY_SERVICE['SQL_DIALECT']
        except KeyError as e:
            logger.error("Dialect required for sql query service is missing. The system requires this to function")
            raise Exception("Dialect required for sql query service is missing. The system requires this to function")

        try:
            sql_url = settings.SQL_QUERY_SERVICE['SQL_URL']
        except KeyError as e:
            logger.error("URL required for sql query service is missing. The system requires this to function")
            raise Exception("URL required for sql query  service is missing. The system requires this to function")

        try:
            username = settings.SQL_QUERY_SERVICE['SQL_USERNAME']
        except KeyError as e:
            ## log it.
            logger.info("Username not provided for sql query service")
        try:
            password = settings.SQL_QUERY_SERVICE['SQL_PASSWORD']
        except KeyError as e:
            logger.info("Password not provided for sql query  service")

        username_str = ""
        if username:
            username_str=username_str+username
            if password:
                username_str+=":"+password

        if username_str != "":
            sql_url_full = sql_dialect+"://"+username_str+"@"+sql_url
        else:
            sql_url_full = sql_dialect+"://"+sql_url


        query_service = SQLQueryService(sql_url_full)
        await query_service.init_service()

        yield {"query_service":query_service}
        await query_service.dispose()

    elif settings.QUERY_SERVICE.upper() == "FHIR_QUERY_SERVICE":
        fhir_server_url = None
        try:
            fhir_server_url =settings.FHIR_QUERY_SERVICE['FHIR_SERVER_URL']
        except KeyError as e:
            logger.error(" FHIR server url required for fhir query service is missing. The system requires this to function")
            raise Exception("FHIR server url required for fhir query service is missing. The system requires this to function")


        query_service = FHIRQueryService(fhir_server_url)
        await query_service.init_service()

        yield {"query_service":query_service}
        await query_service.dispose()

    elif settings.QUERY_SERVICE.upper() == "NONE":
        yield {"query_service":None}
    
    

@manager.add
async def setup_base_directory() -> AsyncIterator:
    """
        Setup base directory and icc profile directory
    """

    base_directory =  Path(__file__).resolve().parent
    icc_directory = (Path(__file__).resolve().parent.parent).joinpath('icc')

    yield {"base_directory":base_directory,"icc_directory":icc_directory}

@manager.add
async def setup_base_url() -> AsyncIterator:
    """
        Setup base url
    """

    yield {"server_base_url": settings.server_base_url}

@manager.add
async def setup_capabilities_statements()->AsyncIterator:
    """
    Setup capabilitie statements
    """

    openapi_json = json.dumps(app.openapi())
    wadl = build_capabilities_xml(openapi_json,settings.server_base_url)
    _json = build_capabilities_json(openapi_json,settings.server_base_url)

    yield {"cap_statement_wadl": wadl, "cap_statement_json":_json}

@manager.add
async def setup_stow_callbacks()->AsyncIterator:
    """
        Setup callbacks
    """
    if settings.QUERY_SERVICE.upper() == "SQL_QUERY_SERVICE":
        yield {"stow_callbacks" : [update_meta_data_qido]}
    elif settings.QUERY_SERVICE.upper() == "FHIR_QUERY_SERVICE":
        yield {"stow_callbacks" : [update_meta_data_qido_fhir]}

@manager.add
async def setup_task_queue()->AsyncIterator:
    """
        Setup task queue
    """

    if settings.task_queue_service == 'rq_task_service':


        redis_url = None
        username = None
        password =  None

        try:
            redis_url = settings.RQ_TASK_SERVICE['REDIS_URL']
        except KeyError as e:
            logger.error("URL required for redis (rq_task_service) is missing. The system requires this to function")
            raise Exception("URL required for redis (rq_task_service) is missing. The system requires this to function")

        try:
            username = settings.RQ_TASK_SERVICE['REDIS_USERNAME']
        except KeyError as e:
            ## log it.
            logger.info("Username not provided for redis (rq_task_service)")
        try:
            password = settings.RQ_TASK_SERVICE['REDIS_PASSWORD']
        except KeyError as e:
            logger.info("Password not provided for redis (rq_task_service)")

        username_str = ""
        if username:
            username_str=username_str+username
            if password:
                username_str+=":"+password

        redis_url_full = "redis://"+username_str+"@"+redis_url


        queue_service = RQTaskQueueService(redis_url_full)
        await queue_service.init_service()

        yield {"queue_service":queue_service}




@manager.add
async def setup_codec_registry()->AsyncIterator:
    """
        Setup codec registry
    """

    if not settings.exists("CODECS"):
        yield {"codec_registry":None}


    codec_registry = CodecRegistry()
    codec_paths = settings.codecs.codec_paths

    decoders = settings.codecs.decoders if settings.codecs.decoders else []
    encoders = settings.codecs.encoders if settings.codecs.encoders else []
    for decoder_name  in decoders:
        (decoder_module_name, decoder_class_name) = decoder_name.split(".")
        (decoder_module, decoder_class) = import_decoder(decoder_module_name,decoder_class_name, codec_paths)
        if not decoder_module or not decoder_class:
            logger.error("Failed to import decoder %s.%s", decoder_module_name, decoder_class_name)
            continue
        (ok,err) = decoder_module.preflight()
        if not ok:
            logger.error("Decoder %s.%s failed preflight check. Error: %s", \
                         decoder_module_name, decoder_class_name, err)
            continue
        decoder = decoder_class()
        logger.info("Registering decoder %s.%s", decoder_module_name, decoder_class_name)
        codec_registry.register_decoder(decoder)

    for encoder_name  in encoders:
        (encoder_module_name, encoder_class_name) = encoder_name.split(".")
        (encoder_module, encoder_class) = import_encoder(encoder_module_name,encoder_class_name, codec_paths)
        if not encoder_module or not encoder_class:
            logger.error("Failed to import encoder %s.%s", encoder_module_name, encoder_class_name)
            continue
        (ok,err) = encoder_module.preflight()
        if not ok:
            logger.error("Encoder %s.%s failed preflight check. Error: %s", encoder_module_name,encoder_class_name,err)
            continue
        encoder = encoder_class()
        logger.info("Registering encoder %s.%s", encoder_module_name, encoder_class_name)
        codec_registry.register_encoder(encoder)
    yield {"codec_registry":codec_registry}

@app.middleware("http")
async def log_requests(request: Request, call_next : Callable) -> StarletteResponse:
    """ Function to log requests
    """
    idem = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    logger.info(f"rid={idem} start request path={request.url.path}")
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}")

    return response



app.include_router(wado_instance_router,prefix="/"+settings.wado_prefix)
app.include_router(wado_metadata_router,prefix="/"+settings.wado_prefix)
app.include_router(wado_bulkdata_router,prefix="/"+settings.wado_prefix)
app.include_router(wado_rendered_router,prefix="/"+settings.wado_prefix)
app.include_router(wado_thumbnail_router,prefix="/"+settings.wado_prefix)
app.include_router(wado_renderedmpr_router,prefix="/"+settings.wado_prefix)
app.include_router(wado_rendered3d_router,prefix="/"+settings.wado_prefix)

app.include_router(stow_router,prefix="/"+settings.stow_prefix)
app.include_router(capabilities_router)

## if we are not supporting qido, then set the appropriate router
if settings.query_service != "none":
    app.include_router(qido_router,prefix="/"+settings.qido_prefix)
else:
    app.include_router(qido_router_ni,prefix="/"+settings.qido_prefix)

