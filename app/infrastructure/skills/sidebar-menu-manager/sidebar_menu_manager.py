# -*- coding: utf-8 -*-
"""
Sidebar Menu Manager Skill Module
"""

import json
import os
import re
from typing import Any, Dict, List, Optional


def get_base_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


def get_sidebar_component_path() -> str:
    return os.path.join(get_base_dir(), "frontend", "src", "components", "Sidebar.vue")


def get_menu_items() -> List[Dict[str, str]]:
    path = get_sidebar_component_path()
    if not os.path.exists(path):
        return []

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    menu_items = []
    pattern = r"\{\s*key:\s*['\"]([^'\"]+)['\"]\s*,\s*name:\s*['\"]([^'\"]+)['\"]\s*,\s*icon:\s*['\"]([^'\"]+)['\"]\s*\}"
    matches = re.findall(pattern, content)

    for match in matches:
        menu_items.append({
            'key': match[0],
            'name': match[1],
            'icon': match[2]
        })

    return menu_items


def find_menu_items_block(content: str) -> Optional[str]:
    pattern = r"const\s+menuItems\s*=\s*\[([^\]]+)\]"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(0) if match else None


def add_menu_item(key: str, name: str, icon: str = '📌') -> Dict[str, Any]:
    path = get_sidebar_component_path()

    if not os.path.exists(path):
        return {'success': False, 'message': f'Sidebar.vue not found at {path}'}

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    existing = get_menu_items()
    if any(item['key'] == key for item in existing):
        return {'success': False, 'message': f'Menu item with key "{key}" already exists'}

    new_item = f"  {{ key: '{key}', name: '{name}', icon: '{icon}' }}"

    insert_pattern = r"(const\s+menuItems\s*=\s*\[)([^\]]+)(\])"
    match = re.search(insert_pattern, content, re.DOTALL)

    if match:
        items_block = match.group(2).rstrip()
        if items_block:
            items_block = items_block + ',\n'
        items_block = items_block + new_item + '\n'

        new_block = match.group(1) + items_block + match.group(3)
        content = content[:match.start()] + new_block + content[match.end():]

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            'success': True,
            'message': f'Added menu item: {name}',
            'item': {'key': key, 'name': name, 'icon': icon}
        }

    return {'success': False, 'message': 'Could not find menuItems array'}


def remove_menu_item(key: str) -> Dict[str, Any]:
    path = get_sidebar_component_path()

    if not os.path.exists(path):
        return {'success': False, 'message': f'Sidebar.vue not found at {path}'}

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    existing = get_menu_items()
    if not any(item['key'] == key for item in existing):
        return {'success': False, 'message': f'Menu item with key "{key}" not found'}

    item_pattern = r"\s*\{\s*key:\s*['\"]" + re.escape(key) + r"['\"]\s*,\s*name:\s*['\"]([^'\"]+)['\"]\s*,\s*icon:\s*['\"]([^'\"]+)['\"]\s*\},?\n?"
    content = re.sub(item_pattern, '', content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {
        'success': True,
        'message': f'Removed menu item: {key}'
    }


def update_menu_item(key: str, name: str = None, icon: str = None) -> Dict[str, Any]:
    path = get_sidebar_component_path()

    if not os.path.exists(path):
        return {'success': False, 'message': f'Sidebar.vue not found at {path}'}

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    existing = get_menu_items()
    if not any(item['key'] == key for item in existing):
        return {'success': False, 'message': f'Menu item with key "{key}" not found'}

    if name is not None:
        pattern = r"(key:\s*['\"]" + re.escape(key) + r"['\"]\s*,\s*name:\s*)['\"]([^'\"]+)['\"]"
        content = re.sub(pattern, lambda m: f"{m.group(1)}'{name}'", content)

    if icon is not None:
        pattern = r"(key:\s*['\"]" + re.escape(key) + r"['\"]\s*,\s*name:\s*['\"][^'\"]+['\"]\s*,\s*icon:\s*)['\"]([^'\"]+)['\"]"
        content = re.sub(pattern, lambda m: f"{m.group(1)}'{icon}'", content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {
        'success': True,
        'message': f'Updated menu item: {key}'
    }


def reorder_menu_items(key: str, new_index: int) -> Dict[str, Any]:
    path = get_sidebar_component_path()

    if not os.path.exists(path):
        return {'success': False, 'message': f'Sidebar.vue not found at {path}'}

    items = get_menu_items()
    if not items:
        return {'success': False, 'message': 'No menu items found'}

    current_index = None
    for i, item in enumerate(items):
        if item['key'] == key:
            current_index = i
            break

    if current_index is None:
        return {'success': False, 'message': f'Menu item with key "{key}" not found'}

    if new_index < 0 or new_index >= len(items):
        return {'success': False, 'message': f'Invalid new_index {new_index}. Must be between 0 and {len(items)-1}'}

    if current_index == new_index:
        return {'success': True, 'message': 'Item is already at position'}

    item = items.pop(current_index)
    items.insert(new_index, item)

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    items_str = ',\n'.join([f"  {{ key: '{i['key']}', name: '{i['name']}', icon: '{i['icon']}' }}" for i in items])

    pattern = r"const\s+menuItems\s*=\s*\[([^\]]+)\]"
    content = re.sub(pattern, f"const menuItems = [\n{items_str}\n]", content, flags=re.DOTALL)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {
        'success': True,
        'message': f'Moved "{key}" from position {current_index} to {new_index}'
    }


def get_sidebar_info() -> Dict[str, Any]:
    path = get_sidebar_component_path()
    items = get_menu_items()

    return {
        'path': path,
        'exists': os.path.exists(path),
        'item_count': len(items),
        'menu_items': items
    }


def get_sidebar_menu_manager_skill():
    return {
        'name': 'sidebar-menu-manager',
        'functions': {
            'get_sidebar_component_path': get_sidebar_component_path,
            'get_menu_items': get_menu_items,
            'get_sidebar_info': get_sidebar_info,
            'add_menu_item': add_menu_item,
            'remove_menu_item': remove_menu_item,
            'update_menu_item': update_menu_item,
            'reorder_menu_items': reorder_menu_items,
        }
    }