"""
This module contains utility functions for dynamically importing decoder and encoder modules.

"""
import importlib
import sys
import os
from types import ModuleType
from typing import Sequence
from app.codecs.decoder import Decoder
from app.codecs.encoder import Encoder

def import_from_path(module_name : str, file_path:str)->ModuleType|None:
    """
        Import a module given its name and file path.

        This function dynamically imports a Python module from a specified file path
        and registers it in the system modules.

        Args:
            module_name (str): The name to assign to the imported module.
            file_path (str): The file system path to the Python module file.

        Returns:
            module: The imported module object.
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is not None:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        if spec.loader is not None:
            spec.loader.exec_module(module)
            return module
    return None


def import_decoder(module_name:str, klass_name:str, codec_paths:Sequence[str])->tuple[ModuleType|None,type[Decoder]|None]:
    """
        Import a decoder class from a module found in the specified codec paths.

        This function searches for a decoder module in the given codec paths and
        attempts to import the specified decoder class that inherits from the Decoder base class.

        Args:
            module_name (str): The name of the module file (without .py extension).
            klass_name (str): The name of the decoder class to import.
            codec_paths (list): List of directory paths to search for the module.

        Returns:
            tuple: A tuple containing (decoder_module, decoder_class) if found,
                   or (None, None) if not found or invalid.
    """
    for codec_path in codec_paths:
        file_path = os.path.join(codec_path, module_name + ".py")
        if os.path.exists(file_path):
            decoder_module = import_from_path(module_name, file_path)
            if decoder_module is not None and hasattr(decoder_module, klass_name):
                decoder_klass = getattr(decoder_module, klass_name)
                if isinstance(decoder_klass, type) and issubclass(decoder_klass, Decoder):
                    return decoder_module, decoder_klass

    return None, None


def import_encoder(module_name:str, klass_name:str, codec_paths:Sequence[str])->tuple[ModuleType|None,type[Encoder]|None]:
    """
        Import an encoder class from a module found in the specified codec paths.

        This function searches for an encoder module in the given codec paths and
        attempts to import the specified encoder class that inherits from the Encoder base class.

        Args:
            module_name (str): The name of the module file (without .py extension).
            klass_name (str): The name of the encoder class to import.
            codec_paths (list): List of directory paths to search for the module.

        Returns:
            tuple: A tuple containing (encoder_module, encoder_class) if found,
                   or (None, None) if not found or invalid.
    """
    for codec_path in codec_paths:
        file_path = os.path.join(codec_path, module_name + ".py")
        if os.path.exists(file_path):
            encoder_module = import_from_path(module_name, file_path)
            if encoder_module is not None and hasattr(encoder_module, klass_name):
                encoder_klass = getattr(encoder_module, klass_name)
                if isinstance(encoder_klass, type) and issubclass(encoder_klass, Encoder):
                    return encoder_module, encoder_klass

    return None, None
