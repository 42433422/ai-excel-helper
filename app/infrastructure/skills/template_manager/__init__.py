# -*- coding: utf-8 -*-
"""
Template Manager Skill Module
"""

from .template_manager import (
    create_template,
    decompose_template_file,
    delete_template,
    export_products_with_template,
    get_base_dir,
    get_default_template,
    get_template_file,
    get_template_file_path,
    get_template_info,
    get_template_manager_skill,
    list_all_templates,
    list_label_templates,
    list_physical_template_files,
    list_product_templates,
    list_purchase_unit_templates,
    list_shipment_record_templates,
    list_shipment_templates,
    list_templates_by_type,
    resolve_template_path,
    save_template_file,
    update_template,
)

__all__ = [
    'get_template_manager_skill',
    'get_base_dir',
    'list_all_templates',
    'list_templates_by_type',
    'list_shipment_templates',
    'list_shipment_record_templates',
    'list_product_templates',
    'list_purchase_unit_templates',
    'list_label_templates',
    'get_template_file_path',
    'get_default_template',
    'decompose_template_file',
    'resolve_template_path',
    'save_template_file',
    'get_template_info',
    'create_template',
    'update_template',
    'delete_template',
    'export_products_with_template',
    'list_physical_template_files',
    'get_template_file',
]