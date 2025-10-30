"""
    Configuration for dynaconf
"""

from dynaconf import Dynaconf, Validator


data_services = ["fs_data_service","mongodb_data_service"]
task_queue_services = ["rq_task_service"]
query_services = ["none","sql_query_service"]

_validators = [
    Validator('data_service',must_exist=True),
    Validator('data_service',condition=lambda v: v in data_services),

    Validator('task_queue_service',must_exist=True),
    Validator('task_queue_service',condition=lambda v: v in task_queue_services),

    Validator('query_service',must_exist=True),
    Validator('query_service',condition=lambda v: v in query_services),

    Validator('server_base_url',must_exist=True),
    #Validator('server_base_url',condition=lambda v: validators.url(v))
]

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    ## root path will be pulled from the env
    settings_files=['settings.toml', '.secrets.toml'],
    validators=_validators
)


# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
