from psd_tools import PSDImage


import re
import os
import tempfile
import shutil

from pxr import Usd, UsdGeom, Tf

from .converter import utils, layer
from .converter import conversion_context, conversion_options

import logging

LOG = logging.getLogger(__name__)


def convert(psd_path, usd_path):

    output_usd_path = usd_path

    is_usdz = False
    if "usdz" in usd_path:  # TODO: Check only extension ?
        is_usdz = True
        output_usd_path = output_usd_path[:-1]

    working_dir = ""

    # If .usd, .usda, .usdc use output file path
    working_dir = os.path.dirname(output_usd_path)

    # If .usdz generate temp dir
    if is_usdz:
        working_dir = tempfile.mkdtemp()
        output_usd_path = os.path.join(working_dir, os.path.basename(output_usd_path))

    conversion_context["working_dir"] = working_dir

    tex_dir = os.path.join(working_dir, "tex")
    os.makedirs(tex_dir, exist_ok=True)

    usd_stage = Usd.Stage.CreateInMemory()

    psd = PSDImage.open(psd_path)
    if conversion_options["output_combined"]:
        psd.composite().save(os.path.join(tex_dir, utils.make_image_path("combined")))

    conversion_context["canvas_size"] = psd.size

    for _layer in psd:
        LOG.debug(f"Export layer {_layer!r}")

        slug = slugify(_layer.name)
        LOG.debug(f"  slug: {slug!r}")

        layer_image = _layer.composite()

        _img_path = os.path.join(tex_dir, utils.make_image_path(slug))

        if conversion_options["use_absolute_paths"]:
            _img_path = os.path.abspath(_img_path)

        layer_image.save(_img_path)

        _path = "/" + Tf.MakeValidIdentifier(slug)

        layer.convert(usd_stage, _path, _img_path, _layer)

    usd_stage.Export(output_usd_path)

    if is_usdz:
        # Zip usd
        utils.zip_usd(usd_path, output_usd_path)

        # Cleanup temp
        try:
            shutil.rmtree(working_dir)
        except OSError as e:
            print("Error: {} : {}".format(working_dir, e.strerror))


def slugify(text):
    # based on:
    # https://medium.com/@ryan_forrester_/remove-special-characters-from-strings-in-python-complete-guide-53651c8163d9

    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    # Remove special characters
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    # Replace spaces with hyphens
    slug = re.sub(r"\s+", "-", slug)
    # Remove multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    return slug
